# -*- coding: utf-8 -*-
"""sala — las salas de espera: la lista, crear, entrar, salir y las opciones (mapa, modo, cupo, título).

Lo que es de la SALA vive acá (mapa, ajustes, cupo, quién es la llave). Lo del jugador DENTRO de la sala (casilla,
equipo, móviles) vive en su `Sesion`.

Los AJUSTES de la sala son 4 bytes que el server no interpreta: los arma el cliente y el server los reparte.
El byte [2] lleva el modo: 0x00 solo · 0x44 score · 0x08 tag · 0x0C jewel. Su bit 0 = el lado del mapa (A/B).

La entrada a una sala (0x2111), medida en el Legacy (rama 0x004CB8C5):
    WORD resultado · 2 bytes de estado · WORD sala · BYTE largo + nombre · mapa · ajustes (4) · 8 bytes ·
    cupo · cantidad · y una ficha por ocupante
La ficha de cada ocupante: ver `ficha_ocupante` (medida con dos clientes).
"""
import time

from . import canal, rangos
from .paquete import con_largo, fijo, texto_c, u8, u16
from .registro import log
from .sesion import AL_AZAR, SIN_LUGAR

ESPERA, JUGANDO = 0, 1
VEDA_DEL_NUMERO = 330              # s sin volver a usar el número de una sala cerrada (el cliente veda 300 s)
PUERTO_P2P = 8363                  # el cliente escucha UDP acá para hablar con los otros de la sala


class Sala:
    def __init__(self, id_, nombre, clave, ajustes, cupo, llave):
        self.id = id_
        self.nombre = nombre
        self.clave = clave
        self.mapa = 0
        self.ajustes = bytes(ajustes)
        self.cupo = cupo
        self.estado = ESPERA
        self.jugadores = []
        self.llave = llave           # la Sesion del anfitrión

    @property
    def modo(self):
        return self.ajustes[2] & 0xFC if len(self.ajustes) > 2 else 0

    def casilla_libre(self):
        usadas = {x.casilla for x in self.jugadores}
        for i in range(16):
            if i not in usadas:
                return i
        return None

    def equipo_para_el_nuevo(self):
        a = sum(1 for x in self.jugadores if x.equipo == 0)
        return 1 if a > len(self.jugadores) - a else 0

    def entrada_de_lista(self):
        """Un renglón de 0x2103. MEDIDO en el lector del Legacy (0x4CB55A): después de los ajustes hay DOS bytes
        (sin identificar: van en 0) y recién ahí jugadores · cupo · jugando · con clave. «Llena» = jugadores == cupo.
        (Con el formato del Serv2, sin esos dos bytes, la sala salía «FULL 0/0».)"""
        return (u16(self.id) + con_largo(self.nombre) + u8(self.mapa) + self.ajustes + b"\x00\x00"
                + u8(len(self.jugadores)) + u8(self.cupo) + u8(self.estado) + u8(1 if self.clave else 0))


def _id_libre(mundo, ahora=None):
    """El número de una sala nueva. ⚠ NO se reusa enseguida el de una sala que se cerró (MEDIDO en el Legacy, 19-nov):
    al ABANDONAR una partida (botón 400, 0x004FA2D1) o al ser echado (0x004EC9E8, 0x004D0D33), el cliente anota el
    número de esa sala (0x00425DA0: servidor + sala + ahora + 300 s, hasta 64) y por 5 minutos NO MANDA el 0x2110
    para entrar a una sala con ese número (0x004CF338 / 0x00500476 → 0x00425F90), sin avisar nada.
    Con el «primer número libre» la sala nueva salía con el MISMO número que la abandonada y nadie podía entrar."""
    ahora = time.monotonic() if ahora is None else ahora
    cerradas = mundo.__dict__.setdefault("salas_cerradas", {})
    libres = [i for i in range(255) if i not in mundo.salas]
    if not libres:
        return None
    for i in libres:
        if ahora - cerradas.get(i, -1e9) >= VEDA_DEL_NUMERO:
            return i
    return min(libres, key=lambda i: cerradas.get(i, -1e9))     # todas vedadas: la que se cerró hace más


def _ip4(ip):
    try:
        return bytes(int(p) for p in ip.split("."))
    except ValueError:
        return bytes(4)


