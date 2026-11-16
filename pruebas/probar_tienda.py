# -*- coding: utf-8 -*-
"""probar_tienda — comprar, ponerse la ropa, el inventario, y que todo quede guardado al reiniciar el server."""
import json
import shutil

from arnes import Banco, ServerDePrueba
from robot import Robot, canjear
from servidor import cifrado
from servidor.ajustes import DIR_DATOS_JUEGO

b = Banco("probar_tienda")
PRECIOS = json.loads((DIR_DATOS_JUEGO / "precios_avatar.json").read_text("utf-8"))["prices"]
# una pieza de cuerpo (casilla 0). Benja (16-nov): TODO se compra con oro; el cash es un placeholder.
PIEZA = next(bytes.fromhex(k) for k, v in PRECIOS.items() if v[0] and k.endswith("0000"))
ORO_PIEZA, CASH_PIEZA = PRECIOS[PIEZA.hex()]
assert all(c == 0 for _, c in PRECIOS.values()), "la tabla del server tiene que ser SÓLO ORO"


def entrar(srv, eid):
    _, d = canjear(srv.url_canje, srv.pase(eid))
    r = Robot(*srv.mundo)
    r.login(d["usuario"], d["ticket"])
    r.esperar(0x1032)
    return r


def compra(r, pieza, moneda, plazo=7):
    """Lo que manda el Legacy: 16 bytes cifrados crudos = [control 4][pieza 4][moneda][plazo] + relleno."""
    plano = ((cifrado.CONTROL_BASE + 0x6020) & 0xFFFFFFFF).to_bytes(4, "little") + pieza + bytes((moneda, plazo)) + bytes(6)
    r.mandar(0x6020, cifrado.cifrar_crudo(plano, r.clave))
    return r.esperar(0x6021)


def inventario(r):
    r.mandar(0x6000)
    c = r.esperar(0x6001)
    n = c[2] | c[3] << 8
    return [(int.from_bytes(c[4 + i * 14:8 + i * 14], "little"), bytes(c[8 + i * 14:12 + i * 14]), c[12 + i * 14])
            for i in range(n)]


srv = ServerDePrueba(oro_inicial=ORO_PIEZA + 10, cash_inicial=10 ** 9)
with srv:
    r = entrar(srv, 90000010)
    b.igual(inventario(r), [], "inventario vacío al nacer")
    resp = compra(r, PIEZA, 1)
    b.igual(bytes(resp[0:2]), b"\x01\x00", "control: con cash (aunque sobre) no se vende: sólo oro")
    resp = compra(r, PIEZA, 0, plazo=1)
    b.igual(bytes(resp[0:2]), b"\x01\x00", "control: un plazo que no es «para siempre» → error")
    b.igual(inventario(r), [], "control: las compras rechazadas no agregan nada")
    resp = compra(r, PIEZA, 0)
    b.igual(bytes(resp[0:4]), b"\x00\x00\x01\x00", "compra por oro → estado 0 y una pieza")
    serie = int.from_bytes(resp[4:8], "little")
    b.igual(bytes(resp[8:12]), PIEZA, "la respuesta trae la pieza")
    r.mandar(0x6104)
    b.igual(int.from_bytes(r.esperar(0x6105)[2:6], "little"), 10, "el oro se descontó")
    inv = inventario(r)
    b.igual([(s_, p_, puesta) for s_, p_, puesta in inv], [(serie, PIEZA, 0)], "la pieza está, sin poner")
    # control: un 0x6020 con el control cambiado (otro comando) se rechaza
    plano = ((cifrado.CONTROL_BASE + 0x6021) & 0xFFFFFFFF).to_bytes(4, "little") + PIEZA + bytes((0, 7)) + bytes(6)
    r.mandar(0x6020, cifrado.cifrar_crudo(plano, r.clave))
    b.igual(bytes(r.esperar(0x6021)[0:2]), b"\x01\x00", "control: un 0x6020 con otro control → error")

    # ponérsela: 0x600E [cantidad][serie(4) puesta(1)] → 0x600F
    r.mandar(0x600E, b"\x01\x00" + serie.to_bytes(4, "little") + b"\x01")
    b.igual(bytes(r.esperar(0x600F)[0:2]), b"\0\0", "ponerse → 0x600F bien (sin esto no deja salir de la tienda)")
    b.igual(inventario(r)[0][2], 1, "ahora figura puesta")
    r.mandar(0x600E, b"\x01\x00" + (serie + 999).to_bytes(4, "little") + b"\x01")
    b.igual(bytes(r.esperar(0x600F)[0:2]), b"\x01\x00", "control: ponerse algo que no es suyo → error")
    # «¿hay regalos?» (0x6004 vacío) no se contesta: un 0x6005 lo tomaría como regalo nuevo
    r.mandar(0x6004)
    b.ver(r.esperar(0x6005, 0.4) is None, "sin regalos no hay 0x6005")
    r.cerrar()
    estado_dir = srv.dir

# el mismo estado con OTRO server (= reinicio): lo comprado y lo puesto sigue
srv2 = ServerDePrueba(dir_estado=estado_dir)
with srv2:
    r = entrar(srv2, 90000010)
    inv = inventario(r)
    b.igual([(p_, puesta) for _, p_, puesta in inv], [(PIEZA, 1)], "después del reinicio: la pieza sigue, puesta")
    j = srv2.en_el_lazo(lambda: srv2.srv.base.jugador(90000010))
    b.igual(j.avatar[0:2], PIEZA[0:2], "el avatar guardado la lleva puesta")
    r.mandar(0x5100, b"\x00/genero f")
    r.esperar(0x5101)
    j = srv2.en_el_lazo(lambda: srv2.srv.base.jugador(90000010))
    b.igual((j.genero, j.avatar), (1, bytes(8)), "/genero f: mujer y sin nada puesto")
    r.mandar(0x5100, b"\x00/nombre Pepe_01")
    r.esperar(0x5101)
    b.igual(srv2.en_el_lazo(lambda: srv2.srv.base.jugador(90000010)).nick, "Pepe_01", "/nombre cambia el nick")
    r2 = entrar(srv2, 90000011)
    r2.mandar(0x5100, b"\x00/nombre pepe_01")
    b.ver(b"ya lo tiene" in (r2.esperar(0x5101) or b""), "control: un nick repetido (sin mirar mayúsculas) no se puede")
    r2.mandar(0x5100, b"\x00/dar Pepe_01 100")
    b.ver(b"No conozco" in (r2.esperar(0x5101) or b""), "control: /dar no es para un jugador común")
    r.cerrar()
    r2.cerrar()
shutil.rmtree(estado_dir, ignore_errors=True)
b.fin()
