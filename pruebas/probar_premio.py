# -*- coding: utf-8 -*-
"""probar_premio — el 0x4412 (lo calcula el cliente de la llave) se acredita UNA vez, con los topes del Serv3."""
import struct

from arnes import Banco, ServerDePrueba
from robot import Robot, canjear
from servidor import partida
from servidor.paquete import con_largo

b = Banco("probar_premio")
R = partida.REGISTRO_RESULTADO
AJUSTES = bytes.fromhex("b2620000")


def entrar(srv, eid):
    _, d = canjear(srv.url_canje, srv.pase(eid))
    r = Robot(*srv.mundo)
    r.login(d["usuario"], d["ticket"])
    r.al_lobby()
    r.todos(0x200E, 0.3)
    return r


def saldo(srv, eid):
    """GP y oro como los ve el cliente: volviendo a entrar (0x1012 +61 / +69)."""
    _, d = canjear(srv.url_canje, srv.pase(eid))
    r = Robot(*srv.mundo)
    l = r.login(d["usuario"], d["ticket"])
    r.cerrar()
    return struct.unpack("<I", bytes(l[61:65]))[0], struct.unpack("<I", bytes(l[69:73]))[0]


def resultado(filas):
    return struct.pack("<H", len(filas)) + b"".join(R.pack(*f) for f in filas)


def partida_de_dos(srv, a_id, c_id, nombre):
    a, c = entrar(srv, a_id), entrar(srv, c_id)
    a.mandar(0x2120, con_largo(nombre) + AJUSTES + bytes(4) + b"\x02")
    sala_id = a.esperar(0x2121)[3:5]          # 0x2121: 00 00 00 + id WORD (con id 0 daba igual [2:4])
    c.mandar(0x2110, bytes(sala_id))
    c.esperar(0x2111)
    a.mandar(0x3430, b"\x01\x02\x03\x04")
    a.esperar(0x3432), c.esperar(0x3432)
    return a, c


with ServerDePrueba(oro_inicial=1000) as srv:
    a, c = partida_de_dos(srv, 90000041, 90000042, "Premio")
    # ganó la casilla 0 (1vs1: 3 GP + 100 de victoria, más un remate: 1 GP + 100) y perdió la 1
    filas = [(0, 200, 0, 4, 3, 450, 1), (1, 25, 0, 0, 2, 120, 0)]
    c.mandar_cifrado(0x4412, resultado([(0, 6000, 0, 50, 0, 0, 1), (1, 6000, 0, 50, 0, 0, 1)]))
    b.ver(c.esperar(0x4413, 0.5) is not None, "el que no es la llave igual recibe el cierre (0x4413)")
    a.mandar_cifrado(0x4412, resultado(filas))
    b.ver(a.esperar(0x4413) is not None, "la llave manda el resultado y recibe 0x4413")
    a.mandar_cifrado(0x4412, resultado(filas))                    # repetido
    a.esperar(0x4413, 0.5)
    a.cerrar(); c.cerrar()
    b.igual(saldo(srv, 90000041), (4, 1200), "el ganador: +4 GP y +200 de oro, UNA vez (control: ni el del "
                                              "no-llave ni el repetido)")
    b.igual(saldo(srv, 90000042), (0, 1025), "el que perdió: +25 de oro de sus tiros")

    a, c = partida_de_dos(srv, 90000043, 90000044, "Tramposo")
    a.mandar_cifrado(0x4412, resultado([(0, 9999, 0, 51, 0, 0, 1), (1, 300, 0, 3, 0, 0, 1)]))
    a.esperar(0x4413)
    a.cerrar(); c.cerrar()
    b.igual(saldo(srv, 90000043), (0, 1000), "control: 51 GP / 9999 de oro pasa el tope → no se acredita")
    b.igual(saldo(srv, 90000044), (3, 1300), "el otro registro de la misma partida sí")

    # práctica (solo): no paga
    p = entrar(srv, 90000045)
    p.mandar(0x2120, con_largo("Solo") + bytes.fromhex("b2620c00") + bytes(4) + b"\x02")
    p.esperar(0x2121)
    p.mandar(0x5100, b"\x00/practica")
    p.esperar(0x3432)
    p.mandar_cifrado(0x4412, resultado([(0, 500, 0, 10, 0, 0, 1)]))
    b.ver(p.esperar(0x4413) is not None, "la práctica también cierra")
    p.cerrar()
    b.igual(saldo(srv, 90000045), (0, 1000), "control: la práctica no paga")

b.igual(partida.leer_resultado(resultado([(0, 1, 0, 1, 0, 0, 1), (0, 1, 0, 1, 0, 0, 1)])), None,
        "control: casillas repetidas → se descarta")
b.igual(len(partida.leer_resultado(resultado([(i, 1, 0, 1, 0, 0, i % 2) for i in range(8)]) + bytes(10))), 8,
        "8 jugadores con relleno del cifrado")
b.fin()
