# -*- coding: utf-8 -*-
"""parchar_cliente — arma el cliente de Eñeños a partir del GunBound Legacy original, SIN tocar el original.

    python herramientas/parchar_cliente.py                     (C:\\GunBound-Legacy → D:\\Gunbound\\Cliente-Enenos)
    python herramientas/parchar_cliente.py ORIGEN DESTINO
    python herramientas/parchar_cliente.py --comprobar DESTINO (dice qué parches tiene un exe)

Los parches de GunBound.exe (todos medidos; ver documentacion/CLIENTE.md):

  1. SIN DualSoft.dll — la «protección» de Legacy: autenticación propia contra SU server (15.204.128.129), HWID,
     mascotas y bonos de GM. Se borra su descriptor de la tabla de imports (20 bytes en 0x4FE0C8). Sin ella el
     cliente arranca y habla el protocolo de siempre.
  2. El REGISTRO de HKLM a HKCU — las 5 aperturas de la clave (`push 80000002` → `push 80000001`): así no hace
     falta ser administrador y cada usuario de Windows tiene lo suyo.
  3. La CLAVE del registro `Software\\softnyx\\Legacy` → `Software\\softnyx\\Enenos` (mismo largo): el cliente
     de Eñeños no pisa ni lee la configuración del Legacy instalado.
  4. VARIAS INSTANCIAS — en 0x40C3EC el cliente pregunta «¿ya hay uno abierto?» (GetLastError == 183) y se cierra
     en silencio. Se anula ese salto (6 NOP). Hace falta para probar con varios jugadores en una PC.
  6. El P2P pasa al TÚNEL a los 2 s (no a los 20). En el bucle de compañeros de sala (0x44D89D, clase CCommP2P):
     si hace 20000 ms que no llega nada de uno (0x44D8FD `add eax, 4E20`), llama a 0x44D5E0, que prende «este va
     por túnel» (bit en +0xE5C, no se apaga) y le reenvía por el túnel lo pendiente. NO corta a nadie (medido).
     Benja (16-nov): «UDP P2P, pero sólo 2000 ms de espera para pasar al túnel». 0x4E20 → 0x7D0.
  7. El PING al compañero cada 1 s (no cada 5): 0x44D8CF `add edx, 1388` → 0x3E8. Con un plazo de 2 s y pings
     cada 5, una conexión directa que anda pero está callada pasaría al túnel; con pings cada 1 s sólo pasa si
     de verdad se pierden.
  8. UNA SOLA PANTALLA de arranque (Benja: «hace 3 o 4 transiciones antes del selector; lo ideal, una sola con
     arte original»). El juego encadena logo (estado 5) → logo 2 (6) → título (1) → selector (2): en 0x4AB5EE
     el `push 6` pasa a `push 2` (del logo directo al selector, conservando la salida del estado 5) y en 0x4CF59E
     la rama que entra por el 6 (`push 1`) también va al 2. Lo encontró Codex (investigacion/ARTE_Y_ARRANQUE.md).

Y uno de dxwnd.dll (el DxWnd que trae Legacy para jugar en VENTANA: sin él el juego no arranca):

  5. DxWnd deja enganchado UN juego a la vez: espera su mutex compartido y, si otro lo tiene, llama a exit(0)
     (medido con Frida: el ExitProcess de la 2.ª instancia sale de dxwnd.dll+0x4203F). En +0x4202A el
     `jne` (75 20) pasa a `jmp` (EB 20): el segundo sigue de largo.

Y los DATOS: `graphics.xfs` con el ARTE ORIGINAL (`herramientas/arte_original/`, del instalador GunBound WC GIS
557): la única pantalla de arranque es el título de GunBound World Champion (en `logomode.img` y `logo.img`), y
vuelven el `title.img`, el fondo de carga `load_back.img` y el del selector `serverlist_back.img` sin la marca
Legacy. Del lobby (`gamelist_back.img`, el logo «GunBound LEGACY» en el chat) y de la sala (`ready_back.img`,
«OPCIONES DE SALA») se cambia SÓLO el fondo 800×600 por el del 557; los botones y marcos siguen siendo los del
Legacy (`mezclar_img.py`; Benja, 16-nov).
  ★ MAPAS: EL ARTE VUELVE AL ORIGINAL, LA JUGABILIDAD DE LEGACY SE QUEDA (Benja, 16-nov: «remover el arte, volver
  al original — fondos; los cambios de gameplay o terreno, los conservamos»). La LISTA de mapas (`stage.dat`) es la
  original: Legacy no agregó mapas. Un terreno `X.img` es [cuadro 0 = el TERRENO, atado a su `X.lnd` = la tierra
  donde pegan los tiros][cuadro 1 = el FONDO, sólo en el lado A; el B usa el del A]. Entonces (`archivos_de_mapa`):
    - `.lnd`: SIEMPRE los de Legacy (7 distintos: metro, babob, brickb, fackyb, hokb, lastb, mosb).
    - terreno con la tierra cambiada: cuadro 0 de Legacy (el dibujo tiene que coincidir con la tierra) + el fondo
      del original (si el original no tiene fondo propio, como babob/mosb, se le saca el que agregó Legacy).
    - terreno con la tierra igual (brick, facky, last, mos: Legacy sólo cambió el fondo): entero del original.
    - los adornos animados (brick1…, metro1…, mos1…, facky1…, que Legacy dejó transparentes): del original.
    - miniaturas de la sala / del lobby y cargas `load_stage`: de Legacy sólo las etapas de terreno cambiado
      (`ETAPAS_DE_LEGACY`, que muestran ESE terreno); las demás, del original.
`avatar.xfs` (la ropa) sale SÓLO ORO (`avatar_xfs.solo_oro`): en las 861 piezas que se venden, cash en 0 y el permiso de cash apagado; las 3 que eran sólo cash, a 180 000 de oro. El server cobra con la misma tabla
(`--precios` la escribe en servidor/datos/precios_avatar.json).

Lo que NO se copia: DualSoft.dll, el NyxLauncher y el Updater de Legacy (hablan con SUS servers), y los logs.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import avatar_xfs  # noqa: E402
import rearmar_xfs  # noqa: E402
import re  # noqa: E402
import tempfile  # noqa: E402
from xfs import XFS  # noqa: E402

ARTE = Path(__file__).resolve().parent / "arte_original"
# el graphics.xfs del instalador GunBound GIS WC 557 (lo sacó Codex de D:\Gunbound\GB; fuera del repo: es de Softnyx)
STOCK = Path(r"D:\Gunbound\GB-originales\GIS557_graphics.xfs")
SHA_STOCK = "5bb5e3075d7c33421dbed8376997637c8ee8008c53dbc9b752fe21c1c41554bb"
# los 12 terrenos (los mismos nombres que sus .lnd), sus adornos (brick1…, metro1…) y lo que los muestra
MAPAS = re.compile(r"^((babo|brick|candy|cave|dragon|facky|hok|kettle|last|metro|mos|star)b?\d*\.(img|lnd)"
                   r"|load_stage\d+\.img|ready_stagemap\.img|gamelist_stagemap\.img)$")


# Las etapas (0-10 lado A, 11-21 lado B: el índice de `ready_stagemap` y de `load_stageNN`) cuyo TERRENO cambió
# Legacy. MEDIDO 16-nov: son exactamente las 7 `load_stage` que difieren y sus miniaturas muestran el terreno de
# Legacy (3 = Metropolis A con la roca oscura, 21 = los alienígenas de fackyb, 17 = el dragón celeste de lastb…).
# `archivos_de_mapa` comprueba que sean tantas como .lnd cambiados.
ETAPAS_DE_LEGACY = {3, 12, 13, 16, 17, 18, 21}


def _armar_img(cab, cuadros):
    return cab[:4] + len(cuadros).to_bytes(4, "little") + b"".join(cuadros)


def archivos_de_mapa(legacy_xfs, stock_xfs):
    """{nombre: bytes} de los archivos de mapa a poner en el cliente (ver el docstring del módulo: arte original,
    jugabilidad de Legacy). Sólo devuelve lo que cambia respecto del Legacy."""
    from mezclar_img import partir
    L, S = XFS(legacy_xfs), XFS(stock_xfs)
    nombres = [n for n in L.entries if MAPAS.match(n) and n in S.entries]
    lnd_cambiadas = {n[:-4] for n in nombres if n.endswith(".lnd") and L.read(n) != S.read(n)}
    if len(lnd_cambiadas) != len(ETAPAS_DE_LEGACY):
        raise SystemExit(f"⛔ {len(lnd_cambiadas)} tierras cambiadas ({sorted(lnd_cambiadas)}) y "
                         f"{len(ETAPAS_DE_LEGACY)} etapas de Legacy: ¿es otro graphics.xfs?")
    salida = {}
    for n in nombres:
        leg, orig = L.read(n), S.read(n)
        if leg == orig or n.endswith(".lnd"):
            continue                                            # igual, o la tierra: queda la de Legacy
        base = n[:-4]
        if base in lnd_cambiadas:                               # terreno de Legacy + fondo original
            cab, cl = partir(leg)
            _, co = partir(orig)
            nuevo = _armar_img(cab, [cl[0]] + co[1:])
        elif n == "ready_stagemap.img" or n == "gamelist_stagemap.img":
            cab, cl = partir(leg)
            _, co = partir(orig)
            por_etapa = len(cl) // 22                           # la sala: 22 cuadros; el lobby: 44 (2 tandas de 22)
            nuevo = _armar_img(cab, [cl[i] if i % 22 in ETAPAS_DE_LEGACY else co[i] for i in range(22 * por_etapa)])
        elif re.fullmatch(r"load_stage\d+", base):
            if int(base[10:]) in ETAPAS_DE_LEGACY:
                continue
            nuevo = orig
        else:                                                   # fondo cambiado con la tierra igual, y los adornos
            nuevo = orig
        if nuevo != leg:
            salida[n] = nuevo
    return salida

ORIGEN = Path(r"C:\GunBound-Legacy")
DESTINO = Path(r"D:\Gunbound\Cliente-Enenos")
SHA_ORIGINAL = "d03e0afed3890595c1ae16a5c64b2481f01ab9caef79c7d37faccbf5cd62b8ca"
NO_COPIAR = {"DualSoft.dll", "NyxLauncher.exe", "NyxLauncher.ini", "Updater.exe", "Uninstall.exe", "log", "apply",
             "fetch"}

# (nombre, desplazamiento en el ARCHIVO, bytes originales, bytes nuevos)
PARCHES = [
    ("sin DualSoft (import)", 0x4FE0C8, bytes.fromhex("19e14f000000000000000000f0e04f0011e14f00"), bytes(20)),
    *[(f"registro HKCU #{i + 1}", o, bytes.fromhex("02000080"), bytes.fromhex("01000080"))
      for i, o in enumerate((0xB55A, 0xBE67, 0xC667, 0xC861, 0xC947))],
    ("clave del registro", 0x1CE081, b"Legacy", b"Enenos"),
    ("varias instancias", 0xC3EC, bytes.fromhex("0f85ef0a0000"), bytes.fromhex("909090909090")),
    ("P2P: al túnel a los 2 s", 0x4D8FD, bytes.fromhex("05204e0000"), bytes.fromhex("05d0070000")),
    ("P2P: ping cada 1 s", 0x4D8CF, bytes.fromhex("81c288130000"), bytes.fromhex("81c2e8030000")),
    ("arranque: del logo al selector", 0xAB5EE, bytes.fromhex("6a06"), bytes.fromhex("6a02")),
    ("arranque: rama alternativa al selector", 0xCF59E, bytes.fromhex("6a01"), bytes.fromhex("6a02")),
]
CLAVE_REGISTRO = r"Software\softnyx\Enenos"
SHA_DXWND = "909349ff70190fe962bdc55748c740b9e4137126b2ac4a4cebb7e63c3df55898"
PARCHES_DXWND = [("DxWnd: varias instancias", 0x4142A, bytes.fromhex("7520"), bytes.fromhex("eb20"))]


def sha256(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def parchar(datos, parches=None):
    datos = bytearray(datos)
    for nombre, off, viejo, nuevo in (PARCHES if parches is None else parches):
        actual = bytes(datos[off:off + len(viejo)])
        if actual == nuevo:
            continue
        if actual != viejo:
            raise SystemExit(f"⛔ {nombre}: en 0x{off:X} esperaba {viejo.hex()} y hay {actual.hex()} (¿otro exe?)")
        datos[off:off + len(viejo)] = nuevo
    return bytes(datos)


def comprobar(exe, parches=None):
    datos = Path(exe).read_bytes()
    salida = {}
    for nombre, off, viejo, nuevo in (PARCHES if parches is None else parches):
        actual = datos[off:off + len(viejo)]
        salida[nombre] = "parchado" if actual == nuevo else ("original" if actual == viejo else "DISTINTO")
    return salida


def armar(origen=ORIGEN, destino=DESTINO):
    origen, destino = Path(origen), Path(destino)
    exe = origen / "GunBound.exe"
    if sha256(exe) != SHA_ORIGINAL:
        raise SystemExit(f"⛔ {exe} no es el GunBound.exe de Legacy que se midió (sha256 distinto)")
    destino.mkdir(parents=True, exist_ok=True)
    for p in origen.iterdir():
        if p.name in NO_COPIAR or p.name in ("GunBound.exe", "dxwnd.dll", "graphics.xfs"):
            continue
        if p.is_dir():
            shutil.copytree(p, destino / p.name, dirs_exist_ok=True)
        else:
            shutil.copy2(p, destino / p.name)
    (destino / "GunBound.exe").write_bytes(parchar(exe.read_bytes()))
    dx = origen / "dxwnd.dll"
    if sha256(dx) != SHA_DXWND:
        raise SystemExit(f"⛔ {dx} no es el DxWnd que se midió")
    (destino / "dxwnd.dll").write_bytes(parchar(dx.read_bytes(), PARCHES_DXWND))
    if sha256(STOCK) != SHA_STOCK:
        raise SystemExit(f"⛔ {STOCK} no es el graphics.xfs del GIS 557 que se midió")
    mapas = archivos_de_mapa(origen / "graphics.xfs", STOCK)
    with tempfile.TemporaryDirectory() as tmp:
        for p in ARTE.iterdir():
            shutil.copy2(p, Path(tmp) / p.name)
        for n, datos in mapas.items():
            (Path(tmp) / n).write_bytes(datos)
        r = rearmar_xfs.rebuild(origen / "graphics.xfs", tmp, destino / "graphics.xfs")
    print(f"✔ graphics.xfs: arte original ({', '.join(p.name for p in ARTE.iterdir())}) y "
          f"{len(mapas)} archivos de mapa con el arte original y la jugabilidad de Legacy ({', '.join(sorted(mapas))})")
    assert len(r["replacements"]) == len(list(ARTE.iterdir())) + len(mapas)
    oro, _ = avatar_xfs.solo_oro((origen / "avatar.xfs").read_bytes())
    (destino / "avatar.xfs").write_bytes(oro)
    print(f"✔ avatar.xfs sólo oro (sha256 {hashlib.sha256(oro).hexdigest()[:16]}…)")
    print(f"✔ cliente armado en {destino}  ·  GunBound.exe sha256 {sha256(destino / 'GunBound.exe')}")
    print(f"  el original sigue igual: {sha256(exe) == SHA_ORIGINAL}")
    return destino


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--precios"]:
        _, precios = avatar_xfs.solo_oro((ORIGEN / "avatar.xfs").read_bytes())
        salida = Path(__file__).resolve().parent.parent / "servidor" / "datos" / "precios_avatar.json"
        salida.write_text(json.dumps({"source": "GunBound Legacy v179 avatar.xfs, piezas permanentes, SÓLO ORO "
                                      "(herramientas/avatar_xfs.py)", "prices": precios},
                                     ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
        print(f"✔ {salida}: {len(precios)} piezas, todas en oro")
    elif args[:1] == ["--comprobar"]:
        ruta = Path(args[1] if len(args) > 1 else DESTINO)
        exe = ruta / "GunBound.exe" if ruta.is_dir() else ruta
        for k, v in list(comprobar(exe).items()) + list(comprobar(exe.parent / "dxwnd.dll", PARCHES_DXWND).items()):
            print(f"  {v:9}  {k}")
    else:
        armar(*(args[:2]))
