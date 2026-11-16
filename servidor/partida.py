# -*- coding: utf-8 -*-
"""partida — empezar y lo que pasa durante la partida.

0x3432 (empieza la partida), CIFRADO, medido en el Legacy (rama 0x004ECDAB):
    ajustes de la sala (4) · mapa (1) · cantidad (WORD) ·
    por jugador 22 bytes: casilla · nick (12) · equipo · móvil 1 · móvil 2 · X (WORD) · Y (WORD) · turno (WORD) ·
    la cola: marca de evento (WORD, FFFF = ninguno) · semilla (4) · 6 joyas × (posición WORD + 0)
⚠ Sin los 4 bytes de ajustes adelante (el formato del Serv2) el Legacy lee el mapa corrido.

Lo que pasa adentro de la partida (disparos, movimientos) lo hablan los clientes ENTRE ELLOS por UDP (puerto 8363).
Si no se ven (NAT), el cliente pide el TÚNEL (0x4500) y el server reenvía.
⚠ El túnel y el cobro del premio al final no están medidos todavía con dos clientes de verdad: se anotan crudos
   en el registro para medirlos.
"""
import random
import secrets

from .paquete import fijo, u8, u16
from .registro import log
from .sala import ESPERA, JUGANDO
from .sesion import AL_AZAR

MOVILES = list(range(0, 14))           # Armor … Aduka
ESPECIALES = (17, 18)                  # Dragón y Caballero (en el Serv2 eran 14/15; en éste, 17/18)
JEWEL = 0x0C


def _movil_al_azar(mundo):
    if random.randint(1, 100) <= mundo.prob_dragon:
        return random.choice(ESPECIALES)
    return random.choice(MOVILES)


def armar_inicio(mundo, x, cola_del_anfitrion=b"", solo=False):
    if x.mapa == 0:                          # «al azar»
        x.mapa = random.choice([m for m in mundo.mapas if m != 0] or [1])
    datos_mapa = mundo.mapas.get(x.mapa) or mundo.mapas.get(1)
    lado_b = x.ajustes[2] & 1 if len(x.ajustes) > 2 else 0
    puntos = datos_mapa["positions_b_side" if lado_b else "positions_a_side"]
    orden_lugar = list(range(len(puntos)))
    random.shuffle(orden_lugar)
    orden_turno = list(range(len(x.jugadores)))
    random.shuffle(orden_turno)
    r = bytearray(x.ajustes + u8(x.mapa) + u16(len(x.jugadores)))
    for i, s in enumerate(x.jugadores):
        if s.movil1 == AL_AZAR:
            s.movil1 = _movil_al_azar(mundo)
        if s.movil2 == AL_AZAR:
            s.movil2 = _movil_al_azar(mundo)
        p = puntos[orden_lugar[s.casilla % len(puntos)]]
        px = random.randint(p["x_min"], p["x_max"])
        py = p["y"] or 0
        r += u8(s.casilla) + fijo(s.nick, 12) + u8(s.equipo) + u8(s.movil1) + u8(s.movil2) + u16(px) + u16(py) + u16(orden_turno[i])
    if not solo and len(cola_del_anfitrion) >= 22:
        r += b"\xFF\xFF" + cola_del_anfitrion[:22]       # la semilla y las joyas que sorteó el anfitrión
    else:
        r += b"\xFF\xFF" + secrets.token_bytes(4)
        for _ in range(6):
            r += secrets.token_bytes(2) + b"\x00"
    return bytes(r)


def empezar(mundo, s, cuerpo, solo=False):
    """0x3430: lo pide la llave. El cuerpo es lo que sorteó el anfitrión (se anota para medirlo)."""
    x = s.sala
    if x is None or x.llave is not s or x.estado != ESPERA:
        return
    if not solo and len(x.jugadores) < 2:
        s.enviar(0x5101, b"Para jugar solo: crea una sala Jewel y escribe /practica")
        return
    log("PARTIDA", f"sala {x.id}: empieza ({len(x.jugadores)} jugadores, mapa {x.mapa}, modo 0x{x.modo:02X}) · "
                   f"cuerpo del anfitrión {len(cuerpo)} bytes {bytes(cuerpo[:40]).hex()}")
    x.estado = JUGANDO
    inicio = armar_inicio(mundo, x, bytes(cuerpo), solo=solo)
    for o in x.jugadores:
        o.enviar_cifrado(0x3432, inicio)


def fin_jewel(mundo, s, cuerpo):
    """0x4200: el anfitrión avisa el fin del Jewel; se reparte a todos como 0x4410."""
    datos, _ = s.descifrar(cuerpo, 0x4200)
    if s.sala:
        for o in s.sala.jugadores:
            o.enviar_cifrado(0x4410, datos)


def murio(mundo, s, cuerpo):
    log("PARTIDA", f"{s.nick} murió · {bytes(cuerpo[:24]).hex()}")
    s.enviar(0x4101)


def resultado(mundo, s, cuerpo):
    """0x4412: el anfitrión pide el resultado; todos reciben 0x4413. ⚠ El premio NO se acredita todavía (sin medir)."""
    log("PARTIDA", f"{s.nick} pide el resultado · {len(cuerpo)} bytes {bytes(cuerpo[:64]).hex()}")
    if s.sala:
        for o in s.sala.jugadores:
            o.enviar(0x4413)


def tunel(mundo, s, cuerpo):
    """0x4500: el cliente no puede hablar directo (UDP) con otros de la sala y le pide al server que pase el mensaje.

    MEDIDO en el Legacy (16-nov, dos clientes en la misma PC: el 2.º no consigue el puerto UDP 8363 y tunela todo):
        enviado  0x4500: [01 00 (fijo)][casilla DESTINO][datagrama P2P]   (lo arma 0x44D530)
        recibido 0x4501: [casilla de QUIEN LO MANDA][datagrama P2P]       (lector 0x4106DC → CCommP2P 0x44D4C0)
    El datagrama empieza con su largo (WORD & 0x3FFF, cabecera incluida): el server no lo toca.
    ⚠ Si al 0x4501 se le deja el byte de destino, el que lo recibe lee corrido y SE CIERRA (medido).
    ⚠ El formato del Serv2 (nombres de 12 bytes de origen y destino) NO es el de este cliente."""
    if s.sala is None or len(cuerpo) < 5:
        return
    destino = cuerpo[2]
    datos = bytes(cuerpo[3:])
    for o in s.sala.jugadores:
        if o is not s and o.casilla == destino:
            o.enviar(0x4501, u8(s.casilla) + datos)
            return
    log("TUNEL", f"{s.nick} → casilla {destino}: no hay nadie ahí en la sala {s.sala.id}")


ATIENDE = {0x3430: empezar, 0x4200: fin_jewel, 0x4100: murio, 0x4412: resultado, 0x4500: tunel}
