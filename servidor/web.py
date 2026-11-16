# -*- coding: utf-8 -*-
"""web — el HTTP del server: el CANJE (pase → boleto) y la salud. Escucha en 127.0.0.1: afuera va detrás de Caddy
(HTTPS), porque el boleto es un secreto.

    GET  /salud                         {"ok": true, "entorno", "juego", "en_linea"}
    POST /canje  {"pase": "<JWT>"}      200 {"usuario": "<Eñeños ID>", "ticket": "<12>", "servidor": "host:puerto"}
                                        401 pase inválido · 409 pase ya usado · 503 sin la clave de Cuenta Eñeños
(las rutas se aceptan también con el prefijo /gunbound o /gunbound-prueba, como las pase Caddy)

Es el MISMO contrato que el canje de EDA: el launcher lo usa igual.
"""
import asyncio
import json

from .registro import log

CUERPO_MAX = 8192


class Web:
    def __init__(self, ajustes, verificador, boletos, base, contar_en_linea, puerto_broker):
        self.aj = ajustes
        self.ver = verificador
        self.boletos = boletos
        self.base = base
        self.contar = contar_en_linea
        self.puerto_broker = puerto_broker
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

    # ── las rutas ─────────────────────────────────────────────────────────────────────────────────────────
    def atender(self, metodo, ruta, cuerpo):
        for prefijo in ("/gunbound-prueba", "/gunbound"):
            if ruta.startswith(prefijo + "/"):
                ruta = ruta[len(prefijo):]
                break
        ruta = ruta.split("?")[0]
        if metodo == "GET" and ruta == "/salud":
            return 200, {"ok": True, "entorno": self.aj.entorno, "juego": self.aj.pase_juego, "en_linea": self.contar()}
        if metodo == "POST" and ruta == "/canje":
            try:
                pase = json.loads(cuerpo.decode("utf-8") or "{}").get("pase", "")
            except (ValueError, AttributeError):
                return 400, {"error": "cuerpo inválido"}
            if not self.ver.clave:
                return 503, {"error": "el server no tiene la clave de Cuenta Eñeños"}
            enenos_id, motivo = self.ver.comprobar(pase)
            if enenos_id is None:
                log("CANJE", f"rechazado: {motivo}")
                return (409 if motivo == "pase ya usado" else 401), {"error": motivo}
            j, nuevo = self.base.crear_si_falta(enenos_id, self.aj.oro_inicial, self.aj.cash_inicial)
            if j.baneado:
                return 403, {"error": "cuenta suspendida en GunBound"}
            boleto = self.boletos.emitir(enenos_id)
            log("CANJE", f"Eñeños ID {enenos_id} ({j.nick}){' · NUEVO' if nuevo else ''}: boleto emitido")
            return 200, {"usuario": str(enenos_id), "ticket": boleto, "servidor": self.servidor_para_el_launcher(),
                         "nick": j.nick, "nuevo": nuevo}
        return 404, {"error": "no existe"}

    async def _conexion(self, lector, escritor):
        try:
            cabecera = await asyncio.wait_for(lector.readuntil(b"\r\n\r\n"), timeout=10)
            lineas = cabecera.decode("latin-1").split("\r\n")
            metodo, ruta, _ = (lineas[0].split(" ") + ["", ""])[:3]
            largo = 0
            for l in lineas[1:]:
                if l.lower().startswith("content-length:"):
                    largo = int(l.split(":", 1)[1].strip() or 0)
            if largo > CUERPO_MAX:
                codigo, datos = 413, {"error": "demasiado grande"}
            else:
                cuerpo = await asyncio.wait_for(lector.readexactly(largo), timeout=10) if largo else b""
                try:
                    codigo, datos = self.atender(metodo, ruta, cuerpo)
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
