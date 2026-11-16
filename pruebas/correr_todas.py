# -*- coding: utf-8 -*-
"""correr_todas — el banco entero.   python pruebas/correr_todas.py [-v]

Fuerza PYTHONIOENCODING=utf-8 (una ñ en una consola cp949 da rojo sin bug). Sale con 1 si hay alguna roja: así
lo usan el Dockerfile (si falla, la imagen no se arma) y actualizar.sh.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
env = dict(os.environ, PYTHONIOENCODING="utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")          # la propia salida, también (consola cp949)
except (AttributeError, ValueError):
    pass
detalle = "-v" in sys.argv
rojas = 0
inicio = time.time()
for p in sorted(AQUI.glob("probar_*.py")):
    r = subprocess.run([sys.executable, str(p)], cwd=str(AQUI), env=env, capture_output=True, text=True,
                       encoding="utf-8", timeout=300)
    ultima = (r.stdout.strip().splitlines() or ["(sin salida)"])[-1]
    print(("✔ " if r.returncode == 0 else "✗ ") + ultima, flush=True)
    if r.returncode != 0:
        rojas += 1
        if detalle:
            print(r.stdout[-3000:], r.stderr[-3000:], sep="\n")
print(f"── {rojas} con rojas · {time.time() - inicio:.1f} s")
sys.exit(1 if rojas else 0)
