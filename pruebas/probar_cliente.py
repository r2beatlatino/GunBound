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
# parche 9: el call de 0x515C07 cae en el cave, y el cave vuelve justo después del push que reemplazó
_rel = lambda datos, en: int.from_bytes(datos[en + 1:en + 5], "little", signed=True) + 0x400000 + en + 5  # noqa: E731
b.igual((parchado[0x115C07], hex(_rel(parchado, 0x115C07))), (0xE8, "0x55ed00"), "medidor: el call va al cave")
_fin = 0x15ED79
b.igual((parchado[_fin], hex(_rel(parchado, _fin))), (0xE9, "0x515c0c"), "medidor: el cave vuelve a 0x515C0C")
b.igual(original[0x15ED00:0x15ED00 + 180], bytes(180), "control: en el original ahí hay sólo ceros (relleno)")
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
