# -*- coding: utf-8 -*-
"""pase — comprueba SOLO el pase que firma Cuenta Eñeños. Es el mismo contrato que R2Beat y EDA.

    JWT compacto, EdDSA (Ed25519):
      header  {"alg": "EdDSA", "typ": "JWT", "kid": "<16 hex>"}
      payload {"iss": "r2beat-portero", "aud": "<juego>", "sub": "<Eñeños ID>", "iat": s, "exp": iat+300, "jti": "<único>"}

Se comprueba: la firma con la clave PÚBLICA de Cuenta Eñeños, `alg`, `iss`, `aud` = el juego de ESTE server
(`gunbound` en prod, `gunbound-prueba` en el de prueba: un pase de uno no sirve en el otro), `exp`, y que el `jti`
no se haya usado antes.

⛔ Nunca se le pregunta nada a Cuenta Eñeños por cada entrada. La clave pública llega por variable de entorno o se
   pide UNA vez al arrancar (`/clave-publica`) y queda en memoria: si Cuenta Eñeños se cae, el que ya juega sigue.
⛔ El pase NO trae el nombre de login (es privado). La identidad es `sub`: el Eñeños ID.
"""
import base64
import json
import time
import urllib.request

from . import firma_ed25519 as ed
from .registro import log

EMISOR = "r2beat-portero"
TOLERANCIA_RELOJ = 30                  # segundos de desfase aceptados entre las máquinas
MAX_RECORDADOS = 50_000


def _de_b64u(s):
    s = s.strip()
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def parsear_clave_publica(valor):
    """base64url (32 bytes), hex de 64, o el JWKS de `/clave-publica`. -> bytes(32) o None."""
    txt = (valor or "").strip()
    if not txt:
        return None
    if txt.startswith("{"):
        try:
            d = json.loads(txt)
            txt = str(((d.get("keys") or [{}])[0].get("x")) or d.get("x") or "")
        except (ValueError, AttributeError):
            return None
    if len(txt) == 64:
        try:
            return bytes.fromhex(txt)
        except ValueError:
            pass
    try:
        b = _de_b64u(txt)
        return b if len(b) == 32 else None
    except (ValueError, TypeError):
        return None


def bajar_clave_publica(url_base, timeout=4.0):
    base = url_base.rstrip("/")
    for u in (base + "/clave-publica", base + "/cuentas/clave-publica"):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"Accept": "application/json"}),
                                        timeout=timeout) as r:
                pub = parsear_clave_publica(r.read().decode("utf-8"))
                if pub:
                    return pub
        except Exception as e:                                          # noqa: BLE001
            log("PASE", f"no pude bajar la clave pública de {u}: {e}")
    return None


class Verificador:
    def __init__(self, juego, clave_publica=None):
        self.juego = juego
        self.clave = clave_publica
        self._usados = {}            # jti -> exp

    def comprobar(self, pase, ahora=None):
        """-> (eñeños_id, None) o (None, motivo)."""
        ahora = int(time.time() if ahora is None else ahora)
        if not self.clave:
            return None, "el server no tiene la clave de Cuenta Eñeños"
        partes = (pase or "").strip().split(".")
        if len(partes) != 3:
            return None, "pase mal formado"
        try:
            cab = json.loads(_de_b64u(partes[0]))
            carga = json.loads(_de_b64u(partes[1]))
            firma = _de_b64u(partes[2])
        except (ValueError, TypeError):
            return None, "pase mal formado"
        if not isinstance(cab, dict) or not isinstance(carga, dict):
            return None, "pase mal formado"
        if cab.get("alg") != "EdDSA":
            return None, "algoritmo no aceptado"
        if not ed.verificar(self.clave, (partes[0] + "." + partes[1]).encode("ascii"), firma):
            return None, "firma inválida"
        if carga.get("iss") != EMISOR:
            return None, "emisor desconocido"
        if carga.get("aud") != self.juego:
            return None, f"el pase es para «{carga.get('aud')}», no para «{self.juego}»"
        try:
            exp, iat = int(carga.get("exp")), int(carga.get("iat", 0))
        except (TypeError, ValueError):
            return None, "pase sin vencimiento"
        if exp + TOLERANCIA_RELOJ < ahora:
            return None, "pase vencido"
        if iat - TOLERANCIA_RELOJ > ahora:
            return None, "pase del futuro"
        jti = str(carga.get("jti") or "")
        if not jti:
            return None, "pase sin jti"
        self._olvidar_vencidos(ahora)
        if jti in self._usados:
            return None, "pase ya usado"
        sub = str(carga.get("sub") or "")
        if not sub.isdigit() or int(sub) <= 0:
            return None, "pase sin Eñeños ID"
        self._usados[jti] = exp
        return int(sub), None

    def _olvidar_vencidos(self, ahora):
        if len(self._usados) < MAX_RECORDADOS // 2:
            return
        for j, e in list(self._usados.items()):
            if e + TOLERANCIA_RELOJ < ahora:
                del self._usados[j]
        # Si después de limpiar los vencidos el diccionario sigue lleno, el sistema está bajo ataque de pases
        # únicos. El tope duro saca los VENCIDOS más viejos primero; si todos son vigentes (anómalo), se
        # conservan para evitar crear ventanas de replay.
        if len(self._usados) >= MAX_RECORDADOS:
            expirados = sorted((e, j) for j, e in self._usados.items() if e + TOLERANCIA_RELOJ < ahora)
            for _, j in expirados:
                if len(self._usados) < MAX_RECORDADOS:
                    break
                del self._usados[j]


# ── para pruebas y para el laboratorio: firmar pases con una clave de prueba ─────────────────────────────────

def _b64u(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def firmar_pase(semilla, aud, sub, vida=300, jti=None, ahora=None, iss=EMISOR):
    """Un pase como los de Cuenta Eñeños, firmado con `semilla` (32 bytes). SÓLO pruebas y laboratorio."""
    import secrets
    ahora = int(time.time() if ahora is None else ahora)
    pub = ed.publica(semilla)
    import hashlib
    cab = {"alg": "EdDSA", "typ": "JWT", "kid": hashlib.sha256(pub).hexdigest()[:16]}
    carga = {"iss": iss, "aud": aud, "sub": str(sub), "iat": ahora, "exp": ahora + vida,
             "jti": jti or secrets.token_hex(12)}
    a = _b64u(json.dumps(cab, separators=(",", ":")).encode()) + "." + _b64u(json.dumps(carga, separators=(",", ":")).encode())
    return a + "." + _b64u(ed.firmar(semilla, a.encode("ascii")))
