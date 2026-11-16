# -*- coding: utf-8 -*-
"""probar_sala — crear, listar, entrar, salir, el túnel y empezar. Los formatos son los MEDIDOS en el Legacy."""
from arnes import Banco, ServerDePrueba
from robot import Robot, canjear
from servidor.paquete import con_largo, texto_c

b = Banco("probar_sala")


def entrar(srv, enenos_id):
    _, d = canjear(srv.url_canje, srv.pase(enenos_id))
    r = Robot(*srv.mundo)
    r.login(d["usuario"], d["ticket"])
    r.al_lobby()
    r.todos(0x200E, 0.3)
    return r


AJUSTES_SOLO = bytes.fromhex("b2620000")
AJUSTES_JEWEL = bytes.fromhex("b2620c00")

with ServerDePrueba() as srv:
    a = entrar(srv, 90000001)          # GM en el banco
    c = entrar(srv, 90000002)
    a.todos(0x200E, 0.3)

    # ── crear (lo que manda el Legacy: [largo][título] ajustes(4) clave(4) cupo) ─────────────────────────────
    a.mandar(0x2120, con_largo("Sala uno") + AJUSTES_SOLO + bytes(4) + b"\x02")
    cre = a.esperar(0x2121)
    b.ver(cre is not None and cre[0:5] == b"\0\0\0\0\0", "0x2121: sala creada (id 0)")
    sale = c.esperar(0x200F)
    b.ver(sale is not None, "los del canal ven irse al que creó la sala (0x200F)")

    # ── la lista (0x2103): después de los ajustes van 2 bytes y RECIÉN ahí jugadores y cupo ────────────────
    c.mandar(0x2100, bytes.fromhex("0100000900"))
    lista = c.esperar(0x2103)
    b.igual(bytes(lista[0:4]), b"\0\0\x01\0", "lista: estado 0 y una sala")
    renglon = lista[4:]
    n = renglon[2]
    tras_nombre = renglon[3 + n:]
    b.igual(texto_c(renglon[3:3 + n]), "Sala uno", "lista: el nombre")
    b.igual(bytes(tras_nombre[1:5]), AJUSTES_SOLO, "lista: los ajustes")
    b.igual(bytes(tras_nombre[5:7]), b"\0\0", "lista: los 2 bytes sin identificar")
    b.igual((tras_nombre[7], tras_nombre[8]), (1, 2), "lista: 1 de 2 (si estuvieran corridos saldría «FULL 0/0»)")

    # ── entrar ─────────────────────────────────────────────────────────────────────────────────────────────
    c.mandar(0x2110, b"\0\0" + b"lo")
    b.ver(c.esperar(0x21F5) is not None, "0x21F5 antes de la entrada")
    ent = c.esperar(0x2111)
    nlen = ent[6]
    p = 7 + nlen + 1 + 4 + 8
    b.igual((ent[p], ent[p + 1]), (2, 2), "0x2111: cupo y cantidad")
    ocup = ent[p + 2:]
    # ficha del Legacy: casilla · nick · GÉNERO · ip · puerto · ip · puerto · m1 · m2 · equipo · listo · avatar(8) ·
    #                   4 WORD · cantidad WORD · byte  = 1+12+1+4+2+4+2+3+1+8+8+2+1 = 49
    b.igual(texto_c(ocup[1:13]), "GB90000001", "ocupante 1: el nick")
    b.igual(ocup[13], 0, "ocupante 1: el byte de género va pegado al nick")
    b.igual(bytes(ocup[14:20]), bytes(6), "GB_P2P=tunel (omisión): la dirección P2P va vacía (0.0.0.0:0)")
    b.igual(texto_c(ocup[49 + 1:49 + 13]), "GB90000002", "ocupante 2 empieza 49 bytes después (ficha de 49)")
    aviso = a.esperar(0x3010)
    b.igual(len(aviso), 47, "0x3010 al anfitrión: la misma ficha SIN «listo» ni el byte final (47)")
    b.igual(texto_c(aviso[1:13]), "GB90000002", "0x3010: el nick del que llegó")

    # control: una sala llena no deja entrar a un tercero
    d = entrar(srv, 90000003)
    d.mandar(0x2110, b"\0\0")
    b.ver(d.esperar(0x2111, 0.6) is None, "control: con la sala llena no hay 0x2111")
    b.ver(d.esperar(0x5101, 0.6) is not None, "control: se le avisa por el chat del sistema")

    # ── el túnel: 0x4500 [01 00][casilla destino][datagrama] → 0x4501 [casilla de quien manda][datagrama] ───
    datagrama = bytes.fromhex("1480") + bytes(18)
    c.mandar(0x4500, b"\x01\x00" + b"\x00" + datagrama)
    t = a.esperar(0x4501)
    b.igual(t, b"\x01" + datagrama, "túnel: le llega al de la casilla 0, con la casilla 1 adelante y SIN el destino")
    b.ver(c.esperar(0x4501, 0.4) is None, "control: el que manda no recibe su propio túnel")
    a.mandar(0x4500, b"\x01\x00" + b"\x07" + datagrama)
    b.ver(c.esperar(0x4501, 0.4) is None, "control: a una casilla vacía no le llega a nadie")

    # ── empezar ────────────────────────────────────────────────────────────────────────────────────────────
    c.mandar(0x3430, b"\x01\x02\x03\x04")
    b.ver(a.esperar(0x3432, 0.5) is None, "control: sólo la llave puede empezar")
    a.mandar(0x3430, bytes.fromhex("9e8e2703"))
    ini_a, ini_c = a.esperar(0x3432), c.esperar(0x3432)
    pa, ok_a = a.descifrar(ini_a, 0x3432)
    pc, ok_c = c.descifrar(ini_c, 0x3432)
    b.ver(ok_a and ok_c, "0x3432 cifrado le llega a los dos y cierra")
    b.igual(bytes(pa[0:4]), AJUSTES_SOLO, "0x3432: empieza con los ajustes de la sala (Legacy)")
    b.igual(pa[5] | pa[6] << 8, 2, "0x3432: cantidad en +5")
    b.igual(pa[:7 + 44], pc[:7 + 44], "los dos reciben el mismo arranque (mapa, lugares, móviles y turnos)")
    b.igual(sorted([pa[7 + 20] | pa[7 + 21] << 8, pa[7 + 22 + 20] | pa[7 + 22 + 21] << 8]), [0, 1],
            "los turnos son 0 y 1 (uno cada uno)")
    a.mandar(0x3001, b"\xff\xff")
    b.ver(a.esperar(0x2001) is not None, "salir de la sala devuelve al canal (0x2001)")
    pase_llave = c.esperar(0x3400)
    b.ver(pase_llave is not None and pase_llave[0] == 1, "al irse la llave, pasa al otro (0x3400 con su casilla)")
    for x in (a, c, d):
        x.cerrar()

