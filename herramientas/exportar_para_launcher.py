# -*- coding: utf-8 -*-
"""exportar_para_launcher — lo que la pantalla de personajes del launcher necesita sacar del CLIENTE de GunBound.

    python herramientas/exportar_para_launcher.py [CARPETA]        (por omisión D:\\Gunbound\\para_el_launcher)

Escribe, FUERA del repo (es arte de Softnyx, como el cliente):
    rangos/<valor>.png   los íconos de rango del juego (`rank2.img`, 25×15, cuadro = valor + 5): 19 = pollito,
                         20 = GM, −4 = dragón plateado; del 21 en adelante, los especiales (VIP, coronas…).
                         Fondo transparente (el magenta del juego).
    paises.json          lo mismo que `GET /gunbound/paises` del server: [{"n", "nombre", "iso"}] (n = número del juego).
    rangos.json          {valor: nombre} de `servidor/rangos.py` + los cortes de GP (`TABLA_GP`).

El formato de los .img (lo midió Codex, `ver_imagenes.py`): [4][cantidad u32] y por cuadro una cabecera de 40
bytes (flag en +0: 0 = RGB565 crudo, otro = filas RLE; ancho/alto en +4/+8; largo de datos en +36) + datos.
"""
import json
import struct
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from servidor import rangos  # noqa: E402
from servidor.web import LISTA_PAISES  # noqa: E402
from xfs import XFS  # noqa: E402

CLIENTE = Path(r"D:\Gunbound\Cliente-Enenos")
DESTINO = Path(r"D:\Gunbound\para_el_launcher")


def cuadros(data):
    n = struct.unpack_from("<I", data, 4)[0]
    p, out = 8, []
    for _ in range(n):
        flag = data[p]
        w, h = struct.unpack_from("<II", data, p + 4)
        sz = struct.unpack_from("<I", data, p + 36)[0]
        extra = struct.unpack_from("<I", data, p + 20)[0] == 1
        out.append((flag, w, h, data[p + 40:p + 40 + sz]))
        p += 40 + sz
        if extra:
            p += 4 + struct.unpack_from("<I", data, p)[0]
    return out


def imagen(cuadro):
    """→ PIL RGBA: el RLE deja transparente lo que no pinta; en el crudo, el magenta puro es el transparente."""
    from PIL import Image
    flag, w, h, b = cuadro
    px = bytearray(w * h * 4)
    def poner(i, v):
        r, g, bl = ((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31
        px[i * 4:i * 4 + 4] = bytes((r, g, bl, 0 if (r, g, bl) == (255, 0, 255) else 255))
    if flag == 0:
        for i in range(w * h):
            poner(i, struct.unpack_from("<H", b, i * 2)[0])
    else:
        p = 0
        for y in range(h):
            largo = struct.unpack_from("<H", b, p)[0]
            fin = p + 2 * largo
            p += 2
            tramos = struct.unpack_from("<H", b, p)[0]
            p += 2
            x = 0
            for _ in range(tramos):
                salto, cuantos = struct.unpack_from("<HH", b, p)
                p += 4
                x += salto
                for _ in range(cuantos):
                    if x < w:
                        poner(y * w + x, struct.unpack_from("<H", b, p)[0])
                    p += 2
                    x += 1
            p = fin
    return Image.frombytes("RGBA", (w, h), bytes(px))


def exportar(cliente=CLIENTE, destino=DESTINO):
    destino = Path(destino)
    (destino / "rangos").mkdir(parents=True, exist_ok=True)
    rank2 = cuadros(XFS(Path(cliente) / "graphics.xfs").read("rank2.img"))
    for i, c in enumerate(rank2):
        imagen(c).save(destino / "rangos" / f"{i - 5}.png")
    (destino / "paises.json").write_text(json.dumps({"paises": LISTA_PAISES}, ensure_ascii=False, indent=1) + "\n",
                                         encoding="utf-8", newline="\n")
    (destino / "rangos.json").write_text(json.dumps({
        "nombres": {str(k): v for k, v in sorted(rangos.NOMBRES.items())},
        "gp_minimo": [{"gp": g, "rango": r} for g, r in rangos.TABLA_GP],
        "pollito": rangos.POLLITO, "gm": rangos.GM,
        "icono": "rangos/<valor>.png (25x15, transparente)"}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n")
    print(f"✔ {destino}: {len(rank2)} íconos de rango ({-5}..{len(rank2) - 6}), {len(LISTA_PAISES)} países")
    return destino


if __name__ == "__main__":
    exportar(destino=sys.argv[1] if len(sys.argv) > 1 else DESTINO)