def ficha_ocupante(x, en_la_lista=True):
    """Un ocupante de la sala. MEDIDO en los lectores del Legacy: 0x2111 (0x4CBA60) y 0x3010 (0x4102E0).

        casilla · nick (12) · género (0 = varón) · IP (4) · puerto (2) · IP (4) · puerto (2) ·
        móvil 1 · móvil 2 · equipo · [listo: SÓLO en 0x2111] · avatar (8) ·
        4 WORD (rangos: el cliente les suma 5 a los tres primeros) · cantidad de piezas extra (WORD) + DWORD c/u ·
        [un byte más: SÓLO en 0x2111]

    ⚠ Con la ficha del Serv2 (sin género, con gremio) el anfitrión veía el nombre con basura y el que entraba no
       veía al anfitrión. Los puertos van como estaban en el server medido (0x20AB = 8363).

    ★ La dirección P2P (IP + puerto, dos veces) decide cómo se hablan los clientes durante la sala y la partida.
      Por omisión (`GB_P2P=directo`, como el original) va la IP real: prueban UDP directo y, si en 2 s no llega nada
      del otro, pasan al TÚNEL del server (el cliente de Eñeños trae el parche 6: el original esperaba 20 s, y si
      nadie empezaba la partida en los ~30 s siguientes el invitado se iba de la sala).
      `GB_P2P=tunel`: va vacía (0.0.0.0:0) y todo pasa por el túnel. Es para probar varios clientes en UNA PC: ahí
      comparten IP y puerto 8363, y el directo del anfitrión le vuelve a él mismo (medido)."""
    j = x.jugador
    ip, puerto = (_ip4(x.ip), PUERTO_P2P) if x.p2p_directo else (bytes(4), 0)
    r = (u8(x.casilla) + fijo(j.nick, 12) + u8(j.byte_genero) + ip + u16_be(puerto) + ip + u16_be(puerto)
         + u8(x.movil1) + u8(x.movil2) + u8(x.equipo))
    if en_la_lista:
        r += u8(1)
    r += j.avatar + rangos.insignias(j) + u16(0)
    if en_la_lista:
        r += u8(0)
    return r


def u16_be(v):
    return bytes(((v >> 8) & 0xFF, v & 0xFF))


def _resto_ficha(x):
    j = x.jugador
    return j.avatar + fijo(j.gremio, 8) + rangos.insignias(j)[:4]


# ── lo que pide el cliente ────────────────────────────────────────────────────────────────────────────────

def lista(mundo, s, cuerpo):
    """0x2100: [filtro] 1 = todas, 2 = esperando. El Legacy lee hasta 9 renglones (0x4CB610: `cmp edi, 9`).
    ⚠ El paginado (las flechas) no está medido: se mandan las 9 primeras."""
    filtro = cuerpo[0] if cuerpo else 1
    salas = [x for x in mundo.salas.values() if filtro != 2 or x.estado == ESPERA][:9]
    s.enviar(0x2103, u16(len(salas)) + b"".join(x.entrada_de_lista() for x in salas), rtc=0)


def detalle(mundo, s, cuerpo):
    """0x2104: los datos de una sala y quién está adentro."""
    sid = cuerpo[0] | (cuerpo[1] << 8) if len(cuerpo) >= 2 else -1
    x = mundo.salas.get(sid)
    if x is None:
        return
    r = (con_largo(x.nombre) + u8(x.mapa) + x.ajustes + u8(len(x.jugadores)) + u8(x.cupo) + u8(x.estado)
         + u8(1 if x.clave else 0))
    for o in x.jugadores:
        r += fijo(o.nick, 12) + _resto_ficha(o)
    s.enviar(0x2105, r, rtc=0)


