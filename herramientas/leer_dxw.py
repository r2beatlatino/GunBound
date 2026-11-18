# -*- coding: utf-8 -*-
"""leer_dxw — dice qué opciones de DxWnd prende un `dxwnd.dxw`, con los NOMBRES que trae el propio dxwnd.dll.

    python herramientas/leer_dxw.py                         el del cliente (D:\\Gunbound\\Cliente-Enenos)
    python herramientas/leer_dxw.py otra\\carpeta\\dxwnd.dxw

DxWnd (v2.05.15, el que trae Legacy) guarda sus opciones como bits en `flag0`, `flagg0`, `flagh0`… En el dll hay, para
su log, una tabla de 32 nombres por palabra (en 0x100E7B20, una cada 0x80 bytes, en el orden flag, flagg, flagh, flagi,
flagj, flagk, flagl, flagm, flagn, flago, flagp): de ahí salen los nombres, no de la memoria. Ver CLIENTE.md «La
ventana» para lo medido (pantalla completa = coord 3 + KEEPASPECTRATIO + HIDEDESKTOP).
"""
import re
import struct
import sys
from pathlib import Path

import pefile

CLIENTE = Path(r"D:\Gunbound\Cliente-Enenos")
PALABRAS = ["flag", "flagg", "flagh", "flagi", "flagj", "flagk", "flagl", "flagm", "flagn", "flago", "flagp"]
TABLA = 0x100E7B20


def nombres(dll):
    pe = pefile.PE(str(dll))
    img, base = pe.get_memory_mapped_image(), pe.OPTIONAL_HEADER.ImageBase

    def texto(va):
        o = va - base
        return img[o:img.find(b"\0", o)].decode("latin1")

    salida = {}
    for i, palabra in enumerate(PALABRAS):
        t = TABLA - base + i * 0x80
        salida[palabra] = [texto(struct.unpack_from("<I", img, t + 4 * b)[0]) for b in range(32)]
    if salida["flag"][0] != "UNNOTIFY" or salida["flagg"][27] != "WINDOWIZE":
        raise SystemExit(f"⛔ {dll}: la tabla de nombres no está donde en la v2.05.15 (¿otro DxWnd?)")
    return salida


def leer(dxw, dll):
    valores = dict(re.findall(r"^(\w+?)0=(.*)$", Path(dxw).read_text("latin1"), re.M))
    tabla = nombres(dll)
    for palabra in PALABRAS:
        if palabra in valores:
            v = int(valores[palabra])
            print(f"  {palabra}0={v:<11} {' '.join(tabla[palabra][b] for b in range(32) if v >> b & 1)}")
    for k in ("coord", "posx", "posy", "sizx", "sizy", "initresw", "initresh"):
        print(f"  {k}0={valores.get(k)}")


if __name__ == "__main__":
    dxw = Path(sys.argv[1]) if len(sys.argv) > 1 else CLIENTE / "dxwnd.dxw"
    leer(dxw, dxw.parent / "dxwnd.dll")
