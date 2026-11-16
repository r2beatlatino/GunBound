# -*- coding: utf-8 -*-
"""cifrado — el AES de GunBound.

Hay DOS cifrados, los dos AES-128 en modo ECB:

1. ESTÁTICO: una clave fija en el cliente. Sólo cifra el nombre de usuario del login (el primer bloque).
2. DINÁMICO: la clave sale de usuario + contraseña + la ficha de 4 bytes que el server da al conectar (0x1001):
   un SHA-0 (no SHA-1: sin la rotación) truncado a 16 bytes, con cada DWORD dado vuelta.
   Cada 12 bytes de datos llevan adelante 4 bytes de control = 0x8631607E + comando: así el que descifra sabe
   que usó la clave buena Y que el mensaje es del comando que dice ser.

⇒ El server necesita la contraseña EN CLARO para hablar con el cliente. Con la entrada por pase la «contraseña» es el
   BOLETO que da el canje (`boletos.py`): el server lo conoce porque lo inventó él.

Fuente: el emulador de jglim (MIT, ver documentacion/CREDITOS.md) y el desensamblado del cliente Legacy.
"""
from Crypto.Cipher import AES

CLAVE_ESTATICA = bytes.fromhex("FFB3B3BEAE97AD83B9610E23A43C2EB0")
# la del ARGUMENTO de GunBound.exe (usuario 16 + contraseña 16 + 16 ceros): la usa el launcher, no el server
CLAVE_ARGUMENTO = bytes.fromhex("FAEE85F24073D9161390197F6E562A67")
CONTROL_BASE = 0x8631607E


def _rotar(n, b):
    return ((n << b) | (n >> (32 - b))) & 0xFFFFFFFF


def _sha0_un_bloque(bloque):
    w = [int.from_bytes(bloque[i * 4:i * 4 + 4], "big") for i in range(16)] + [0] * 64
    for i in range(16, 80):
        w[i] = w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16]          # SHA-0: sin rotar (SHA-1 rota 1)
    h = [0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0]
    a, b, c, d, e = h
    for i in range(80):
        if i < 20:
            f, k = d ^ (b & (c ^ d)), 0x5A827999
        elif i < 40:
            f, k = b ^ c ^ d, 0x6ED9EBA1
        elif i < 60:
            f, k = (b & c) | (b & d) | (c & d), 0x8F1BBCDC
        else:
            f, k = b ^ c ^ d, 0xCA62C1D6
        a, b, c, d, e = (_rotar(a, 5) + f + e + k + w[i]) & 0xFFFFFFFF, a, _rotar(b, 30), c, d
    h = [(x + y) & 0xFFFFFFFF for x, y in zip(h, (a, b, c, d, e))]
    return b"".join(x.to_bytes(4, "little") for x in h[:4])           # 16 bytes, cada DWORD dado vuelta


def clave_dinamica(usuario, contrasena, ficha):
    """usuario y contraseña ≤ 12 letras cada uno: entran en un solo bloque de 64 bytes."""
    m = bytearray(usuario.encode("latin-1") + contrasena.encode("latin-1") + bytes(ficha))
    bits = len(m) * 8
    m.append(0x80)
    m.extend(bytes(62 - len(m)))
    m.extend(bits.to_bytes(2, "big"))
    return _sha0_un_bloque(bytes(m))


def descifrar_estatico(bloque16):
    return AES.new(CLAVE_ESTATICA, AES.MODE_ECB).decrypt(bytes(bloque16))


def cifrar_estatico(bloque16):
    return AES.new(CLAVE_ESTATICA, AES.MODE_ECB).encrypt(bytes(bloque16))


def cifrar_crudo(datos, clave):
    return AES.new(clave, AES.MODE_ECB).encrypt(bytes(datos))


def descifrar_crudo(datos, clave):
    return AES.new(clave, AES.MODE_ECB).decrypt(bytes(datos))


def cifrar(datos, clave, comando):
    """Rellena a múltiplo de 12, mete el control cada 12 y cifra. Devuelve un múltiplo de 16."""
    datos = bytes(datos)
    if len(datos) % 12:
        datos += bytes(12 - len(datos) % 12)
    control = ((CONTROL_BASE + comando) & 0xFFFFFFFF).to_bytes(4, "little")
    plano = b"".join(control + datos[i:i + 12] for i in range(0, len(datos), 12))
    return cifrar_crudo(plano, clave)


def descifrar(datos, clave, comando):
    """-> (datos, control_bien). `control_bien` False = clave equivocada o comando cambiado."""
    datos = bytes(datos)
    if not datos or len(datos) % 16:
        return b"", False
    plano = descifrar_crudo(datos, clave)
    control = ((CONTROL_BASE + comando) & 0xFFFFFFFF).to_bytes(4, "little")
    salida, bien = bytearray(), True
    for i in range(0, len(plano), 16):
        if plano[i:i + 4] != control:
            bien = False
        salida.extend(plano[i + 4:i + 16])
    return bytes(salida), bien


def argumento_cliente(usuario, contrasena):
    """La línea de comandos de GunBound.exe: usuario (16) + contraseña (16) + 16 ceros, AES, en HEX MAYÚSCULA."""
    plano = usuario.encode("latin-1")[:16].ljust(16, b"\0") + contrasena.encode("latin-1")[:16].ljust(16, b"\0") + bytes(16)
    return cifrar_crudo(plano, CLAVE_ARGUMENTO).hex().upper()
