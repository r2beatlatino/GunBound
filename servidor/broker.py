# -*- coding: utf-8 -*-
"""broker — la lista de mundos. Es lo PRIMERO que toca el cliente (la IP y el puerto del registro de Windows).

    0x1013 → 0x1312 (00 00), con la secuencia fija 0xCBEB (el broker no lleva la cuenta en el primer mensaje)
    0x1100 → 0x1102: [00 00 01][cantidad] + un mundo por renglón:
        lugar, 0, 0 · largo + nombre · largo + descripción · IP (4) · puerto (BE) · ocupación (BE) ×2 · cupo (BE) ·
        ⚠ Legacy: 3 bytes más ANTES de «habilitado» (rango mínimo FB, máximo 100, 0). Sin ellos lee el «habilitado»
        corrido y muestra el mundo «In Maintenance».
        · habilitado

La IP que se anuncia: `GB_IP_PUBLICA` si está; si no, la IP por la que el cliente llegó a ESTE broker (sirve en la
misma PC y en la LAN; en un VPS detrás de NAT hay que ponerla, porque la máquina no ve su IP pública).
"""
import asyncio
import socket

from . import paquete
from .paquete import con_largo, u8, u16_be
from .registro import log


class Broker:
    def __init__(self, ajustes, contar_en_linea):
        self.aj = ajustes
        self.contar = contar_en_linea
        self._servidor = None

    async def arrancar(self):
        self._servidor = await asyncio.start_server(self._conexion, self.aj.escucha, self.aj.puerto_broker,
                                                    reuse_address=True)
        log("BROKER", f"escuchando {self.aj.escucha}:{self.aj.puerto_broker} · mundo «{self.aj.nombre_mundo}»")

    def cerrar(self):
        if self._servidor:
            self._servidor.close()

    @property
    def puerto(self):
        return self._servidor.sockets[0].getsockname()[1] if self._servidor else self.aj.puerto_broker

    def ip_a_anunciar(self, escritor):
        if self.aj.ip_publica:
            try:
                return socket.gethostbyname(self.aj.ip_publica)       # acepta un nombre: se resuelve acá
            except OSError:
                log("BROKER", f"⚠ no pude resolver GB_IP_PUBLICA={self.aj.ip_publica}")
        local = escritor.get_extra_info("sockname")
        return local[0] if local else "127.0.0.1"

    def lista(self, ip):
        aj = self.aj
        en_linea = self.contar()
        desc = f"{aj.descripcion_mundo}\r\n[{en_linea}/{aj.capacidad_mundo}] en linea"
        renglon = (bytes((0, 0, 0)) + con_largo(aj.nombre_mundo) + con_largo(desc) + bytes(int(p) for p in ip.split("."))
                   + u16_be(aj.puerto_mundo_publico) + u16_be(en_linea) + u16_be(en_linea) + u16_be(aj.capacidad_mundo)
                   + bytes((0xFB, 100, 0)) + u8(1))
        return bytes((0, 0, 1)) + u8(1) + renglon

    async def _conexion(self, lector, escritor):
        cortador = paquete.Cortador()
        try:
            while True:
                pedazo = await asyncio.wait_for(lector.read(1024), timeout=60)
                if not pedazo:
                    break
                for crudo in cortador.meter(pedazo):
                    comando = crudo[4] | (crudo[5] << 8)
                    if comando == 0x1013:
                        escritor.write(paquete.armar(0, 0x1312, b"\x00\x00", secuencia_fija=0xCBEB))
                    elif comando == 0x1100:
                        ip = self.ip_a_anunciar(escritor)
                        escritor.write(paquete.armar(0, 0x1102, self.lista(ip)))
                    else:
                        log("BROKER", f"comando desconocido 0x{comando:04X}")
                await escritor.drain()
        except (asyncio.TimeoutError, ConnectionError, ValueError):
            pass
        finally:
            escritor.close()
