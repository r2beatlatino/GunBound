# -*- coding: utf-8 -*-
"""lista_del_cliente — la LISTA de archivos del cliente de GunBound para el launcher, con el mismo formato que la de
EDA (`launcher_tauri/src-tauri/src/eda.rs`, `validar_manifiesto`). SIN firmar: la firma la pone la clave de
publicación de la plataforma, igual que la de EDA (ver `documentacion/PARA_EL_LAUNCHER.md` §5).

    python herramientas/lista_del_cliente.py --version 1.0.0 --base https://cdn…/gunbound/1.0.0/ \
        --servidor juego.eñeños.link:8372 --canje https://eñeños.link/gunbound/canje  [--cliente D:\\Gunbound\\Cliente-Enenos]

Escribe `lista_gunbound_<version>.json` en la carpeta actual:
    {"juego": "gunbound", "version", "base", "servidor", "canje", "exe": "GunBound.exe",
     "del_usuario": [...], "files": [{"path", "size", "md5"}]}

Las reglas de `eda.rs` que tiene que cumplir cada ruta: `^[A-Za-z0-9_.\\- /]+$`, con `/`, sin `..` ni `/` adelante.
Si un archivo del cliente no las cumple, se corta acá (no en la PC del jugador).
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

CLIENTE = Path(r"D:\Gunbound\Cliente-Enenos")
RX_RUTA = re.compile(r"^[A-Za-z0-9_.\- /]+$")
# lo que escribe el JUEGO o el jugador: no va en la lista (el launcher no lo pisa)
NO_VA = {"MuteList.txt", "dxwnd.ini"}
DEL_USUARIO = ["MuteList.txt"]


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def armar(cliente, version, base, servidor, canje):
    cliente = Path(cliente)
    files = []
    for p in sorted(cliente.rglob("*")):
        if not p.is_file() or p.name in NO_VA:
            continue
        ruta = p.relative_to(cliente).as_posix()
        if not RX_RUTA.match(ruta) or ".." in ruta.split("/"):
            raise SystemExit(f"⛔ «{ruta}» no pasa las reglas de ruta del launcher")
        files.append({"path": ruta, "size": p.stat().st_size, "md5": md5(p)})
    if not any(f["path"] == "GunBound.exe" for f in files):
        raise SystemExit(f"⛔ {cliente} no tiene GunBound.exe")
    return {"juego": "gunbound", "version": version, "base": base, "servidor": servidor, "canje": canje,
            "exe": "GunBound.exe", "del_usuario": DEL_USUARIO, "files": files}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--servidor", required=True)
    ap.add_argument("--canje", required=True)
    ap.add_argument("--cliente", default=str(CLIENTE))
    a = ap.parse_args()
    lista = armar(a.cliente, a.version, a.base, a.servidor, a.canje)
    salida = Path(f"lista_gunbound_{a.version}.json")
    salida.write_text(json.dumps(lista, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    total = sum(f["size"] for f in lista["files"])
    print(f"✔ {salida}: {len(lista['files'])} archivos, {total / 1e6:.0f} MB")
