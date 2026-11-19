# -*- coding: utf-8 -*-
"""mundo — el server de juego: las conexiones TCP de los jugadores y el reparto de cada mensaje a quien lo atiende.

Todo corre en UN hilo (asyncio): no hay candados porque nunca hay dos cosas a la vez. Lo que tarda (la base) es
SQLite local y tarda microsegundos.

Quién atiende qué (ver servidor/MAPA.md):
    entrada.py   0x1000 ficha · 0x1010 login · 0x1020 buscar a alguien
    canal.py     0x2000/0x2001 entrar al canal · 0x2010 chat
    sala.py      0x21xx lista, crear, entrar · 0x3001 salir · 0x31xx/0x32xx opciones de la sala
    partida.py   0x3430 empezar · 0x4xxx durante la partida · 0x4500 túnel
    tienda.py    0x1090 ajustes del mundo · 0x60xx inventario, compra, ponerse ropa · 0x61xx saldos
    comandos.py  0x5100 los /comandos del chat
"""
import asyncio
import json
import socket

from . import canal, comandos, entrada, partida, sala, tienda
from .paquete import Cortador
from .registro import log
from .sala import JUGANDO
from .sesion import Sesion

SILENCIO_MAXIMO = 600                    # fuera de partida: 10 min sin nada por TCP y se corta


def _keepalive(sock):
    """El keepalive TCP del sistema: a una PC que se apagó o perdió la red la descubre en ~2 min aunque el
    juego no mande nada (jugando por P2P directo). En Linux se afinan los tiempos; en otros, lo que haya."""
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        for nombre, valor in (("TCP_KEEPIDLE", 60), ("TCP_KEEPINTVL", 15), ("TCP_KEEPCNT", 4)):
            if hasattr(socket, nombre):
                sock.setsockopt(socket.IPPROTO_TCP, getattr(socket, nombre), valor)
    except OSError:
        pass


