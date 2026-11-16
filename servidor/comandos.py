# -*- coding: utf-8 -*-
"""comandos — lo que el jugador escribe en el chat empezando con «/» (el cliente lo manda por 0x5100, en claro).
Las respuestas van por 0x5101 (texto del sistema). ⚠ Sólo ASCII/latin-1: el cliente no dibuja otra cosa.

    /ayuda                 la lista
    /nombre <nick>         cambiar el nick (3 a 12: letras, números y _). Se ve al volver a entrar al mundo
    /genero m|f            varón o mujer (saca lo puesto). Se ve al volver a entrar
    /saldo                 oro y cash
    /practica              en una sala Jewel, solo: empieza sin rival (el botón pide 2 jugadores)
    /movil <0-13|17|18>    fija el móvil principal en la sala
GM (los Eñeños ID de GB_GM):
    /aviso <texto>         a todos los que están en el mundo
    /quien                 quién está y desde dónde
    /dar <nick> <oro> [cash]
"""
import re

from . import partida
from .registro import log

RX_NICK = re.compile(r"^[A-Za-z0-9_]{3,12}$")


def _decir(s, texto):
    s.enviar(0x5101, texto.encode("latin-1", "replace"))


def comando(mundo, s, cuerpo):
    texto = bytes(cuerpo[1:]).split(b"\0")[0].decode("latin-1").strip()
    if texto.startswith("/"):
        texto = texto[1:]
    partes = texto.split()
    if not partes:
        return
    nombre, args = partes[0].lower(), partes[1:]
    log("COMANDO", f"{s.nick}: /{texto}")
    f = COMANDOS.get(nombre) or (COMANDOS_GM.get(nombre) if mundo.es_gm(s) else None)
    if f is None:
        _decir(s, f"No conozco /{nombre}. Escribe /ayuda")
        return
    f(mundo, s, args)


def ayuda(mundo, s, args):
    _decir(s, "/nombre <nick>  /genero m|f  /saldo  /practica (Jewel, solo)  /movil <n>")
    if mundo.es_gm(s):
        _decir(s, "GM: /aviso <texto>  /quien  /dar <nick> <oro> [cash]")


def nombre(mundo, s, args):
    if len(args) != 1 or not RX_NICK.match(args[0]):
        _decir(s, "Uso: /nombre <nick>  (3 a 12 letras, numeros o _)")
        return
    motivo = mundo.base.poner_nick(s.enenos_id, args[0])
    if motivo:
        _decir(s, f"No se pudo: {motivo}.")
        return
    _decir(s, f"Listo: te vas a llamar {args[0]}. Sal del mundo y vuelve a entrar para verlo.")


def genero(mundo, s, args):
    if len(args) != 1 or args[0].lower() not in ("m", "f"):
        _decir(s, "Uso: /genero m  o  /genero f")
        return
    mundo.base.poner_genero(s.enenos_id, args[0].lower() == "f")
    _decir(s, "Listo. Sal del mundo y vuelve a entrar para verlo (lo que tenias puesto se guardo en el inventario).")


def saldo(mundo, s, args):
    j = mundo.base.jugador(s.enenos_id)
    _decir(s, f"Oro: {j.oro}   Cash: {j.cash}")


def practica(mundo, s, args):
    x = s.sala
    if x is None or x.llave is not s or len(x.jugadores) != 1 or x.estado != 0:
        _decir(s, "Crea una sala Jewel y espera a estar solo en ella.")
        return
    if x.modo != partida.JEWEL:
        _decir(s, "La practica es en modo Jewel.")
        return
    partida.empezar(mundo, s, b"", solo=True)


def movil(mundo, s, args):
    if len(args) != 1 or not args[0].isdigit() or int(args[0]) not in list(range(14)) + [17, 18]:
        _decir(s, "Uso: /movil <0-13, 17 o 18>")
        return
    s.movil1 = int(args[0])
    _decir(s, f"Movil principal: {args[0]}")


def aviso(mundo, s, args):
    t = " ".join(args)
    for x in mundo.sesiones:
        _decir(x, t)


def quien(mundo, s, args):
    for x in mundo.sesiones:
        _decir(s, f"{x.nick} #{x.enenos_id} {x.ip} {'sala ' + str(x.sala.id) if x.sala else 'canal'}")


def dar(mundo, s, args):
    if len(args) < 2 or not all(a.lstrip("-").isdigit() for a in args[1:]):
        _decir(s, "Uso: /dar <nick> <oro> [cash]")
        return
    j = mundo.base.por_nick(args[0])
    if j is None:
        _decir(s, "No existe ese nick.")
        return
    oro_, cash_ = int(args[1]), int(args[2]) if len(args) > 2 else 0
    mundo.base.sumar(j.enenos_id, oro=oro_, cash=cash_, motivo=f"GM {s.enenos_id}")
    _decir(s, f"{j.nick}: oro {oro_:+d}, cash {cash_:+d}")


COMANDOS = {"ayuda": ayuda, "help": ayuda, "nombre": nombre, "genero": genero, "saldo": saldo,
            "practica": practica, "movil": movil, "tankset": movil}
COMANDOS_GM = {"aviso": aviso, "quien": quien, "dar": dar}
ATIENDE = {0x5100: comando}
