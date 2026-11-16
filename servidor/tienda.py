# -*- coding: utf-8 -*-
"""tienda — el inventario de avatares, la compra, ponerse la ropa y los saldos.

Medido en el Legacy:
  · 0x6000 → 0x6001 SIN cifrar: rtc 0 · cantidad (WORD) · por pieza 14 bytes: serie (4) · pieza (4) · puesta (1) · 5 ceros
    (⚠ cifrado, el Legacy lee la cantidad del texto cifrado y se cae en el bucle de lectura)
  · 0x6020 compra (en el Legacy es COMPRA, no venta): 16 bytes cifrados: [control 4][pieza 4][moneda 1][plazo 1]…
    moneda 0 = oro, 1 = cash · plazo 7 = para siempre (el único que se vende)
    → 0x6021 rtc = estado (0 bien, 0x6003 no alcanza, 1 error) · 01 00 + serie (4) + pieza (4) + 5 ceros
  · 0x600E ponerse/sacarse: cantidad (WORD) + por pieza serie (4) + puesta (1) → 0x600F rtc 0
    (sin esa confirmación el cliente reenvía el pedido y no deja salir de la tienda)
  · 0x6004 vacío = «¿tengo regalos?»: sin regalos NO se contesta (un 0x6005 lo toma como regalo nuevo)
  · 0x6008 → 0x6009 rtc 0 + 00 00 (cierra el cartel de regalo)
  · 0x1090 [00] → 0x1091: 00 00 · móvil 1 · móvil 2 · 6 ceros (sin esto el Legacy no pasa al lobby)
  · 0x6100 → 0x6101 cash · 0x6104 → 0x6105 oro
"""
from . import canal, cifrado
from .entrada import avisar_cash
from .paquete import u16, u32
from .registro import log

PARA_SIEMPRE = 7
ORO, CASH = 0, 1
NO_ALCANZA = 0x6003


def _registros(mundo, s):
    j = s.jugador
    puestas = set()
    salida = []
    for serie, pieza in mundo.base.inventario(j.enenos_id):
        casilla = pieza[2] | (pieza[3] << 8)
        puesta = casilla < 4 and casilla not in puestas and pieza[:2] == j.avatar[casilla * 2:casilla * 2 + 2]
        if puesta:
            puestas.add(casilla)
        salida.append(u32(serie) + pieza + bytes((1 if puesta else 0,)) + bytes(5))
    return salida


def inventario(mundo, s, cuerpo):
    regs = _registros(mundo, s)
    s.enviar(0x6001, u16(len(regs)) + b"".join(regs), rtc=0)
    avisar_cash(s)


def ajustes_mundo(mundo, s, cuerpo):
    if bytes(cuerpo) == b"\x00":
        s.enviar(0x1091, b"\x00\x00" + bytes((s.movil1 & 0xFF, s.movil2 & 0xFF)) + bytes(6))


def cash(mundo, s, cuerpo):
    s.enviar(0x6101, u32(_fresco(mundo, s).cash), rtc=0)


def oro(mundo, s, cuerpo):
    s.enviar(0x6105, u32(_fresco(mundo, s).oro), rtc=0)


def _fresco(mundo, s):
    s.jugador = mundo.base.jugador(s.enenos_id)
    return s.jugador


def regalos(mundo, s, cuerpo):
    if len(cuerpo) == 0:
        # «¿hay regalos?» → no hay: silencio. Es lo ÚLTIMO que pide el lobby al armarse: recién ahí se le
        # presentan los que ya estaban en el canal (antes, el lobby limpia su lista y los pierde)
        if s.sala is None and not s.presentado:
            s.presentado = True
            canal.presentar(mundo, s)
        return
    log("TIENDA", f"{s.nick}: 0x6004 con datos (sin atender) {bytes(cuerpo[:32]).hex()}")


def cerrar_regalo(mundo, s, cuerpo):
    s.enviar(0x6009, b"\x00\x00", rtc=0)


def comprar(mundo, s, cuerpo):
    if len(cuerpo) != 16:
        s.enviar(0x6021, b"", rtc=1)
        return
    plano = cifrado.descifrar_crudo(cuerpo, s.clave)
    if plano[:4] != ((cifrado.CONTROL_BASE + 0x6020) & 0xFFFFFFFF).to_bytes(4, "little"):
        s.enviar(0x6021, b"", rtc=1)
        return
    pieza, moneda, plazo = bytes(plano[4:8]), plano[8], plano[9]
    precios = mundo.precios.get(pieza.hex())
    if plazo != PARA_SIEMPRE or moneda not in (ORO, CASH) or not precios or not precios[moneda]:
        log("TIENDA", f"{s.nick}: compra no disponible {pieza.hex()} moneda {moneda} plazo {plazo}")
        s.enviar(0x6021, b"", rtc=1)
        s.enviar(0x5101, b"Esa pieza no se vende con esa moneda o ese plazo (solo para siempre).")
        return
    precio = precios[moneda]
    serie = mundo.base.comprar(s.enenos_id, pieza, "cash" if moneda == CASH else "oro", precio)
    if serie is None:
        s.enviar(0x6021, b"", rtc=NO_ALCANZA)
        return
    _fresco(mundo, s)
    log("TIENDA", f"{s.nick} compra {pieza.hex()} por {precio} {'cash' if moneda == CASH else 'oro'} (serie {serie})")
    s.enviar(0x6021, b"\x01\x00" + u32(serie) + pieza + bytes(5), rtc=0)


def ponerse(mundo, s, cuerpo):
    j = _fresco(mundo, s)
    n = cuerpo[0] | (cuerpo[1] << 8) if len(cuerpo) >= 2 else 0
    if n > 8 or len(cuerpo) != 2 + n * 5:
        s.enviar(0x600F, b"", rtc=1)
        return
    mias = dict(mundo.base.inventario(j.enenos_id))
    cambios = []
    for i in range(2, len(cuerpo), 5):
        serie = int.from_bytes(cuerpo[i:i + 4], "little")
        puesta = cuerpo[i + 4]
        pieza = mias.get(serie)
        if pieza is None or puesta not in (0, 1):
            s.enviar(0x600F, b"", rtc=1)
            return
        casilla = pieza[2] | (pieza[3] << 8)
        if casilla >= 4:
            s.enviar(0x600F, b"", rtc=1)
            return
        cambios.append((puesta, casilla, pieza[:2]))
    avatar = bytearray(j.avatar)
    # un reemplazo trae «sacar» y «poner» para la misma casilla: primero se saca, después se pone
    for puesta, casilla, codigo in sorted(cambios, key=lambda c: c[0]):
        k = casilla * 2
        if puesta:
            avatar[k:k + 2] = codigo
        elif avatar[k:k + 2] == codigo:
            avatar[k:k + 2] = bytes((0, codigo[1] & 0x80)) if casilla < 3 else bytes(2)
    if bytes(avatar) != j.avatar:
        mundo.base.poner_avatar(j.enenos_id, bytes(avatar))
        _fresco(mundo, s)
        log("TIENDA", f"{s.nick} se viste {bytes(avatar).hex()}")
    s.enviar(0x600F, b"", rtc=0)


ATIENDE = {0x1090: ajustes_mundo, 0x6000: inventario, 0x6004: regalos, 0x6008: cerrar_regalo,
           0x600E: ponerse, 0x6020: comprar, 0x6100: cash, 0x6104: oro}
