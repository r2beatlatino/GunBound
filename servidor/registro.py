# -*- coding: utf-8 -*-
"""registro — una línea por suceso, con hora y tema. Va a la salida (Docker la guarda) y nada más."""
import sys
import time

_silencio = False


def silenciar(si=True):
    """Las pruebas lo callan para que la salida sea sólo el resultado."""
    global _silencio
    _silencio = si


def log(tema, texto):
    if _silencio:
        return
    linea = f"{time.strftime('%Y-%m-%d %H:%M:%S')} [{tema}] {texto}"
    try:
        print(linea, flush=True)
    except UnicodeEncodeError:                     # ⚠ la consola de Windows en cp949: no morir por una ñ
        sys.stdout.buffer.write((linea + "\n").encode("utf-8", "replace"))
        sys.stdout.flush()