def crear(mundo, s, cuerpo):
    """0x2120: [largo][título] + ajustes (4) + clave (4) + cupo (1)."""
    if s.sala is not None:
        log("SALA", f"{s.nick} pide crear una sala pero el server lo tiene en la sala {s.sala.id}: se ignora")
        return
    if not cuerpo:
        log("SALA", f"{s.nick} pide crear una sala sin datos")
        return
    n = cuerpo[0]
    titulo = cuerpo[1:1 + n].decode("latin-1")
    resto = cuerpo[1 + n:]
    sid = _id_libre(mundo)
    if sid is None or len(resto) < 9:
        motivo = "no quedan números de sala" if sid is None else "pedido corto"
        log("SALA", f"{s.nick} no puede crear la sala: {motivo} · {bytes(cuerpo[:32]).hex()}")
        s.enviar(0x5101, motivo.encode("latin-1"))
        return
    x = Sala(sid, titulo, texto_c(resto[4:8]), resto[0:4], max(1, min(resto[8], 8)), s)
    mundo.salas[sid] = x
    canal.avisar_salida(mundo, s)
    _poner(s, x, casilla=0, equipo=0)
    log("SALA", f"{s.nick} crea la sala {sid} «{titulo}» modo 0x{x.modo:02X} cupo {x.cupo}{' con clave' if x.clave else ''}")
    s.enviar(0x2121, b"\x00\x00\x00" + u16(sid) + mundo.aj.anuncio_sala.encode("latin-1", "replace"))


def entrar(mundo, s, cuerpo):
    """0x2110: [sala WORD][clave]."""
    if s.sala is not None or len(cuerpo) < 2:
        log("SALA", f"{s.nick} pide entrar a una sala y se ignora: "
                    f"{f'el server lo tiene en la sala {s.sala.id}' if s.sala is not None else 'pedido corto'}"
                    f" · {bytes(cuerpo[:16]).hex()}")
        return
    sid = cuerpo[0] | (cuerpo[1] << 8)
    clave = texto_c(cuerpo[2:])
    x = mundo.salas.get(sid)
    motivo = None
    if x is None:
        motivo = "esa sala ya no existe"
    elif x.estado != ESPERA:
        motivo = "la sala está jugando"
    elif len(x.jugadores) >= x.cupo or x.casilla_libre() is None:
        motivo = "la sala está llena"
    elif x.clave and clave != x.clave:
        motivo = "clave equivocada"
    if motivo:
        # ⚠ el código de rechazo del Legacy no está medido: se avisa por el chat del sistema y no se entra
        s.enviar(0x5101, motivo.encode("latin-1"))
        log("SALA", f"{s.nick} no entra a la sala {sid}: {motivo}")
        return
    canal.avisar_salida(mundo, s)
    _poner(s, x, casilla=x.casilla_libre(), equipo=x.equipo_para_el_nuevo())
    log("SALA", f"{s.nick} entra a la sala {sid} (casilla {s.casilla}, equipo {'AB'[s.equipo]})")
    s.enviar(0x21F5, b"\x03", rtc=0)
    r = bytearray(u16(0) + u16(0x0100) + u16(x.id) + con_largo(x.nombre) + u8(x.mapa) + x.ajustes + b"\xFF" * 8
                  + u8(x.cupo) + u8(len(x.jugadores)))
    for o in x.jugadores:
        r += ficha_ocupante(o)
    r += mundo.aj.anuncio_sala.encode("latin-1", "replace")
    s.enviar(0x2111, bytes(r))
    aviso = ficha_ocupante(s, en_la_lista=False)
    for o in x.jugadores:
        if o is not s:
            o.enviar(0x3010, aviso)


def _poner(s, x, casilla, equipo):
    s.sala, s.casilla, s.equipo = x, casilla, equipo
    s.movil1 = s.movil2 = AL_AZAR
    s.listo = False
    x.jugadores.append(s)


def salir(mundo, s, cuerpo):
    """0x3001 (el Legacy manda el canal de destino, WORD) → se lo saca y vuelve al canal con 0x2001."""
    if s.sala is None:
        return
    sacar_de_sala(mundo, s)
    pedido = cuerpo[0] | (cuerpo[1] << 8) if len(cuerpo) >= 2 else 0xFFFF
    canal.entrar(mundo, s, pedido)


