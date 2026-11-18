# -*- coding: utf-8 -*-
"""lista_del_cliente — la LISTA de archivos del cliente de GunBound para el launcher, con el mismo formato que la de
EDA (`launcher_tauri/src-tauri/src/eda.rs`, `validar_manifiesto`). SIN firmar: la firma la pone la clave de
publicación de la plataforma, igual que la de EDA (ver `documentacion/PARA_EL_LAUNCHER.md` §5).

    python herramientas/lista_del_cliente.py --version 2026.11.19 --base https://cdn.xn--eeos-gqab.link/gunbound/2026.11.19/ \
        --servidor juego.eñeños.link:8372 --canje https://eñeños.link/gunbound/canje  [--cliente D:\\Gunbound\\Cliente-Enenos]
        [--partes CARPETA]

Escribe `lista_gunbound_<version>.json` en la carpeta actual:
    {"juego": "gunbound", "version", "base", "servidor", "canje", "exe": "GunBound.exe",
     "del_usuario": [...], "files": [{"path", "size", "md5"[, "partes": [{"path", "size", "md5"}, …]]}]}

★ La BASE es la CDN (desde el 18-nov): `https://cdn.xn--eeos-gqab.link/gunbound/<versión>/` (Cloudflare delante del
VPS, caché de 1 año). ⛔ Por eso la carpeta de una versión NO se reusa con otros contenidos: versión nueva, carpeta nueva.

★ PARTES: el plan gratis de Cloudflare no guarda archivos de más de 512 MB (graphics.xfs pesa 650). Con `--partes
CARPETA`, cada archivo de más de `MAX_SIN_PARTIR` se corta en pedazos de `PEDAZO` bytes (el último, lo que sobre),
que se escriben en CARPETA con la misma ruta + `.p1`, `.p2`… (se suben junto al cliente, en la misma carpeta de la
versión) y se declaran en `partes`, EN ORDEN. El launcher baja las partes, las junta y comprueba el `md5` y el `size`
del archivo ENTERO (el de la entrada). Un launcher que no conoce `partes` las ignora y baja el archivo entero.

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
MAX_SIN_PARTIR = 500 * 1024 * 1024        # Cloudflare (plan gratis) no guarda más de 512 MB por archivo
PEDAZO = 256 * 1024 * 1024


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def partir(p, ruta, carpeta, pedazo=PEDAZO):
    """Corta `p` en pedazos de `pedazo` bytes en `carpeta`/<ruta>.p1… y devuelve su lista [{path, size, md5}]."""
    partes = []
    with open(p, "rb") as f:
        while datos := f.read(pedazo):
            nombre = f"{ruta}.p{len(partes) + 1}"
            destino = Path(carpeta) / nombre
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(datos)
            partes.append({"path": nombre, "size": len(datos), "md5": hashlib.md5(datos).hexdigest()})
    return partes


def armar(cliente, version, base, servidor, canje, carpeta_partes=None, max_sin_partir=MAX_SIN_PARTIR,
          pedazo=PEDAZO):
    cliente = Path(cliente)
    files = []
    for p in sorted(cliente.rglob("*")):
        if not p.is_file() or p.name in NO_VA:
            continue
        ruta = p.relative_to(cliente).as_posix()
        if not RX_RUTA.match(ruta) or ".." in ruta.split("/"):
            raise SystemExit(f"⛔ «{ruta}» no pasa las reglas de ruta del launcher")
        entrada = {"path": ruta, "size": p.stat().st_size, "md5": md5(p)}
        if carpeta_partes and entrada["size"] > max_sin_partir:
            entrada["partes"] = partir(p, ruta, carpeta_partes, pedazo)
            if sum(x["size"] for x in entrada["partes"]) != entrada["size"]:
                raise SystemExit(f"⛔ {ruta}: las partes no suman el archivo")
        files.append(entrada)
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
    ap.add_argument("--partes", help="carpeta donde escribir los pedazos de los archivos de más de 500 MB")
    a = ap.parse_args()
    lista = armar(a.cliente, a.version, a.base, a.servidor, a.canje, a.partes)
    salida = Path(f"lista_gunbound_{a.version}.json")
    salida.write_text(json.dumps(lista, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    total = sum(f["size"] for f in lista["files"])
    partidos = [f"{f['path']} en {len(f['partes'])}" for f in lista["files"] if "partes" in f]
    print(f"✔ {salida}: {len(lista['files'])} archivos, {total / 1e6:.0f} MB"
          + (f" · partidos: {', '.join(partidos)} (los pedazos, en {a.partes})" if partidos else ""))
