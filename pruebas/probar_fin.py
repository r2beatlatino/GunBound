# -*- coding: utf-8 -*-
"""probar_fin — el fin de la partida lo decide el server (Solo, Score, Tag), como el Serv3:
muertes 0x4100 → 0x4102 a todos · reapariciones 0x4104 → 0x4106 · fin → 0x4410 [ganador].
Y el número de sala: no se reusa enseguida el de una sala cerrada (el cliente lo veda 5 minutos)."""
import struct
import types

from arnes import Banco, ServerDePrueba
from robot import Robot, canjear
from servidor import partida, sala
from servidor.paquete import con_largo

b = Banco("probar_fin")
SOLO = bytes.fromhex("b2620000")
SCORE = bytes.fromhex("b2620400")
SOLO_SIN_EQUIPOS = bytes.fromhex("32620000")      # sin el bit 0x80: gana el último vivo (su casilla)


def entrar(srv, eid):
    _, d = canjear(srv.url_canje, srv.pase(eid))
    r = Robot(*srv.mundo)
    r.login(d["usuario"], d["ticket"])
    r.al_lobby()
    r.todos(0x200E, 0.2)
    return r


def armar(srv, ids, ajustes, nombre):
    """Una sala con los jugadores `ids` (casillas 0, 1, 2…; equipos A, B, A, B…) y la partida empezada."""
    rs = [entrar(srv, i) for i in ids]
    llave = rs[0]
    llave.mandar(0x2120, con_largo(nombre) + ajustes + bytes(4) + bytes([len(ids)]))
    sid = llave.esperar(0x2121)[3:5]
    for r in rs[1:]:
        r.mandar(0x2110, bytes(sid))
        r.esperar(0x2111)
    llave.mandar(0x3430, b"")
    inicios = [r.esperar(0x3432) for r in rs]
    return rs, inicios, sid[0] | sid[1] << 8


def morir(r, causa=1, quien=1):
    r.mandar(0x4100, struct.pack("<I", causa) + bytes([quien]))


def avisos(r, comando, plazo=0.4):
    salida = []
    for c in r.todos(comando, plazo):
        d, ok = r.descifrar(c, comando)
        salida.append(bytes(d) if ok else None)
    return salida


def cerrar(rs):
    for r in rs:
        r.cerrar()


