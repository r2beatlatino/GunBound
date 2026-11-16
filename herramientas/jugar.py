# -*- coding: utf-8 -*-
"""jugar — el «launcher de mesa»: hace lo mismo que el launcher de Eñeños, para probar sin él.

    pase (Cuenta Eñeños, o uno de PRUEBA firmado acá) → POST /canje → registro de Windows → GunBound.exe

    python herramientas/jugar.py                            un jugador de prueba (Eñeños ID 90000001) contra el server local
    python herramientas/jugar.py --veces 3                  tres clientes a la vez (90000001, 90000002, 90000003)
    python herramientas/jugar.py --id 90000005 --ventana 1024x768
    python herramientas/jugar.py --canje https://ensayo…/gunbound/canje --pase <JWT>     con un pase de verdad

Los pases de PRUEBA se firman con la clave de `estado/clave_prueba.json` (la crea `laboratorio.py`): sólo sirven
contra un server arrancado con esa clave pública. ⛔ Nunca en prod.

Abre en VENTANA (ScreenMode=Windowed): varias instancias se ven a la vez y no toman la pantalla.
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request
import winreg
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from servidor import cifrado, pase  # noqa: E402

CLIENTE = Path(r"D:\Gunbound\Cliente-Enenos")
CLAVE_REGISTRO = r"Software\softnyx\Enenos"
CLAVE_PRUEBA = RAIZ / "estado" / "clave_prueba.json"

# lo que el NyxLauncher de Legacy dejaba en el registro (medido), menos lo que depende del server.
# ⚠ Los TIPOS importan: los `bytes` van como REG_BINARY de UN byte (PowerShell los muestra como «{1}», pero NO son el
#   texto «{1}»). Escritos como texto, el juego lee el «{» (0x7B) como modo de interfaz y dibuja el HUD mezclado
#   (medido 16-nov: el panel WEAPON clásico vacío con el selector redondo encima).
REGISTRO_BASE = {
    "ScreenMode": "Windowed", "ScreenDetail": "1600x1200", "MusicVolume": 7, "EffectVolume": 100, "MouseSpeed": 50,
    "Language": 1, "AppID1": 701, "AppID2": 702, "AppID3": 703, "LastServer": 0, "AutoRefresh": 1, "Version": 179,
    "PlayBackStyle": 1, "Background": b"\x01", "ChannelName": b"\x00", "Effect3D": b"\x03", "EffectUse": b"\x01",
    "GameName": b"\x00", "InterfaceMode": b"\x01", "MusicUse": b"\x00", "MidiMode": b"\x01", "ShootingMode": b"\x00",
    "ShowMoon": b"\x00", "ShowOnlineUser": b"\x00", "ShowTurn": b"\x01", "LastID": b"\x00",
}


def escribir_registro(cliente, host, puerto, ventana, interfaz=None):
    """`interfaz`: el modo de interfaz del juego (InterfaceMode {0} / {1}); None = el de REGISTRO_BASE
    (o GB_INTERFAZ en el entorno, para comparar)."""
    import os
    interfaz = interfaz if interfaz is not None else os.environ.get("GB_INTERFAZ")
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, CLAVE_REGISTRO, 0, winreg.KEY_SET_VALUE) as k:
        valores = dict(REGISTRO_BASE, ScreenDetail=ventana, IP=host, port=int(puerto), BuddyIP=host,
                       BuddyPort=int(puerto) - 20, Location=str(cliente) + "\\", Path=str(cliente) + "\\")
        if interfaz is not None:
            valores["InterfaceMode"] = bytes((int(interfaz),))
        for nombre, v in valores.items():
            if isinstance(v, bytes):
                winreg.SetValueEx(k, nombre, 0, winreg.REG_BINARY, v)
            elif isinstance(v, int):
                winreg.SetValueEx(k, nombre, 0, winreg.REG_DWORD, v)
            else:
                winreg.SetValueEx(k, nombre, 0, winreg.REG_SZ, v)


def pase_de_prueba(enenos_id, juego):
    datos = json.loads(CLAVE_PRUEBA.read_text("utf-8"))
    return pase.firmar_pase(bytes.fromhex(datos["semilla"]), juego, enenos_id)


def canjear(url, el_pase):
    req = urllib.request.Request(url, data=json.dumps({"pase": el_pase}).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"⛔ el canje dijo {e.code}: {e.read().decode('utf-8', 'replace')}")


def abrir(cliente, usuario, ticket):
    return subprocess.Popen(cifrado.argumento_cliente(usuario, ticket), executable=str(cliente / "GunBound.exe"),
                            cwd=str(cliente))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canje", default="http://127.0.0.1:8371/canje")
    ap.add_argument("--juego", default="gunbound", help="el aud del pase de prueba (gunbound / gunbound-prueba)")
    ap.add_argument("--pase", help="un pase de verdad de Cuenta Eñeños (si no, se firma uno de prueba)")
    ap.add_argument("--id", type=int, default=90000001)
    ap.add_argument("--veces", type=int, default=1)
    ap.add_argument("--cliente", default=str(CLIENTE))
    ap.add_argument("--ventana", default="1600x1200")
    a = ap.parse_args()
    cliente = Path(a.cliente)
    procesos = []
    for i in range(a.veces):
        el_pase = a.pase or pase_de_prueba(a.id + i, a.juego)
        r = canjear(a.canje, el_pase)
        host, _, puerto = r["servidor"].rpartition(":")
        escribir_registro(cliente, host, puerto, a.ventana)
        p = abrir(cliente, r["usuario"], r["ticket"])
        procesos.append(p)
        print(f"✔ {r['nick']} (Eñeños ID {r['usuario']}) → {r['servidor']} · PID {p.pid}", flush=True)
        time.sleep(3)
    return procesos


if __name__ == "__main__":
    main()
