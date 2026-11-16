# -*- coding: utf-8 -*-
"""El server entero en un proceso:  python -m servidor

    broker (lista de mundos)  ·  mundo (TCP + UDP)  ·  web (canje del pase y salud)

Todo se configura con variables de entorno (servidor/ajustes.py, despliegue/ejemplo.env).
"""
import asyncio
import signal
import sys

from .ajustes import cargar
from .base import Base
from .boletos import Boletos
from .broker import Broker
from .mundo import Mundo
from .pase import Verificador, bajar_clave_publica, parsear_clave_publica
from .registro import log
from .web import Web


class Server:
    """Las tres piezas juntas. Las pruebas lo levantan con puertos 0 (los elige el sistema)."""

    def __init__(self, ajustes, clave_publica=None):
        self.aj = ajustes
        self.base = Base(ajustes.ruta_base)
        self.boletos = Boletos(ajustes.boleto_horas)
        clave = clave_publica or parsear_clave_publica(ajustes.clave_publica)
        if clave is None and ajustes.url_cuentas:
            clave = bajar_clave_publica(ajustes.url_cuentas)
        self.verificador = Verificador(ajustes.pase_juego, clave)
        self.mundo = Mundo(ajustes, self.base, self.boletos)
        self.broker = Broker(ajustes, lambda: len(self.mundo.sesiones))
        self.web = Web(ajustes, self.verificador, self.boletos, self.base, lambda: len(self.mundo.sesiones),
                       lambda: self.broker.puerto)

    async def arrancar(self):
        await self.mundo.arrancar()
        # el broker anuncia el puerto del mundo: si se pidió el 0 (pruebas), recién ahora se sabe cuál es
        if self.aj.puerto_mundo == 0:
            self.aj.puerto_mundo = self.mundo.puerto
            self.aj.puerto_mundo_publico = self.mundo.puerto
        await self.broker.arrancar()
        await self.web.arrancar()
        if not self.verificador.clave:
            log("MAIN", "⚠ SIN la clave pública de Cuenta Eñeños (GB_CUENTAS_CLAVE_PUBLICA o GB_CUENTAS_URL): "
                        "nadie puede entrar hasta que esté")
        log("MAIN", f"GunBound «{self.aj.entorno}» listo · pase «{self.aj.pase_juego}» · base {self.aj.ruta_base}")

    def cerrar(self):
        self.web.cerrar()
        self.broker.cerrar()
        self.mundo.cerrar()
        self.base.cerrar()


async def principal():
    srv = Server(cargar())
    await srv.arrancar()
    fin = asyncio.Event()
    lazo = asyncio.get_running_loop()
    for sig in (getattr(signal, "SIGTERM", None), getattr(signal, "SIGINT", None)):
        if sig is not None:
            try:
                lazo.add_signal_handler(sig, fin.set)
            except (NotImplementedError, RuntimeError):
                pass                                      # Windows: Ctrl+C corta igual
    try:
        await fin.wait()
    finally:
        log("MAIN", "cerrando")
        srv.cerrar()


if __name__ == "__main__":
    try:
        asyncio.run(principal())
    except KeyboardInterrupt:
        sys.exit(0)
