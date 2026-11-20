# -*- coding: utf-8 -*-
"""web — el HTTP del server: el CANJE (pase → boleto), la gestión de personajes del launcher y la salud.
Escucha en 127.0.0.1: afuera va detrás de Caddy (HTTPS), porque la ficha y el boleto son secretos.

    GET  /salud                                     {"ok": true, "entorno", "juego", "en_linea"}
    GET  /paises                                    {"paises": [{"n", "nombre", "iso"}]}   (para el menú del launcher)
    POST /personajes      {"pase"}                200 {"ficha", "personajes", "maximo", "pais_sugerido"}
    POST /personajes/crear  {"ficha", "nick", "genero": "m"|"f", "pais"}      200 {"personajes"}
    POST /personajes/pais   {"ficha", "personaje", "pais"}                     200 {"personajes"}
    POST /canje             {"pase"} | {"ficha", "personaje"}                  200 {"usuario", "ticket", "servidor", "nick", "nuevo"}
(las rutas se aceptan también con el prefijo /gunbound o /gunbound-prueba, como las pase Caddy)

    /interno/panel/…   la puerta del panel del Coordinador (servidor/panel.py). ⛔ SÓLO sin prefijo: lo que llega
                       por Caddy trae /gunbound… y da 404. Pide la ficha interna (sin ella, 404 también)
"""
import asyncio
import json

from . import panel as puerta_panel
from . import rangos
from .ajustes import DIR_DATOS_JUEGO
from .base import PAISES
from .boletos import Fichas
from .registro import log

CUERPO_MAX = 8192
PAISES_ISO = json.loads((DIR_DATOS_JUEGO / "paises_iso.json").read_text("utf-8"))
_ISO_DE = {n: iso for iso, n in PAISES_ISO.items()}
# la lista para el launcher: el número es el que va en el juego (la etiqueta de 2 letras que dibuja el cliente,
# `nationcode.img`); `iso` = el código ISO-3166 (null en los pocos que no tienen uno claro); 0 = «?» (sin país)
LISTA_PAISES = [{"n": 0, "nombre": "Sin país", "iso": None}] + [
    {"n": int(n), "nombre": nombre, "iso": _ISO_DE.get(int(n))}
    for n, nombre in sorted(json.loads((DIR_DATOS_JUEGO / "paises.json").read_text("utf-8"))["paises"].items(),
                            key=lambda kv: int(kv[0]))]


def _json(cuerpo):
    try:
        d = json.loads((cuerpo or b"").decode("utf-8") or "{}")
        return d if isinstance(d, dict) else None
    except (ValueError, UnicodeDecodeError):
        return None


def _pais_sugerido(cabeceras):
    if not cabeceras:
        return 0
    for k, v in cabeceras.items():
        if k.lower() == "cf-ipcountry":
            codigo = str(v).strip().upper()
            return PAISES_ISO.get(codigo, 0) if len(codigo) == 2 else 0
    return 0


