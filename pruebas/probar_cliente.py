# -*- coding: utf-8 -*-
"""probar_cliente — la herramienta que arma el cliente de Eñeños (herramientas/parchar_cliente.py).

Necesita el GunBound Legacy original (C:\\GunBound-Legacy). Donde no está (Docker, otra PC) se SALTA y lo dice:
no da verde de mentira.
"""
import sys
from pathlib import Path

from arnes import Banco, RAIZ

sys.path.insert(0, str(RAIZ / "herramientas"))
try:
    import parchar_cliente as pc  # noqa: E402
except ImportError:                                  # en la imagen de Docker no va herramientas/
    print("probar_cliente: SALTADA · no está herramientas/parchar_cliente.py (¿adentro del contenedor?)")
    sys.exit(0)

b = Banco("probar_cliente")
exe = pc.ORIGEN / "GunBound.exe"
if not exe.exists():
    print(f"probar_cliente: SALTADA · no está {exe}")
    sys.exit(0)

original = exe.read_bytes()
b.igual(pc.sha256(exe), pc.SHA_ORIGINAL, "el original es el que se midió")
b.ver(all(v == "original" for v in pc.comprobar(exe).values()), "el original no tiene ningún parche")
parchado = pc.parchar(original)
b.ver(parchado != original and len(parchado) == len(original), "parchar cambia bytes y no el tamaño")
cambiados = sum(1 for x, y in zip(original, parchado) if x != y)
esperado = sum(sum(1 for x, y in zip(v, n) if x != y) for _, _, v, n in pc.PARCHES)
b.igual(cambiados, esperado, "cambia EXACTAMENTE los bytes de los parches, ni uno más")
b.igual(pc.parchar(parchado), parchado, "parchar dos veces no cambia nada")
otro = bytearray(original)
otro[0xC3EC] ^= 0xFF
try:
    pc.parchar(bytes(otro))
    b.ver(False, "control: con un exe distinto tiene que negarse")
except SystemExit:
    b.ver(True, "")
dx = pc.ORIGEN / "dxwnd.dll"
b.igual(pc.sha256(dx), pc.SHA_DXWND, "el DxWnd es el que se midió")
b.ver(pc.parchar(dx.read_bytes(), pc.PARCHES_DXWND) != dx.read_bytes(), "el parche de DxWnd cambia algo")
armado = pc.DESTINO / "GunBound.exe"
if armado.exists():
    b.ver(all(v == "parchado" for v in pc.comprobar(armado).values()), f"el cliente armado ({armado}) tiene todo")
b.fin()