# GB_P2P=directo: la IP real y el puerto 8363, como el original
with ServerDePrueba(p2p="directo") as srv:
    a = entrar(srv, 90000006)
    c = entrar(srv, 90000007)
    a.mandar(0x2120, con_largo("Directo") + AJUSTES_SOLO + bytes(4) + b"\x02")
    a.esperar(0x2121)
    c.mandar(0x2110, b"\0\0")
    ent = c.esperar(0x2111)
    ocup = ent[7 + ent[6] + 1 + 4 + 8 + 2:]
    b.igual(bytes(ocup[14:20]), bytes([127, 0, 0, 1, 0x20, 0xAB]), "GB_P2P=directo: IP real y puerto 8363 (BE)")
    a.cerrar()
    c.cerrar()

# práctica: Jewel con uno solo
with ServerDePrueba() as srv:
    a = entrar(srv, 90000005)
    a.mandar(0x2120, con_largo("Solo") + AJUSTES_SOLO + bytes(4) + b"\x02")
    a.esperar(0x2121)
    a.mandar(0x5100, b"\x00/practica")
    msg = a.esperar(0x5101)
    b.ver(msg is not None and b"Jewel" in msg and a.esperar(0x3432, 0.3) is None, "control: /practica fuera de Jewel no arranca")
    a.mandar(0x3101, AJUSTES_JEWEL)
    a.esperar(0x3105)
    a.mandar(0x5100, b"\x00/practica")
    ini = a.esperar(0x3432)
    datos, ok = a.descifrar(ini or b"", 0x3432)
    b.ver(ok and datos[5] == 1, "/practica en Jewel arranca con un jugador")
    a.mandar(0x3430, b"")
    b.ver(a.esperar(0x3432, 0.3) is None, "control: ya jugando, no arranca de nuevo")
    a.cerrar()
b.fin()