def sacar_de_sala(mundo, s, por_desconexion=False):
    x = s.sala
    if x is None:
        return
    casilla = s.casilla
    if x.estado == JUGANDO and s in x.jugadores:
        # Serv3 0x4145BF: el que se va vivo a mitad de partida cuenta como muerto (y eso puede cerrarla)
        from . import partida  # partida importa sala: acá adentro, para no hacer un ciclo
        if casilla not in getattr(x, "caidos", {casilla}):
            partida.caer(mundo, x, casilla, partida.CAUSA_SE_FUE, 0xFF, salvo=s)
    x.jugadores.remove(s)
    s.sala, s.casilla = None, SIN_LUGAR
    if not x.jugadores:
        del mundo.salas[x.id]
        mundo.__dict__.setdefault("salas_cerradas", {})[x.id] = time.monotonic()
        log("SALA", f"la sala {x.id} quedó vacía y se cierra")
        return
    if x.llave is s:
        x.llave = x.jugadores[0]
        log("SALA", f"la llave de la sala {x.id} pasa a {x.llave.nick}")
    pase = (u8(x.llave.casilla) + con_largo(x.nombre) + u8(x.mapa) + x.ajustes + b"\xFF" * 8 + u8(x.cupo))
    for o in x.jugadores:
        o.enviar(0x3020, u16(casilla))
        o.enviar(0x3400, pase)
    log("SALA", f"{s.nick} sale de la sala {x.id}{' (se desconectó)' if por_desconexion else ''}")


def _sala_de_la_llave(s):
    return s.sala if s.sala is not None and s.sala.llave is s else None


def _llave_en_espera(s):
    """La sala del anfitrión sólo si está en ESPERA (no se toca la config durante la partida)."""
    x = _sala_de_la_llave(s)
    return x if x is not None and x.estado == ESPERA else None


def cambiar_mapa(mundo, s, cuerpo):
    x = _llave_en_espera(s)
    if x is not None and cuerpo:
        x.mapa = cuerpo[0]
    s.enviar(0x3105, b"", rtc=0)


def cambiar_ajustes(mundo, s, cuerpo):
    x = _llave_en_espera(s)
    if x is not None and len(cuerpo) >= 4:
        x.ajustes = bytes(cuerpo[:4])
    s.enviar(0x3105, b"", rtc=0)


def cambiar_items(mundo, s, cuerpo):
    s.enviar(0x3105, b"", rtc=0)


def cambiar_cupo(mundo, s, cuerpo):
    x = _llave_en_espera(s)
    if x is not None and cuerpo and len(x.jugadores) <= cuerpo[0] <= 8:
        x.cupo = cuerpo[0]
    s.enviar(0x3105, b"", rtc=0)


def cambiar_titulo(mundo, s, cuerpo):
    x = _llave_en_espera(s)
    if x is not None:
        x.nombre = texto_c(cuerpo)[:40]
    s.enviar(0x3105, b"", rtc=0)


def elegir_equipo(mundo, s, cuerpo):
    if s.sala is not None and cuerpo and cuerpo[0] in (0, 1):
        s.equipo = cuerpo[0]
    s.enviar(0x3211, b"", rtc=0)


_MOVILES_VALIDOS = set(range(16)) | {17, 18, AL_AZAR}   # 0-15 normales + especiales + AL_AZAR (0xFF)


def elegir_movil(mundo, s, cuerpo):
    if s.sala is not None and len(cuerpo) >= 2:
        m1, m2 = cuerpo[0], cuerpo[1]
        if m1 in _MOVILES_VALIDOS and m2 in _MOVILES_VALIDOS:
            s.movil1, s.movil2 = m1, m2
    s.enviar(0x3201, b"", rtc=0)


def listo(mundo, s, cuerpo):
    if s.sala is not None and cuerpo:
        s.listo = bool(cuerpo[0])
    s.enviar(0x3231, b"", rtc=0)


def volver_del_resultado(mundo, s, cuerpo):
    # Solo se acepta cuando la partida ya tiene ganador (pantalla de resultados), no durante el juego.
    x = s.sala
    if x is not None and getattr(x, "ganador", None) is not None:
        x.estado = ESPERA
    s.enviar(0x3233, b"", rtc=0)


ATIENDE = {
    0x2100: lista, 0x2104: detalle, 0x2110: entrar, 0x2120: crear, 0x3001: salir,
    0x3100: cambiar_mapa, 0x3101: cambiar_ajustes, 0x3102: cambiar_items, 0x3103: cambiar_cupo, 0x3104: cambiar_titulo,
    0x3200: elegir_movil, 0x3210: elegir_equipo, 0x3230: listo, 0x3232: volver_del_resultado,
}
