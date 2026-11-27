# -*- coding: utf-8 -*-
"""comandos — lo que el jugador escribe en el chat empezando con «/» (el cliente lo manda por 0x5100, en claro).
Las respuestas van por 0x5101 (texto del sistema). ⚠ Sólo ASCII/latin-1: el cliente no dibuja otra cosa.

    /ayuda                 la lista
    /nombre <nick>         cambiar el nick (3 a 12: letras, números y _). Se ve al volver a entrar al mundo
    /genero m|f            varón o mujer (saca lo puesto). Se ve al volver a entrar
    /pais <0-241>          cambia tu bandera (0 = sin país). Se ve al volver a entrar
    /saldo                 oro y cash
    /rango                 rango actual, GP, lo que falta para el próximo, país y puesto
    /practica              en una sala Jewel, solo: empieza sin rival (el botón pide 2 jugadores)
    /movil <0-13|17|18>    fija el móvil principal en la sala
GM (los Eñeños ID de GB_GM):
    /aviso <texto>         a todos los que están en el mundo
    /quien                 quién está y desde dónde
    /dar <nick> <oro> [cash]
    /gp <nick> <n|+n|-n>        fija o suma/resta GP (se ve al volver a entrar)
    /pais <nick> <0-241>        cambia la bandera de otro jugador (0 = sin país; se ve al volver a entrar)
    /rangofijo <nick> <n|auto>  fija un rango manual o vuelve al automático por GP
"""
from . import partida, rangos
from .base import RX_NICK
from .registro import log


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
    _decir(s, "/nombre <nick>  /genero m|f  /pais <0-241>  /saldo  /rango  /practica (Jewel, solo)  /movil <n>")
    if mundo.es_gm(s):
        _decir(s, "GM: /aviso <texto>  /quien  /dar <nick> <oro> [cash]  /gp  /pais <nick> <n>  /rangofijo")


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


def rango(mundo, s, args):
    j = mundo.base.jugador(s.enenos_id)
    r = rangos.rango_de(j)
    nombre_r = rangos.NOMBRES.get(r, str(r))
    sig = rangos.siguiente(j.gp)
    if sig is None:
        avance = "es el maximo"
    else:
        sig_r, falta = sig
        avance = f"faltan {falta} GP para {rangos.NOMBRES.get(sig_r, str(sig_r))}"
    pais_nombre = mundo.paises.get(j.pais) or "sin pais"
    puesto, _ = mundo.base.puestos(j.enenos_id)
    _decir(s, f"Rango: {nombre_r} - GP {j.gp} - {avance} - Pais: {pais_nombre} - Puesto #{puesto}")


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
    if len(args) != 1 or not args[0].isdigit() or int(args[0]) not in list(range(16)) + [17, 18]:
        _decir(s, "Uso: /movil <0-15, 17 o 18>")
        return
    s.movil1 = int(args[0])
    _decir(s, f"Movil principal: {args[0]}")


def avisar(mundo, texto, a=None):
    """El aviso de GM: a todos los del mundo, o sólo a la sesión `a`. -> a cuántos les llegó.
    Lo usan /aviso y el panel del Coordinador (servidor/panel.py)."""
    destinos = list(mundo.sesiones) if a is None else [a]
    for x in destinos:
        _decir(x, texto)
    return len(destinos)


def aviso(mundo, s, args):
    avisar(mundo, " ".join(args))


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


def gp(mundo, s, args):
    if len(args) != 2:
        _decir(s, "Uso: /gp <nick> <n|+n|-n>")
        return
    val = args[1]
    relativo = val.startswith(("+", "-"))
    num_txt = val[1:] if relativo else val
    if not num_txt.isdigit():
        _decir(s, "Uso: /gp <nick> <n|+n|-n>")
        return
    j = mundo.base.por_nick(args[0])
    if j is None:
        _decir(s, "No existe ese nick.")
        return
    n = int(val)
    if relativo:
        mundo.base.sumar(j.enenos_id, gp=n, motivo=f"GM {s.enenos_id}")
    else:
        mundo.base.poner_gp(j.enenos_id, n)
    j2 = mundo.base.jugador(j.enenos_id)
    r_actual = rangos.rango_de(j2)
    _decir(s, f"{j2.nick}: GP {j2.gp} ({rangos.NOMBRES.get(r_actual, str(r_actual))}). El jugador lo ve al volver a entrar.")


def pais(mundo, s, args):
    if len(args) == 1 and args[0].isdigit():
        n = int(args[0])
        if n != 0 and n not in mundo.paises:
            _decir(s, "Pais invalido (0 = sin pais, o 1..241).")
            return
        mundo.base.poner_pais(s.enenos_id, n)
        nombre_p = mundo.paises.get(n) or "sin pais"
        _decir(s, f"Listo: pais {n} ({nombre_p}). Sal del mundo y vuelve a entrar para verlo.")
        return
    if len(args) == 2 and mundo.es_gm(s) and args[1].isdigit():
        n = int(args[1])
        if n != 0 and n not in mundo.paises:
            _decir(s, "Pais invalido (0 = sin pais, o 1..241).")
            return
        j = mundo.base.por_nick(args[0])
        if j is None:
            _decir(s, "No existe ese nick.")
            return
        mundo.base.poner_pais(j.enenos_id, n)
        nombre_p = mundo.paises.get(n) or "sin pais"
        _decir(s, f"{j.nick}: pais {n} ({nombre_p}). El jugador lo ve al volver a entrar.")
        return
    if mundo.es_gm(s):
        _decir(s, "Uso: /pais <0-241>  o  /pais <nick> <0-241>")
    else:
        _decir(s, "Uso: /pais <0-241>  (0 = sin pais)")


def rangofijo(mundo, s, args):
    if len(args) != 2:
        _decir(s, "Uso: /rangofijo <nick> <n|auto>")
        return
    if args[1].lower() == "auto":
        val = None
    else:
        try:
            val = int(args[1])
        except ValueError:
            _decir(s, "Uso: /rangofijo <nick> <n|auto>")
            return
        if not -5 <= val <= 177:            # rank2.img tiene 183 cuadros (valor + 5): del 21 en adelante, VIP, coronas…
            _decir(s, "Rango invalido (de -5 a 177, o auto).")
            return
    j = mundo.base.por_nick(args[0])
    if j is None:
        _decir(s, "No existe ese nick.")
        return
    mundo.base.poner_rango_fijo(j.enenos_id, val)
    j2 = mundo.base.jugador(j.enenos_id)
    r_actual = rangos.rango_de(j2)
    estado = "auto" if val is None else str(val)
    _decir(s, f"{j2.nick}: rango fijo {estado} (queda {rangos.NOMBRES.get(r_actual, str(r_actual))}). El jugador lo ve al volver a entrar.")


COMANDOS = {"ayuda": ayuda, "help": ayuda, "nombre": nombre, "genero": genero, "pais": pais,
            "saldo": saldo, "rango": rango, "practica": practica, "movil": movil, "tankset": movil}
COMANDOS_GM = {"aviso": aviso, "quien": quien, "dar": dar, "gp": gp, "rangofijo": rangofijo}
ATIENDE = {0x5100: comando}
