# -*- coding: utf-8 -*-
"""partida — empezar y lo que pasa durante la partida.

0x3432 (empieza la partida), CIFRADO, medido en el Legacy (rama 0x004ECDAB):
    ajustes de la sala (4) · mapa (1) · cantidad (WORD) ·
    por jugador 22 bytes: casilla · nick (12) · equipo · móvil 1 · móvil 2 · X (WORD) · Y (WORD) · turno (WORD) ·
    la cola: marca de evento (WORD, FFFF = ninguno) · semilla (4) · 6 joyas × (posición WORD + 0)
⚠ Sin los 4 bytes de ajustes adelante (el formato del Serv2) el Legacy lee el mapa corrido.

Lo que pasa adentro de la partida (disparos, movimientos) lo hablan los clientes ENTRE ELLOS por UDP (puerto 8363).
Si no se ven (NAT), el cliente pide el TÚNEL (0x4500) y el server reenvía.

EL PREMIO (0x4412 → 0x4413). Lo CALCULA EL CLIENTE (medido por Codex en el exe, 16-nov:
documentacion/investigacion/PAGOS_GP_Y_ORO.md): la llave manda, al terminar, un registro de 18 bytes por jugador con
el oro y el GP YA GANADOS (victoria 3/6/9/12 GP y 100/150/200/300 de oro por 1vs1…4vs4, más remates, tiros, daño,
joyas, penalizaciones; con los factores del login ya aplicados). El server no recalcula: valida y acredita UNA vez.
Los topes son los de fábrica del Serv3 (`ANU_*`): un registro fuera de rango no se acredita (no se recorta).

EL FIN DE SOLO, SCORE Y TAG LO DECIDE EL SERVER (19-nov; copiado del Serv3, `GunBoundServ3.exe` Perú —
documentacion/investigacion/FIN_DE_PARTIDA_Y_SCORE.md). El cliente avisa cada muerte (0x4100) y cada reaparición
(0x4104); el server lleva quién está caído y, cuando corresponde, manda 0x4410 [ganador] a todos. Sin ese 0x4410 la
partida no termina nunca (lo que pasó en el ensayo) y el ganador no cobra el bono de victoria: el bono lo suma el
lector del 0x4410 (0x004106F4 → 0x004107BE). Sólo el Jewel lo cierra el cliente (0x4200).
    DeadUser      0x4180F0: [casilla][DWORD causa][byte quién] → 0x4102 cifrado a TODOS · Score: suma la baja
    CheckPlayEnd  0x4183E0: Score: bajas de un equipo >= vidas → gana el otro. Si no: ajustes[0] bit 0x80 (equipos)
                            → si los vivos son de UN solo equipo, gana ése; sin el bit, el último vivo (su casilla).
                            Nadie vivo → 0xFF (empate).
    Resurrect     0x418210: 0x4104 cifrado [casilla] → vuelve a estar vivo (sólo Score y Jewel) · 0x4106 [casilla]
    vidas         0x415F55: en Score, al empezar: jugadores / 2 + 1 en el nibble alto del byte [2] de los ajustes
    quien se va   0x4145BF: si se va uno vivo a mitad de partida, cuenta como muerto (causa 0xF000, quién 0xFF)
"""
import random
import secrets
import struct

from .paquete import fijo, u8, u16
from .registro import log
from .sala import ESPERA, JUGANDO
from .sesion import AL_AZAR

MOVILES = list(range(0, 14))           # Armor … Aduka
ESPECIALES = (17, 18)                  # Dragón y Caballero (en el Serv2 eran 14/15; en éste, 17/18)
JEWEL = 0x0C
SCORE = 0x04
POR_EQUIPOS = 0x80                     # ajustes[0]: el fin se decide por equipos (el Legacy lo manda siempre: b2…)
SIN_GANADOR = 0xFF
CAUSA_SE_FUE = 0xF000                  # la «causa» con que el Serv3 da por muerto al que abandona


def tipo_de_juego(ajustes):
    """Los bits 18–19 de los ajustes (byte [2] & 0x0C): 0 solo · 4 score · 8 tag · 0C jewel."""
    return ajustes[2] & 0x0C if len(ajustes) > 2 else 0


def vidas_del_score(cantidad):
    """Serv3 0x415F6C: (jugadores / 2) + 1. 1vs1 → 2 · 2vs2 → 3 · 4vs4 → 5. (El cliente cuenta las suyas aparte:
    jugadores de cada equipo + 1, 0x004D61A8.)"""
    return cantidad // 2 + 1


