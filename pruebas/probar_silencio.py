# -*- coding: utf-8 -*-
"""probar_silencio — el corte por silencio en el TCP del mundo.

Jugando con P2P directo el cliente no manda NADA por TCP (no tiene keepalive propio): el server no puede cortarlo
por callado. Fuera de partida sí (control). El plazo se achica a 0,4 s para que la prueba no tarde 10 minutos.
"""
import time

from arnes import Banco, ServerDePrueba
from robot import Robot, canjear
from servidor import mundo
from servidor.paquete import con_largo

b = Banco("probar_silencio")
mundo.SILENCIO_MAXIMO = 0.4


def entrar(srv, enenos_id):
    _, d = canjear(srv.url_canje, srv.pase(enenos_id))
    r = Robot(*srv.mundo)
    r.login(d["usuario"], d["ticket"])
    r.al_lobby()
    r.todos(0x200E, 0.3)
    return r


def sigue_conectado(r, segundos):
    """Escucha callado `segundos`: False si el server cortó."""
    fin = time.time() + segundos
    try:
        while time.time() < fin:
            r._leer(fin - time.time())
    except (ConnectionError, OSError):
        return False
    return True


with ServerDePrueba() as srv:
    quieto = entrar(srv, 90000011)                 # se queda en el canal sin decir nada
    jugando = entrar(srv, 90000012)                # arranca una práctica y se calla
    jugando.mandar(0x2120, con_largo("Larga") + bytes.fromhex("b2620c00") + bytes(4) + b"\x02")
    jugando.esperar(0x2121)
    jugando.mandar(0x5100, b"\x00/practica")
    b.ver(jugando.esperar(0x3432) is not None, "la práctica arrancó (la sala está JUGANDO)")
    b.ver(sigue_conectado(jugando, 1.5), "jugando y callado por TCP (P2P directo): NO se lo corta")
    b.ver(not sigue_conectado(quieto, 1.5), "control: callado en el canal, fuera de partida, SÍ se lo corta")
    jugando.cerrar()
    quieto.cerrar()
b.fin()
