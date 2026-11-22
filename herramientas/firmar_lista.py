# -*- coding: utf-8 -*-
"""firmar_lista — firma la lista del cliente (la de `lista_del_cliente.py`) con la clave de PUBLICACIÓN de la
plataforma Eñeños, como la de EDA: un JWS compacto Ed25519 que el launcher verifica ANTES de bajar un byte.

    python herramientas/firmar_lista.py lista_gunbound_2026.11.18.json  [--clave %USERPROFILE%\\.enenos\\publicacion_actual.pem]

Escribe `lista.jws` al lado de la lista. La cabecera y la carga (lo que el launcher tiene que comprobar):
    cabecera  {"alg": "EdDSA", "typ": "gunbound-manifiesto", "kid": sha256(pública)[:16]}
    carga     la lista + {"aud": "gunbound-launcher", "iat": <segundos>}
(el mismo molde que EDA: `typ` "eda-manifiesto", `aud` "eda-launcher"; ver `eda.rs:verificar_manifiesto`)

⛔ La clave privada vive SÓLO en esta PC (`%USERPROFILE%\\.enenos\\`): no se imprime, no se copia, no va a ningún
VPS ni repo. Antes de firmar se comprueba que su pública sea la que el launcher ya conoce (`publicacion_publicas.json`),
y después de firmar se VERIFICA la firma con la pública.
"""
import argparse
import base64
import hashlib
import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from servidor import firma_ed25519 as ed  # noqa: E402

CLAVES = Path.home() / ".enenos"
TYP, AUD = "gunbound-manifiesto", "gunbound-launcher"
PKCS8_ED25519 = bytes.fromhex("302e020100300506032b657004220420")   # el prefijo DER de una privada Ed25519


def b64u(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def semilla_de_pem(ruta):
    lineas = [x for x in Path(ruta).read_text("ascii").splitlines() if x and not x.startswith("-----")]
    der = base64.b64decode("".join(lineas))
    if len(der) != 48 or not der.startswith(PKCS8_ED25519):
        raise SystemExit(f"⛔ {ruta} no es una clave privada Ed25519 (PKCS#8)")
    return der[16:]


def firmar(lista, semilla):
    pub = ed.publica(semilla)
    kid = hashlib.sha256(pub).hexdigest()[:16]
    conocidas = json.loads((CLAVES / "publicacion_publicas.json").read_text("utf-8"))
    if not any(v["kid"] == kid and v["publica"] == b64u(pub) for v in conocidas.values()):
        raise SystemExit("⛔ esa privada no corresponde a ninguna pública de publicacion_publicas.json")
    carga = dict(lista, aud=AUD, iat=int(time.time()))
    cab = {"alg": "EdDSA", "typ": TYP, "kid": kid}
    a = b64u(json.dumps(cab, separators=(",", ":")).encode())
    b = b64u(json.dumps(carga, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    firma = ed.firmar(semilla, f"{a}.{b}".encode())
    if not ed.verificar(pub, f"{a}.{b}".encode(), firma):
        raise SystemExit("⛔ la firma recién hecha no verifica")
    return f"{a}.{b}.{b64u(firma)}", kid


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("lista")
    ap.add_argument("--clave", default=str(CLAVES / "publicacion_actual.pem"))
    x = ap.parse_args()
    lista = json.loads(Path(x.lista).read_text("utf-8"))
    jws, kid = firmar(lista, semilla_de_pem(x.clave))
    salida = Path(x.lista).with_name("lista.jws")
    salida.write_text(jws + "\n", encoding="ascii", newline="\n")
    print(f"✔ {salida}: {len(lista['files'])} archivos, versión {lista['version']}, firmada con kid {kid} "
          f"(typ {TYP}, aud {AUD})")