def ajustes_de_partida(ajustes, cantidad):
    """Los ajustes que van en el 0x3432: en Score el Serv3 pone las vidas en el nibble alto del byte [2]."""
    a = bytearray(ajustes)
    if len(a) > 2 and tipo_de_juego(a) == SCORE:
        a[2] = (a[2] & 0x0F) | (min(vidas_del_score(cantidad), 15) << 4)
    return bytes(a)


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
    r = bytearray(ajustes_de_partida(x.ajustes, len(x.jugadores)) + u8(x.mapa) + u16(len(x.jugadores)))
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
    x.premio_cobrado = False
    x.practica = solo
    x.caidos = set()                                   # casillas muertas AHORA (las que reaparecen salen)
    x.bajas = [0, 0]                                   # Score: muertes del equipo A y del B
    x.equipos = {o.casilla: o.equipo for o in x.jugadores}
    x.vidas = vidas_del_score(len(x.jugadores))
    x.ganador = None
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
    """0x4100 (sin cifrar): [causa DWORD][quién byte], lo arma 0x4E91E3. Causa 1 = lo mató otro, 3 = suicidio
    (INFERIDO de los logs del ensayo). El Serv3 contesta 0x4101 [WORD 0] al que murió (el Legacy no lo lee)."""
    causa = struct.unpack_from("<I", bytes(cuerpo))[0] if len(cuerpo) >= 4 else 0
    quien = cuerpo[4] if len(cuerpo) >= 5 else SIN_GANADOR
    log("PARTIDA", f"{s.nick} murió · {bytes(cuerpo[:24]).hex()}")
    if s.sala is not None and s.sala.estado == JUGANDO:
        caer(mundo, s.sala, s.casilla, causa, quien)
    s.enviar(0x4101, rtc=0)


def caer(mundo, x, casilla, causa, quien, salvo=None):
    """DeadUser del Serv3 (0x4180F0). `salvo`: a quién no mandarle los avisos (el que se está yendo)."""
    if not hasattr(x, "caidos"):
        return
    if casilla in x.caidos:
        log("PARTIDA", f"sala {x.id}: la casilla {casilla} ya estaba muerta")
        return
    x.caidos.add(casilla)
    aviso = u8(casilla) + struct.pack("<I", causa & 0xFFFFFFFF) + u8(quien)
    for o in x.jugadores:
        if o is not salvo:
            o.enviar_cifrado(0x4102, aviso)
    if tipo_de_juego(x.ajustes) == SCORE:
        equipo = x.equipos.get(casilla, 0)
        if equipo in (0, 1):
            x.bajas[equipo] += 1
    ver_fin(mundo, x, salvo=salvo)


def ver_fin(mundo, x, salvo=None):
    """CheckPlayEnd del Serv3 (0x4183E0). Si la partida terminó: 0x4410 [ganador] cifrado a todos, UNA vez.
    (La /practica no se cierra sola: la cierra el jugador.)"""
    if x.ganador is not None or getattr(x, "practica", False):
        return None
    ganador = None
    if tipo_de_juego(x.ajustes) == SCORE:
        if x.bajas[1] >= x.vidas:
            ganador = 0
        elif x.bajas[0] >= x.vidas:
            ganador = 1
    if ganador is None:
        vivos = [o for o in x.jugadores if o.casilla not in x.caidos]
        if x.ajustes[0] & POR_EQUIPOS:
            equipos = {x.equipos.get(o.casilla, o.equipo) for o in vivos}
            if len(equipos) > 1:
                return None
            ganador = equipos.pop() if equipos else SIN_GANADOR
        else:
            if len(vivos) > 1:
                return None
            ganador = vivos[0].casilla if vivos else SIN_GANADOR
    x.ganador = ganador
    log("PARTIDA", f"sala {x.id}: terminó · ganador {ganador} · bajas A {x.bajas[0]} B {x.bajas[1]} (vidas {x.vidas})")
    for o in x.jugadores:
        if o is not salvo:
            o.enviar_cifrado(0x4410, u8(ganador))
    return ganador


def reaparecer(mundo, s, cuerpo):
    """0x4104 (cifrado) [casilla]: lo manda el cliente al reaparecer (0x463EC5, sólo Score y Jewel). Resurrect del
    Serv3 (0x418210): vuelve a estar vivo y se avisa 0x4106 [casilla] a todos; al que lo pidió, 0x4105 [WORD 0].
    Sin esto, el que reapareció seguiría «muerto» para el server y el fin por equipo entero muerto saltaría mal."""
    datos, ok = s.descifrar(cuerpo, 0x4104)
    x = s.sala
    if not ok or not datos or x is None or x.estado != JUGANDO or not hasattr(x, "caidos"):
        log("PARTIDA", f"{s.nick} reaparece fuera de partida o con el cifrado mal · {bytes(cuerpo[:16]).hex()}")
        return
    casilla = datos[0]
    if tipo_de_juego(x.ajustes) not in (SCORE, JEWEL):
        log("PARTIDA", f"sala {x.id}: {s.nick} pide reaparecer y el modo no es Score ni Jewel")
    elif casilla not in x.caidos:
        log("PARTIDA", f"sala {x.id}: {s.nick} pide reaparecer la casilla {casilla}, que no está muerta")
    else:
        x.caidos.discard(casilla)
        log("PARTIDA", f"sala {x.id}: reaparece la casilla {casilla} ({s.nick})")
        for o in x.jugadores:
            o.enviar_cifrado(0x4106, u8(casilla))
    s.enviar(0x4105, rtc=0)


