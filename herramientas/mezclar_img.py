# -*- coding: utf-8 -*-
"""mezclar_img — un .img del Legacy con UNO de sus cuadros sacado de otro .img (el original de GIS 557).

    python herramientas/mezclar_img.py LEGACY.img ORIGINAL.img SALIDA.img [cuadro=0]

Para qué: en el lobby (`gamelist_back.img`) y la sala (`ready_back.img`) el Legacy pintó su marca sobre el FONDO
(cuadro 0, 800×600: el logo «GunBound LEGACY» en el chat del lobby, «OPCIONES DE SALA» en la sala). Los demás
cuadros (botones, marcos, flechas) se dejan como los trae el Legacy: el cliente los dibuja en posiciones fijas y en
`gamelist_back` el cuadro 1 hasta tiene otro tamaño en el 557 (117×29 contra 20×21).

Formato (el de `ver_imagenes.py` de Codex): [4 bytes][cantidad u32] y por cuadro una cabecera de 40 bytes (flag,
ancho y alto en +4/+8, variante extra en +20, largo de los datos en +36) + los datos (+ un bloque extra si la
variante es 1). Se copian los BYTES del cuadro tal cual: no se recomprime nada.
"""
import struct
import sys
from pathlib import Path


def partir(data):
    """→ (cabecera de 8 bytes, [bytes crudos de cada cuadro])."""
    n = struct.unpack_from("<I", data, 4)[0]
    if n > 10000:
        raise ValueError("cantidad de cuadros imposible")
    p, cuadros = 8, []
    for _ in range(n):
        ini = p
        sz = struct.unpack_from("<I", data, p + 36)[0]
        extra = struct.unpack_from("<I", data, p + 20)[0] == 1
        p += 40 + sz
        if extra:
            p += 4 + struct.unpack_from("<I", data, p)[0]
        cuadros.append(bytes(data[ini:p]))
    if p != len(data):
        raise ValueError(f"el .img no cierra: {p} de {len(data)}")
    return bytes(data[:8]), cuadros


def tamano(cuadro):
    return struct.unpack_from("<II", cuadro, 4)


def mezclar(legacy, original, cuadro=0):
    cab, cl = partir(legacy)
    _, co = partir(original)
    if tamano(cl[cuadro]) != tamano(co[cuadro]):
        raise SystemExit(f"⛔ el cuadro {cuadro} no mide lo mismo: {tamano(cl[cuadro])} contra {tamano(co[cuadro])}")
    cl[cuadro] = co[cuadro]
    salida = cab + b"".join(cl)
    assert len(partir(salida)[1]) == len(cl)
    return salida


if __name__ == "__main__":
    a = sys.argv[1:]
    datos = mezclar(Path(a[0]).read_bytes(), Path(a[1]).read_bytes(), int(a[3]) if len(a) > 3 else 0)
    Path(a[2]).write_bytes(datos)
    print(f"✔ {a[2]}: {len(datos)} bytes")