with ServerDePrueba(p2p="tunel") as srv:
    # ── 1 · Score 1vs1: las vidas van en el 0x3432 y morir el único del equipo cierra la partida ─────────────
    rs, ini, _ = armar(srv, [90000101, 90000102], SCORE, "Score1")
    a, c = rs
    d, ok = a.descifrar(ini[0], 0x3432)
    b.igual(d[2], 0x24, "Score 1vs1: el 0x3432 lleva las vidas (2) en el nibble alto del byte [2] (Serv3 0x415F6C)")
    b.ver(c.esperar(0x4410, 0.3) is None, "control: sin muertes no hay fin")
    morir(a, 1, 1)
    b.ver(a.esperar(0x4101) is not None, "el que murió recibe 0x4101")
    d102 = avisos(c, 0x4102)
    b.igual(d102[:1], [bytes([0, 1, 0, 0, 0, 1]) + bytes(6)], "0x4102 cifrado a todos: [casilla][causa][quién]")
    b.igual(len(avisos(a, 0x4102)), 1, "…también al que murió (como el Serv3)")
    b.igual([x[:1] for x in avisos(a, 0x4410)], [b"\x01"], "Score 1vs1: muere el A → 0x4410 gana el equipo B")
    b.igual([x[:1] for x in avisos(c, 0x4410)], [b"\x01"], "…y le llega también al otro")
    morir(c, 1, 0)
    b.igual(avisos(a, 0x4410, 0.3), [], "control: el 0x4410 va UNA vez (otra muerte después no lo repite)")
    morir(c, 1, 0)
    b.igual(len(avisos(a, 0x4102, 0.3)), 1, "control: la misma casilla muerta dos veces no se avisa dos veces")
    cerrar(rs)

    rs, ini, _ = armar(srv, [90000103, 90000104], SOLO, "Solo1")
    d, ok = rs[0].descifrar(ini[0], 0x3432)
    b.igual(bytes(d[0:4]), SOLO, "control: fuera de Score los ajustes del 0x3432 no se tocan")
    morir(rs[1], 1, 0)
    b.igual([x[:1] for x in avisos(rs[0], 0x4410)], [b"\x00"], "Solo 1vs1: muere el B → gana el equipo A")
    cerrar(rs)

    # ── 2 · Score 2vs2 (vidas 3): equipo entero muerto, reaparecer, y vidas agotadas ───────────────────────
    rs, ini, _ = armar(srv, [90000111, 90000112, 90000113, 90000114], SCORE, "Score2")   # A: 0 y 2 · B: 1 y 3
    a0, b1, a2, b3 = rs
    d, ok = a0.descifrar(ini[0], 0x3432)
    b.igual(d[2] >> 4, 3, "Score 2vs2: 3 vidas")
    morir(a0)
    b.igual(avisos(b1, 0x4410, 0.3), [], "2vs2: muere uno del A y queda su compañero → sigue")
    a0.mandar_cifrado(0x4104, b"\x00")
    b.ver(a0.esperar(0x4105) is not None, "0x4104 (reaparecer) → 0x4105 al que lo pidió")
    b.igual([x[:1] for x in avisos(b3, 0x4106)], [b"\x00"], "…y 0x4106 [casilla] a todos")
    morir(a2)
    b.igual(avisos(b1, 0x4410, 0.3), [], "el que reapareció cuenta como vivo: muere el otro del A y sigue")
    morir(a0)
    b.igual([x[:1] for x in avisos(b1, 0x4410)], [b"\x01"],
            "control al revés: ahora sí están los dos del A muertos → gana B")
    cerrar(rs)

    rs, ini, _ = armar(srv, [90000121, 90000122, 90000123, 90000124], SCORE, "Score3")
    a0, b1, a2, b3 = rs
    for vez in range(2):
        morir(a0)
        a0.mandar_cifrado(0x4104, b"\x00")
        a0.esperar(0x4105)
    b.igual(avisos(b1, 0x4410, 0.3), [], "2 bajas del A con 3 vidas: sigue")
    morir(a0)
    b.igual([x[:1] for x in avisos(b1, 0x4410)], [b"\x01"], "3.ª baja del A (su compañero vivo): se acabaron las vidas → gana B")
    cerrar(rs)

    rs, ini, _ = armar(srv, [90000125, 90000126, 90000127, 90000128], SOLO, "Solo2")
    a0, b1, a2, b3 = rs
    morir(a0)
    a0.mandar_cifrado(0x4104, b"\x00")
    b.igual(avisos(b3, 0x4106, 0.3), [], "control: en Solo no se reaparece (el Serv3 sólo deja en Score y Jewel)")
    morir(a2)
    b.igual([x[:1] for x in avisos(b1, 0x4410)], [b"\x01"], "Solo 2vs2: los dos del A muertos → gana B")
    cerrar(rs)

    # ── 3 · sin equipos (bit 0x80 apagado): gana el último vivo, por casilla ───────────────────────────────
    rs, ini, _ = armar(srv, [90000131, 90000132, 90000133], SOLO_SIN_EQUIPOS, "Libre")
    morir(rs[0])
    b.igual(avisos(rs[1], 0x4410, 0.3), [], "sin equipos: quedan 2 vivos (aunque sean del mismo lado) → sigue")
    morir(rs[1])
    b.igual([x[:1] for x in avisos(rs[2], 0x4410)], [b"\x02"], "sin equipos: gana la casilla del último vivo")
    cerrar(rs)

    # ── 4 · el que se va a mitad de partida cuenta como muerto ────────────────────────────────────────────
    rs, ini, _ = armar(srv, [90000141, 90000142], SOLO, "Abandono")
    a, c = rs
    a.mandar(0x2000, b"\xff\xff")                    # ABANDONAR: el Legacy manda 0x2000 directo (medido 16-nov)
    d102 = avisos(c, 0x4102)
    b.igual([x[:6] for x in d102], [bytes([0]) + struct.pack("<I", 0xF000) + b"\xff"],
            "abandonar: 0x4102 [casilla][F000][FF] a los que quedan (Serv3 0x4145BF)")
    b.igual([x[:1] for x in avisos(c, 0x4410)], [b"\x01"], "…y como no queda nadie del A, gana B")
    b.igual(avisos(a, 0x4102, 0.3), [], "control: al que se va no le llega su propia baja")
    cerrar(rs)

    # ── 5 · el número de sala no se reusa enseguida (el cliente veda 5 min el de la sala abandonada) ────────
    x = entrar(srv, 90000151)
    x.mandar(0x2120, con_largo("Veda") + SOLO + bytes(4) + b"\x02")
    primera = x.esperar(0x2121)[3:5]
    x.mandar(0x2000, b"\xff\xff")
    x.esperar(0x2001)
    x.mandar(0x2120, con_largo("Veda2") + SOLO + bytes(4) + b"\x02")
    segunda = x.esperar(0x2121)[3:5]
    b.ver(segunda != primera, f"la sala nueva NO sale con el número de la que se acaba de cerrar "
                              f"({primera.hex()} → {segunda.hex()})")
    x.cerrar()

# _id_libre sin server: la veda vence a los 330 s; si todo está vedado, la que se cerró hace más
m = types.SimpleNamespace(salas={}, salas_cerradas={0: 1000.0, 1: 1100.0})
b.igual(sala._id_libre(m, ahora=1200.0), 2, "veda: 0 y 1 se cerraron hace < 330 s → la 2")
b.igual(sala._id_libre(m, ahora=1000.0 + sala.VEDA_DEL_NUMERO), 0, "control: pasada la veda, vuelve la 0")
m = types.SimpleNamespace(salas={i: None for i in range(2, 255)}, salas_cerradas={0: 1000.0, 1: 900.0})
b.igual(sala._id_libre(m, ahora=1100.0), 1, "todas vedadas: la que se cerró hace más")
b.igual(partida.vidas_del_score(8), 5, "4vs4: 5 vidas")
b.fin()