class Web:
    def __init__(self, ajustes, verificador, boletos, base, contar_en_linea, puerto_broker, fichas=None, panel=None):
        self.aj = ajustes
        self.ver = verificador
        self.boletos = boletos
        self.base = base
        self.contar = contar_en_linea
        self.puerto_broker = puerto_broker
        self.fichas = fichas if fichas is not None else Fichas()
        self.panel = panel                   # servidor/panel.py (None = sin puerta del Coordinador)
        self._servidor = None

    async def arrancar(self):
        self._servidor = await asyncio.start_server(self._conexion, self.aj.escucha_http, self.aj.puerto_http,
                                                    reuse_address=True)
        log("WEB", f"escuchando http://{self.aj.escucha_http}:{self.aj.puerto_http} (canje del pase «{self.aj.pase_juego}»)")

    def cerrar(self):
        if self._servidor:
            self._servidor.close()

    @property
    def puerto(self):
        return self._servidor.sockets[0].getsockname()[1] if self._servidor else self.aj.puerto_http

    def servidor_para_el_launcher(self):
        return self.aj.broker_publico or f"127.0.0.1:{self.puerto_broker()}"

    # ── apoyo ─────────────────────────────────────────────────────────────────────────────────────────────
    def _verificar_pase(self, datos):
        if not self.ver.clave:
            return None, (503, {"error": "el server no tiene la clave de Cuenta Eñeños"})
        pase = datos.get("pase", "")
        if not isinstance(pase, str):
            return None, (400, {"error": "cuerpo inválido"})
        cuenta, motivo = self.ver.comprobar(pase)
        if cuenta is None:
            log("CANJE", f"rechazado: {motivo}")
            return None, ((409 if motivo == "pase ya usado" else 401), {"error": motivo})
        return cuenta, None

    def _ficha(self, datos):
        cuenta = self.fichas.cuenta(datos.get("ficha"))
        if cuenta is None:
            return None, (401, {"error": "ficha inválida o vencida"})
        return cuenta, None

    def _personajes_json(self, cuenta):
        return [
            {
                "id": j.enenos_id,
                "nick": j.nick,
                "genero": "f" if j.genero else "m",
                "pais": j.pais,
                "rango": rangos.rango_de(j),
                "rango_nombre": rangos.NOMBRES.get(rangos.rango_de(j), "Especial"),
                "gp": j.gp,
            }
            for j in self.base.personajes(cuenta)
        ]

    # ── las rutas ─────────────────────────────────────────────────────────────────────────────────────────
    def atender(self, metodo, ruta, cuerpo, cabeceras=None):
        # ⛔ ANTES de sacar el prefijo: /gunbound/interno/panel/… (lo que pasa Caddy) NO es la puerta
        if puerta_panel.es_suya(ruta.split("?")[0]):
            return self.panel.atender(metodo, ruta, cuerpo, cabeceras or {}) if self.panel else (404, {"error": "no existe"})
        for prefijo in ("/gunbound-prueba", "/gunbound"):
            if ruta.startswith(prefijo + "/"):
                ruta = ruta[len(prefijo):]
                break
        ruta = ruta.split("?")[0]
        if metodo == "GET" and ruta == "/salud":
            return 200, {"ok": True, "entorno": self.aj.entorno, "juego": self.aj.pase_juego, "en_linea": self.contar()}
        if metodo == "GET" and ruta == "/paises":
            return 200, {"paises": LISTA_PAISES}
        if metodo != "POST":
            return 404, {"error": "no existe"}
        datos = _json(cuerpo)
        if datos is None:
            return 400, {"error": "cuerpo inválido"}

        if ruta == "/personajes":
            cuenta, err = self._verificar_pase(datos)
            if err:
                return err
            lista = self.base.personajes(cuenta)
            if any(j.baneado for j in lista):
                return 403, {"error": "cuenta suspendida en GunBound"}
            ficha = self.fichas.emitir(cuenta)
            return 200, {
                "ficha": ficha,
                "personajes": self._personajes_json(cuenta),
                "maximo": self.aj.personajes_por_cuenta,
                "pais_sugerido": _pais_sugerido(cabeceras),
            }

        if ruta == "/personajes/crear":
            cuenta, err = self._ficha(datos)
            if err:
                return err
            if any(j.baneado for j in self.base.personajes(cuenta)):
                return 403, {"error": "cuenta suspendida en GunBound"}
            nick, genero, pais = datos.get("nick"), datos.get("genero"), datos.get("pais")
            if (not isinstance(nick, str) or genero not in ("m", "f")
                    or isinstance(pais, bool) or not isinstance(pais, int)):
                return 400, {"error": "datos inválidos"}
            j, motivo = self.base.crear_personaje(
                cuenta, nick, genero == "f", pais,
                self.aj.oro_inicial, self.aj.cash_inicial,
                maximo=self.aj.personajes_por_cuenta,
            )
            if j is None:
                if "máximo" in motivo:
                    return 403, {"error": motivo}
                if "ocupado" in motivo:
                    return 409, {"error": motivo}
                return 400, {"error": motivo}
            log("PERSONAJES", f"cuenta {cuenta}: creó personaje {j.enenos_id} ({j.nick}, {'f' if j.genero else 'm'}, país {j.pais})")
            return 200, {"personajes": self._personajes_json(cuenta)}

        if ruta == "/personajes/pais":
            cuenta, err = self._ficha(datos)
            if err:
                return err
            pid, pais = datos.get("personaje"), datos.get("pais")
            if (isinstance(pid, bool) or not isinstance(pid, int)
                    or isinstance(pais, bool) or not isinstance(pais, int)):
                return 400, {"error": "datos inválidos"}
            if pais != 0 and pais not in PAISES:
                return 400, {"error": "país inválido"}
            j = self.base.jugador(pid)
            if j is None or j.cuenta != cuenta:
                return 403, {"error": "ese personaje no es de tu cuenta"}
            if j.baneado:
                return 403, {"error": "cuenta suspendida en GunBound"}
            self.base.poner_pais(j.enenos_id, pais)
            return 200, {"personajes": self._personajes_json(cuenta)}

        if ruta == "/canje":
            if "ficha" in datos or "personaje" in datos:
                cuenta, err = self._ficha(datos)
                if err:
                    return err
                pid = datos.get("personaje")
                if isinstance(pid, bool) or not isinstance(pid, int):
                    return 400, {"error": "datos inválidos"}
                j = self.base.jugador(pid)
                if j is None or j.cuenta != cuenta:
                    return 403, {"error": "ese personaje no es de tu cuenta"}
                if j.baneado:
                    return 403, {"error": "cuenta suspendida en GunBound"}
                boleto = self.boletos.emitir(j.enenos_id)
                log("CANJE", f"cuenta {cuenta} · personaje {j.enenos_id} ({j.nick}): boleto emitido")
                return 200, {"usuario": str(j.enenos_id), "ticket": boleto,
                             "servidor": self.servidor_para_el_launcher(), "nick": j.nick, "nuevo": False}
            cuenta, err = self._verificar_pase(datos)
            if err:
                return err
            j, nuevo = self.base.crear_si_falta(cuenta, self.aj.oro_inicial, self.aj.cash_inicial)
            if j.baneado:
                return 403, {"error": "cuenta suspendida en GunBound"}
            boleto = self.boletos.emitir(j.enenos_id)
            log("CANJE", f"Eñeños ID {j.enenos_id} ({j.nick}){' · NUEVO' if nuevo else ''}: boleto emitido")
            return 200, {"usuario": str(j.enenos_id), "ticket": boleto, "servidor": self.servidor_para_el_launcher(),
                         "nick": j.nick, "nuevo": nuevo}

        return 404, {"error": "no existe"}

    async def _conexion(self, lector, escritor):
        try:
            cabecera = await asyncio.wait_for(lector.readuntil(b"\r\n\r\n"), timeout=10)
            lineas = cabecera.decode("latin-1").split("\r\n")
            metodo, ruta, _ = (lineas[0].split(" ") + ["", ""])[:3]
            cabeceras = {}
            for l in lineas[1:]:
                if ":" in l:
                    k, v = l.split(":", 1)
                    cabeceras[k.strip().lower()] = v.strip()
            largo = int(cabeceras.get("content-length") or 0)
            if largo > CUERPO_MAX:
                codigo, datos = 413, {"error": "demasiado grande"}
            else:
                cuerpo = await asyncio.wait_for(lector.readexactly(largo), timeout=10) if largo else b""
                try:
                    codigo, datos = self.atender(metodo, ruta, cuerpo, cabeceras)
                except Exception as e:                                  # noqa: BLE001
                    log("WEB", f"⚠ error atendiendo {metodo} {ruta}: {type(e).__name__}: {e}")
                    codigo, datos = 500, {"error": "error interno"}
        except (asyncio.TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError, ValueError, ConnectionError):
            escritor.close()
            return
        b = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        texto = {200: "OK", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found",
                 409: "Conflict", 413: "Payload Too Large", 500: "Internal Server Error", 503: "Service Unavailable"}.get(codigo, "OK")
        escritor.write(f"HTTP/1.1 {codigo} {texto}\r\nContent-Type: application/json; charset=utf-8\r\n"
                       f"Content-Length: {len(b)}\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n".encode("latin-1") + b)
        try:
            await escritor.drain()
        finally:
            escritor.close()
