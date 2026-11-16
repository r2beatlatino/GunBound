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

Y uno de dxwnd.dll (el DxWnd que trae Legacy para jugar en VENTANA: sin él el juego no arranca):

  5. DxWnd deja enganchado UN juego a la vez: espera su mutex compartido y, si otro lo tiene, llama a exit(0)
     (medido con Frida: el ExitProcess de la 2.ª instancia sale de dxwnd.dll+0x4203F). En +0x4202A el
     `jne` (75 20) pasa a `jmp` (EB 20): el segundo sigue de largo.

Lo que NO se copia: DualSoft.dll, el NyxLauncher y el Updater de Legacy (hablan con SUS servers), y los logs.
"""
import hashlib
import shutil
import sys
from pathlib import Path

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
        if p.name in NO_COPIAR or p.name in ("GunBound.exe", "dxwnd.dll"):
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
    print(f"✔ cliente armado en {destino}  ·  GunBound.exe sha256 {sha256(destino / 'GunBound.exe')}")
    print(f"  el original sigue igual: {sha256(exe) == SHA_ORIGINAL}")
    return destino


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--comprobar"]:
        ruta = Path(args[1] if len(args) > 1 else DESTINO)
        exe = ruta / "GunBound.exe" if ruta.is_dir() else ruta
        for k, v in list(comprobar(exe).items()) + list(comprobar(exe.parent / "dxwnd.dll", PARCHES_DXWND).items()):
            print(f"  {v:9}  {k}")
    else:
        armar(*(args[:2]))
