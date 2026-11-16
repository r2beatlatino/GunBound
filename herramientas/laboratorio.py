# -*- coding: utf-8 -*-
"""laboratorio — el server en ESTA PC, con una clave de PRUEBA en lugar de la de Cuenta Eñeños.

    python herramientas/laboratorio.py            arranca el server (Ctrl+C para cortar)
    python herramientas/laboratorio.py --clave    sólo crea/muestra la clave de prueba

La base queda en `estado/` (gitignorado). Los pases de prueba los firma `jugar.py` con la misma clave.
⛔ La clave de prueba no va a ningún server de verdad: con ella cualquiera se firma un pase.
"""
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from servidor import firma_ed25519 as ed  # noqa: E402

CLAVE = RAIZ / "estado" / "clave_prueba.json"


def clave_prueba():
    if not CLAVE.exists():
        CLAVE.parent.mkdir(parents=True, exist_ok=True)
        semilla = secrets.token_bytes(32)
        CLAVE.write_text(json.dumps({"semilla": semilla.hex(), "publica": ed.publica(semilla).hex(),
                                     "aviso": "SOLO laboratorio: con esta semilla cualquiera firma un pase"}, indent=1))
    return json.loads(CLAVE.read_text("utf-8"))


if __name__ == "__main__":
    c = clave_prueba()
    if "--clave" in sys.argv:
        print(c["publica"])
        sys.exit(0)
    env = dict(os.environ, GB_ENTORNO=os.environ.get("GB_ENTORNO", "local"), GB_ESTADO=str(RAIZ / "estado"),
               GB_CUENTAS_CLAVE_PUBLICA=c["publica"], GB_GM=os.environ.get("GB_GM", "90000001"), GB_TRAZA=os.environ.get("GB_TRAZA", "1"),
               PYTHONIOENCODING="utf-8")
    sys.exit(subprocess.call([sys.executable, "-m", "servidor"], cwd=str(RAIZ), env=env))
