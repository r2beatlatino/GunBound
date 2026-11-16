# -*- coding: utf-8 -*-
"""probar_rangos — el rango sale del GP (el cliente no tiene tabla: lo decide el server), la bandera es el país y
el GP/oro van en el 0x1012. Los esperados salen de rangos.TABLA_GP, no escritos a mano."""
import struct

from arnes import Banco, ServerDePrueba
from robot import Robot, canjear
from servidor import rangos

b = Banco("probar_rangos")


class J:                                    # un jugador de mentira para lo que no necesita base
    def __init__(self, gp=0, pais=0, es_gm=False, rango_fijo=None):
        self.gp, self.pais, self.es_gm, self.rango_fijo = gp, pais, es_gm, rango_fijo


# ── la tabla ───────────────────────────────────────────────────────────────────────────────────────────────
b.igual(rangos.rango_por_gp(0), rangos.POLLITO, "con 0 GP se empieza de pollito")
anterior = None
for minimo, r in rangos.TABLA_GP:
    b.ver(rangos.rango_por_gp(minimo) == r, f"{minimo} GP da {rangos.NOMBRES[r]}")
    if anterior is not None:
        b.ver(rangos.rango_por_gp(minimo - 1) == anterior, f"control: {minimo - 1} GP todavía es {rangos.NOMBRES[anterior]}")
    anterior = r
b.ver(all(a[0] < c[0] and a[1] > c[1] for a, c in zip(rangos.TABLA_GP, rangos.TABLA_GP[1:])),
      "la tabla sube de GP y baja de número (19 pollito … -4 dragón plateado)")
b.igual(rangos.siguiente(0), (rangos.TABLA_GP[1][1], rangos.TABLA_GP[1][0]), "al pollito le falta el 1.er corte")
b.igual(rangos.siguiente(rangos.TABLA_GP[-1][0]), None, "el último no tiene siguiente")

# ── los 8 bytes ────────────────────────────────────────────────────────────────────────────────────────────
b.igual(struct.unpack("<4h", rangos.insignias(J(gp=0, pais=9))), (19, 19, 19, 9), "pollito de Argentina")
b.igual(struct.unpack("<4h", rangos.insignias(J(gp=10 ** 6))), (-4, -4, -4, 0), "dragón plateado (negativo) y «?»")
b.igual(struct.unpack("<4h", rangos.insignias(J(gp=10 ** 6, es_gm=True))), (20, 20, 20, 0), "el GM es 20 aunque tenga GP")
b.igual(struct.unpack("<4h", rangos.insignias(J(gp=0, rango_fijo=26))), (26, 26, 26, 0), "rango fijo pisa al GP")


# ── con el server: el login y el canal ─────────────────────────────────────────────────────────────────────
def entrar(srv, enenos_id):
    _, d = canjear(srv.url_canje, srv.pase(enenos_id))
    r = Robot(*srv.mundo)
    l = r.login(d["usuario"], d["ticket"])
    r.al_lobby()
    return r, l


def login_rangos(l):
    return struct.unpack("<4h", bytes(l[27:35])), struct.unpack("<I", bytes(l[61:65]))[0], struct.unpack("<I", bytes(l[69:73]))[0]


with ServerDePrueba(oro_inicial=777) as srv:
    gm, _ = entrar(srv, 90000001)
    c, l = entrar(srv, 90000021)
    ins, gp_, oro = login_rangos(l)
    b.igual(ins, (19, 19, 19, 0), "nace pollito y sin país")
    b.igual((gp_, oro), (0, 777), "0x1012: GP en +61 y oro en +69")
    c.cerrar()

    gm.mandar(0x5100, b"\x00/gp GB90000021 2300")
    gm.mandar(0x5100, b"\x00/pais GB90000021 208")
    gm.esperar(0x5101); gm.esperar(0x5101)
    c, l = entrar(srv, 90000021)
    ins, gp_, _ = login_rangos(l)
    b.igual(ins, (rangos.rango_por_gp(2300), rangos.rango_por_gp(2300), rangos.rango_por_gp(2300), 208),
            "/gp 2300 y /pais 208: al volver a entrar sube de rango y tiene bandera")
    b.igual(gp_, 2300, "y «Mi info» muestra el GP")
    gm.todos(0x200E, 0.5)
    c.cerrar()
    gm.mandar(0x5100, b"\x00/gp GB90000021 +5000")
    gm.esperar(0x5101)
    c, l = entrar(srv, 90000021)
    ins, gp_, _ = login_rangos(l)
    b.igual((ins[2], gp_), (rangos.rango_por_gp(7300), 7300), "/gp +5000 suma y el rango sigue subiendo")
    llega = gm.esperar(0x200E)
    b.ver(llega is not None and struct.unpack("<4h", bytes(llega[22:30])) == ins,
          "el canal ve al que llega con las mismas insignias (ficha de 30: lugar, nick, género, avatar, 8)")
    c.mandar(0x5100, b"\x00/gp GB90000021 999999")
    b.ver(b"No conozco" in (c.esperar(0x5101) or b""), "control: /gp no es para un jugador común")
    _, lg = entrar(srv, 90000001)
    b.igual(login_rangos(lg)[0][:3], (20, 20, 20), "el GM entra con rango 20")
b.fin()