REGISTRO_RESULTADO = struct.Struct("<BihhIIB")     # casilla · oro (i32) · evento (i16) · GP (i16) · tiros · daño · resultado
# Los topes de fábrica del Serv3 (GunBoundServ3.exe 0x403CA5, opciones ANU_*): por jugador y por partida.
TOPE_GP, TOPE_ORO = 50, 6000                 # más que esto: no se acredita (anómalo)
PISO_GP, PISO_ORO = -100, -2500              # menos que esto: tampoco
AVISO_GP, AVISO_ORO = 30, 3000               # más que esto: se acredita pero queda anotado


def leer_resultado(datos):
    """El cuerpo DESCIFRADO del 0x4412 → [(casilla, oro, evento, gp, tiros, daño, resultado)], o None si no cierra.
    (El descifrado trae relleno hasta múltiplo de 12: se ignora.)"""
    if len(datos) < 2:
        return None
    n = datos[0] | datos[1] << 8
    if not 1 <= n <= 8 or len(datos) < 2 + n * REGISTRO_RESULTADO.size:
        return None
    filas = [REGISTRO_RESULTADO.unpack_from(datos, 2 + i * REGISTRO_RESULTADO.size) for i in range(n)]
    casillas = [f[0] for f in filas]
    if len(set(casillas)) != n or any(c > 7 for c in casillas) or any(f[6] > 2 for f in filas):
        return None
    return filas


def resultado(mundo, s, cuerpo):
    """0x4412: la llave manda el resultado (lo calculó su cliente). Se acredita oro y GP una vez; todos reciben 0x4413.
    Sin acreditar: si no lo manda la llave, si no hay partida, si ya se cobró, o si es una /practica (solo)."""
    x = s.sala
    datos, ok = s.descifrar(cuerpo, 0x4412)
    filas = leer_resultado(bytes(datos)) if ok else None
    log("PARTIDA", f"{s.nick} manda el resultado · {len(cuerpo)} bytes · {filas}")
    if x is None:
        return
    if x.llave is s and x.estado == JUGANDO and not getattr(x, "premio_cobrado", True) and filas:
        x.premio_cobrado = True
        if getattr(x, "practica", False) or len(x.jugadores) < 2:
            log("PREMIO", f"sala {x.id}: práctica, no se acredita")
        else:
            _acreditar(mundo, x, filas)
    for o in x.jugadores:
        o.enviar(0x4413)


def _acreditar(mundo, x, filas):
    por_casilla = {o.casilla: o for o in x.jugadores}
    for casilla, oro, evento, gp, tiros, dano, res in filas:
        o = por_casilla.get(casilla)
        if o is None or o.jugador is None:
            continue
        if not (PISO_GP <= gp <= TOPE_GP and PISO_ORO <= oro <= TOPE_ORO):
            log("PREMIO", f"⚠ sala {x.id} {o.nick}: {gp:+d} GP {oro:+d} oro FUERA DE RANGO, no se acredita")
            mundo.base.anotar(o.enenos_id, "premio_rechazado", f"gp{gp:+d} oro{oro:+d} sala {x.id}")
            continue
        if gp > AVISO_GP or oro > AVISO_ORO:
            log("PREMIO", f"⚠ sala {x.id} {o.nick}: {gp:+d} GP {oro:+d} oro (alto, se acredita)")
        mundo.base.sumar(o.enenos_id, oro=oro, gp=gp,
                         motivo=f"partida sala {x.id} {('perdió', 'ganó', 'empate')[res]} tiros {tiros} daño {dano}")
        o.jugador = mundo.base.jugador(o.enenos_id)          # el rango nuevo se ve en las fichas de sala
        log("PREMIO", f"sala {x.id} {o.nick}: {gp:+d} GP {oro:+d} oro ({('perdió', 'ganó', 'empate')[res]})")


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


ATIENDE = {0x3430: empezar, 0x4200: fin_jewel, 0x4100: murio, 0x4104: reaparecer, 0x4412: resultado,
           0x4500: tunel}
