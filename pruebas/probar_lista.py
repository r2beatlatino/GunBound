# -*- coding: utf-8 -*-
"""probar_lista — la lista del cliente para el launcher (herramientas/lista_del_cliente.py), sobre todo las PARTES:
los archivos grandes cortados en pedazos para la CDN (Cloudflare no guarda más de 512 MB por archivo)."""
import hashlib
import sys
import tempfile
from pathlib import Path

from arnes import Banco, RAIZ

sys.path.insert(0, str(RAIZ / "herramientas"))
try:
    import lista_del_cliente as lc  # noqa: E402
except ImportError:                                  # en la imagen de Docker no va herramientas/
    print("probar_lista: SALTADA · no está herramientas/lista_del_cliente.py (¿adentro del contenedor?)")
    sys.exit(0)

b = Banco("probar_lista")
with tempfile.TemporaryDirectory() as tmp:
    cli, partes = Path(tmp) / "cliente", Path(tmp) / "partes"
    (cli / "sub").mkdir(parents=True)
    grande = bytes(range(256)) * 41 + b"cola"            # 10 500 bytes: no es múltiplo del pedazo
    (cli / "GunBound.exe").write_bytes(b"MZ" + bytes(100))
    (cli / "sub" / "grafico.xfs").write_bytes(grande)
    (cli / "MuteList.txt").write_text("del jugador")
    args = ("v1", "https://cdn/x/v1/", "h:8372", "https://h/canje")

    sin = lc.armar(cli, *args)
    b.ver(all("partes" not in f for f in sin["files"]), "control: sin --partes no se parte nada")
    b.ver(not partes.exists(), "control: sin --partes no se escribe ningún pedazo")

    con = lc.armar(cli, *args, carpeta_partes=partes, max_sin_partir=5000, pedazo=4096)
    g = next(f for f in con["files"] if f["path"] == "sub/grafico.xfs")
    exe = next(f for f in con["files"] if f["path"] == "GunBound.exe")
    b.ver("partes" not in exe, "control: el archivo chico (bajo el umbral) va entero")
    b.igual([p["path"] for p in g["partes"]], ["sub/grafico.xfs.p1", "sub/grafico.xfs.p2", "sub/grafico.xfs.p3"],
            "el grande va en 3 pedazos, en orden, con la ruta del archivo + .pN")
    b.igual([p["size"] for p in g["partes"]], [4096, 4096, len(grande) - 8192], "tamaños: 2 enteros y la cola")
    junto = b"".join((partes / p["path"]).read_bytes() for p in g["partes"])
    b.igual(junto, grande, "los pedazos, juntos y en orden, son el archivo")
    b.igual(hashlib.md5(junto).hexdigest(), g["md5"], "el md5 de la entrada es el del archivo ENTERO")
    b.ver(all(hashlib.md5((partes / p["path"]).read_bytes()).hexdigest() == p["md5"] for p in g["partes"]),
          "cada pedazo trae su md5")
    b.ver(all(lc.RX_RUTA.match(p["path"]) for p in g["partes"]), "las rutas de los pedazos pasan la regla del launcher")
    b.ver(all(f["path"] != "MuteList.txt" for f in con["files"]), "MuteList.txt (del jugador) no va")
    desordenado = list(reversed(g["partes"]))
    b.ver(hashlib.md5(b"".join((partes / p["path"]).read_bytes() for p in desordenado)).hexdigest() != g["md5"],
          "control: juntados en otro orden, el md5 NO da")
b.fin()
