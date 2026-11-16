# -*- coding: utf-8 -*-
"""paquete — el sobre de cada mensaje de GunBound (TCP), y cómo se corta el chorro en mensajes.

    bytes 0-1   largo TOTAL (cabecera incluida), little endian
    bytes 2-3   secuencia: sale de la SUMA de todo lo que este lado ya mandó por esa conexión
    bytes 4-5   comando
    bytes 6-…   el cuerpo

La secuencia (de `GunBoundServ2.exe`, función 0x40B760): el cliente la comprueba en lo que recibe, así que el
server tiene que llevar la cuenta de cuántos bytes mandó por cada conexión. Lo que manda el cliente NO se comprueba.
"""
import struct

CABECERA = 6
LARGO_MAX = 0x4000                 # un mensaje del juego nunca pasa de unos cientos de bytes; más es basura


def secuencia(total_enviado):
    """`total_enviado` = lo ya mandado por la conexión + el largo de ESTE mensaje."""
    return (((total_enviado * 0x43FD) & 0xFFFF) - 0x53FD) & 0xFFFF


def armar(ya_enviado, comando, cuerpo, secuencia_fija=None):
    """El mensaje entero, listo para mandar. `ya_enviado` = bytes mandados antes por esta conexión."""
    largo = len(cuerpo) + CABECERA
    sec = secuencia(ya_enviado + largo) if secuencia_fija is None else secuencia_fija
    return struct.pack("<HHH", largo, sec, comando) + bytes(cuerpo)


def leer_cabecera(crudo):
    largo, sec, comando = struct.unpack_from("<HHH", crudo, 0)
    return largo, sec, comando


class Cortador:
    """Recibe pedazos del TCP (pueden venir mensajes pegados o partidos) y devuelve mensajes enteros."""

    def __init__(self):
        self._pend = bytearray()

    def meter(self, pedazo):
        self._pend.extend(pedazo)
        salida = []
        while len(self._pend) >= 2:
            largo = self._pend[0] | (self._pend[1] << 8)
            if largo < CABECERA or largo > LARGO_MAX:
                raise ValueError(f"largo inválido {largo}")
            if len(self._pend) < largo:
                break
            crudo = bytes(self._pend[:largo])
            del self._pend[:largo]
            salida.append(crudo)
        return salida

    @property
    def pendiente(self):
        return len(self._pend)


# ── ayudas para armar cuerpos (todo es little endian salvo donde se dice) ─────────────────────────────────────

def u8(v):
    return bytes((v & 0xFF,))


def u16(v):
    return struct.pack("<H", v & 0xFFFF)


def u32(v):
    return struct.pack("<I", v & 0xFFFFFFFF)


def u16_be(v):
    return struct.pack(">H", v & 0xFFFF)


def fijo(texto, largo):
    """Texto en un campo de largo fijo, relleno con ceros (y cortado si sobra)."""
    b = texto.encode("latin-1", "replace") if isinstance(texto, str) else bytes(texto)
    return b[:largo].ljust(largo, b"\0")


def con_largo(texto):
    """Un byte con el largo y después el texto (el formato de los nombres de sala y del mundo)."""
    b = texto.encode("latin-1", "replace")[:255]
    return u8(len(b)) + b


def texto_c(b):
    """Lee un texto hasta el primer cero."""
    b = bytes(b)
    i = b.find(b"\0")
    return (b if i < 0 else b[:i]).decode("latin-1")