class Mundo:
    def __init__(self, ajustes, base, boletos):
        self.aj = ajustes
        self.base = base
        self.boletos = boletos
        self.sesiones = []                   # las conexiones con login hecho
        self.salas = {}                      # id -> Sala
        self.mapas = {m["map_id"]: m for m in json.loads((ajustes_dir(ajustes) / "mapas.json").read_text("utf-8"))}
        self.precios = json.loads((ajustes_dir(ajustes) / "precios_avatar.json").read_text("utf-8"))["prices"]
        self.paises = {int(k): v for k, v in json.loads((ajustes_dir(ajustes) / "paises.json").read_text("utf-8"))["paises"].items()}
        self.prob_dragon = ajustes.prob_especiales   # % de que el «al azar» salga Dragón o Caballero
        self.atiende = {}
        for modulo in (entrada, canal, sala, partida, tienda, comandos):
            self.atiende.update(modulo.ATIENDE)
        self._servidor = None
        self._udp = None

    # ── arrancar ──────────────────────────────────────────────────────────────────────────────────────────
    async def arrancar(self):
        self._servidor = await asyncio.start_server(self._conexion, self.aj.escucha, self.aj.puerto_mundo,
                                                    reuse_address=True)
        lazo = asyncio.get_running_loop()
        self._udp, _ = await lazo.create_datagram_endpoint(lambda: _EcoUDP(), local_addr=(self.aj.escucha, self.aj.puerto_mundo),
                                                           reuse_port=False)
        log("MUNDO", f"escuchando TCP+UDP {self.aj.escucha}:{self.aj.puerto_mundo}")

    def cerrar(self):
        if self._servidor:
            self._servidor.close()
        if self._udp:
            self._udp.close()
        for s in list(self.sesiones):
            s.cerrar()

    @property
    def puerto(self):
        return self._servidor.sockets[0].getsockname()[1] if self._servidor else self.aj.puerto_mundo

    # ── una conexión ──────────────────────────────────────────────────────────────────────────────────────
    async def _conexion(self, lector, escritor):
        if len(self.sesiones) >= self.aj.max_conexiones:
            escritor.close()
            return
        sock = escritor.get_extra_info("socket")
        if sock is not None:
            try:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except OSError:
                pass
            _keepalive(sock)
        s = Sesion(escritor, escritor.get_extra_info("peername"), traza=self.aj.traza)
        s.p2p_directo = self.aj.p2p == "directo"
        cortador = Cortador()
        try:
            while not s.cerrada:
                try:
                    pedazo = await asyncio.wait_for(lector.read(4096), timeout=SILENCIO_MAXIMO)
                except asyncio.TimeoutError:
                    # ⚠ Jugando con P2P directo el cliente NO manda nada por TCP (no tiene keepalive propio:
                    # sólo se entera de un corte por FD_CLOSE). Cortar acá echaría de una partida larga a todos.
                    # A ése lo vigila el keepalive TCP del sistema (_keepalive), no este plazo.
                    if s.sala is not None and s.sala.estado == JUGANDO:
                        continue
                    log("MUNDO", f"{s}: 10 minutos sin nada, se corta")
                    break
                if not pedazo:
                    break
                for crudo in cortador.meter(pedazo):
                    self.atender(s, crudo)
                await escritor.drain()
        except (ConnectionError, ValueError) as e:
            log("MUNDO", f"{s}: conexión cortada ({e})")
        finally:
            self.desconectar(s)

    def atender(self, s, crudo):
        comando = crudo[4] | (crudo[5] << 8)
        cuerpo = crudo[6:]
        if self.aj.traza:
            log("TRAZA", f"{s.nick} → 0x{comando:04X} ({len(cuerpo)}) {bytes(cuerpo[:64]).hex()}")
        f = self.atiende.get(comando)
        if f is None:
            log("MUNDO", f"{s}: comando sin atender 0x{comando:04X} ({len(cuerpo)} bytes) {cuerpo[:48].hex()}")
            return
        if s.jugador is None and comando not in entrada.ANTES_DEL_LOGIN:
            log("MUNDO", f"{s}: 0x{comando:04X} antes del login, se ignora")
            return
        try:
            f(self, s, cuerpo)
        except Exception as e:                                          # noqa: BLE001
            # ⛔ un mensaje raro de UN jugador no tira al resto: se anota y se sigue
            log("MUNDO", f"{s}: ⚠ error atendiendo 0x{comando:04X}: {type(e).__name__}: {e} · {cuerpo[:48].hex()}")

    def desconectar(self, s):
        if s in self.sesiones:
            sala.sacar_de_sala(self, s, por_desconexion=True)
            canal.avisar_salida(self, s)
            self.sesiones.remove(s)
            log("MUNDO", f"{s} se fue ({len(self.sesiones)} en línea)")
        s.cerrar()

    # ── búsquedas ─────────────────────────────────────────────────────────────────────────────────────────
    def sesion_de(self, enenos_id):
        for s in self.sesiones:
            if s.enenos_id == enenos_id:
                return s
        return None

    def sesiones_de_cuenta(self, cuenta):
        """Las sesiones de cualquier personaje de esa persona (Eñeños ID)."""
        return [s for s in self.sesiones if s.jugador is not None and s.jugador.cuenta == cuenta]

    def sesion_por_nick(self, nick):
        nick = nick.lower()
        for s in self.sesiones:
            if s.nick.lower() == nick:
                return s
        return None

    def en_canal(self):
        """Los que están en el canal (no en una sala)."""
        return [s for s in self.sesiones if s.sala is None and s.lugar_canal >= 0]

    def es_gm(self, s):
        return bool(s.jugador and (s.jugador.es_gm or s.jugador.cuenta in self.aj.gm))


def ajustes_dir(aj):
    from .ajustes import DIR_DATOS_JUEGO
    return DIR_DATOS_JUEGO


class _EcoUDP(asyncio.DatagramProtocol):
    """El cliente le manda UDP al puerto del mundo para saber cómo lo ve el server (su IP y puerto de afuera).
    El server le devuelve lo mismo, como hacía el original."""

    def connection_made(self, transporte):
        self.t = transporte

    def datagram_received(self, datos, origen):
        try:
            self.t.sendto(datos, origen)
        except OSError:
            pass
