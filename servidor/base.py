# -*- coding: utf-8 -*-
"""base — los jugadores de GunBound, en SQLite (`<GB_ESTADO>/gunbound.db`). Es lo ÚNICO que no se reconstruye.

La identidad es el Eñeños ID (el `sub` del pase): la cuenta es de Cuenta Eñeños, acá sólo vive lo del juego.
⛔ No hay contraseñas acá: el que entra trae un pase.

El AVATAR (lo que el jugador tiene puesto) son 8 bytes: 4 casillas de 2 bytes (cuerpo, cabeza, ojos, bandera).
El bit 0x80 del segundo byte de cada casilla dice el género (0x80 = varón). Sin nada puesto, un varón es
`00 80 00 80 00 80 00 00` y una mujer `00 00 00 00 00 00 00 00`.
Cada pieza del inventario son 4 bytes: código (2) + casilla (2).
"""
import sqlite3
import time
from pathlib import Path

AVATAR_VARON = bytes.fromhex("0080008000800000")
AVATAR_MUJER = bytes(8)
VARON, MUJER = 0, 1          # el byte de género del login (0x1012 +18): 0 = varón

ESQUEMA = """
CREATE TABLE IF NOT EXISTS jugadores (
    enenos_id       INTEGER PRIMARY KEY,
    nick            TEXT NOT NULL UNIQUE COLLATE NOCASE,
    genero          INTEGER NOT NULL DEFAULT 0,
    avatar          BLOB NOT NULL,
    oro             INTEGER NOT NULL DEFAULT 0,
    cash            INTEGER NOT NULL DEFAULT 0,
    gp              INTEGER NOT NULL DEFAULT 0,
    rango           INTEGER NOT NULL DEFAULT 10,
    rango_temporada INTEGER NOT NULL DEFAULT 10,
    gremio          TEXT NOT NULL DEFAULT '',
    baneado         INTEGER NOT NULL DEFAULT 0,
    creado          INTEGER NOT NULL,
    ultimo          INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS inventario (
    serie       INTEGER PRIMARY KEY AUTOINCREMENT,
    enenos_id   INTEGER NOT NULL REFERENCES jugadores(enenos_id),
    pieza       BLOB NOT NULL,
    comprado    INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS inventario_dueno ON inventario(enenos_id);
CREATE TABLE IF NOT EXISTS movimientos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    enenos_id   INTEGER NOT NULL,
    cuando      INTEGER NOT NULL,
    que         TEXT NOT NULL,
    detalle     TEXT NOT NULL DEFAULT ''
);
"""


class Jugador:
    __slots__ = ("enenos_id", "nick", "genero", "avatar", "oro", "cash", "gp", "rango", "rango_temporada",
                 "gremio", "baneado")

    def __init__(self, fila):
        for k in self.__slots__:
            setattr(self, k, fila[k])
        self.avatar = bytes(self.avatar)

    @property
    def byte_genero(self):
        return MUJER if self.genero else VARON


class Base:
    def __init__(self, ruta):
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(self.ruta), isolation_level=None)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA journal_mode=WAL")
        self.con.execute("PRAGMA foreign_keys=ON")
        self.con.executescript(ESQUEMA)

    def cerrar(self):
        self.con.close()

    # ── jugadores ─────────────────────────────────────────────────────────────────────────────────────────
    def jugador(self, enenos_id):
        f = self.con.execute("SELECT * FROM jugadores WHERE enenos_id=?", (int(enenos_id),)).fetchone()
        return Jugador(f) if f else None

    def por_nick(self, nick):
        f = self.con.execute("SELECT * FROM jugadores WHERE nick=?", (nick,)).fetchone()
        return Jugador(f) if f else None

    def crear_si_falta(self, enenos_id, oro, cash):
        """El que entra por primera vez nace con un nick provisorio (GB<id>) y lo cambia con /nombre."""
        j = self.jugador(enenos_id)
        if j:
            return j, False
        ahora = int(time.time())
        nick = f"GB{int(enenos_id)}"[:12]
        self.con.execute("INSERT INTO jugadores (enenos_id, nick, genero, avatar, oro, cash, creado, ultimo) "
                         "VALUES (?,?,?,?,?,?,?,?)", (int(enenos_id), nick, 0, AVATAR_VARON, oro, cash, ahora, ahora))
        self.anotar(enenos_id, "nace", f"oro={oro} cash={cash}")
        return self.jugador(enenos_id), True

    def tocar(self, enenos_id):
        self.con.execute("UPDATE jugadores SET ultimo=? WHERE enenos_id=?", (int(time.time()), int(enenos_id)))

    def poner_nick(self, enenos_id, nick):
        """-> None si quedó, o el motivo."""
        try:
            self.con.execute("UPDATE jugadores SET nick=? WHERE enenos_id=?", (nick, int(enenos_id)))
        except sqlite3.IntegrityError:
            return "ese nombre ya lo tiene otro jugador"
        self.anotar(enenos_id, "nick", nick)
        return None

    def poner_genero(self, enenos_id, genero):
        """Cambiar de género le saca todo lo puesto (las prendas son de un género)."""
        avatar = AVATAR_MUJER if genero else AVATAR_VARON
        self.con.execute("UPDATE jugadores SET genero=?, avatar=? WHERE enenos_id=?", (1 if genero else 0, avatar, int(enenos_id)))
        self.anotar(enenos_id, "genero", "mujer" if genero else "varon")

    def poner_avatar(self, enenos_id, avatar):
        self.con.execute("UPDATE jugadores SET avatar=? WHERE enenos_id=?", (bytes(avatar), int(enenos_id)))

    def sumar(self, enenos_id, oro=0, cash=0, gp=0, motivo=""):
        self.con.execute("UPDATE jugadores SET oro=MAX(0, oro+?), cash=MAX(0, cash+?), gp=MAX(0, gp+?) WHERE enenos_id=?",
                         (int(oro), int(cash), int(gp), int(enenos_id)))
        self.anotar(enenos_id, "saldo", f"oro{oro:+d} cash{cash:+d} gp{gp:+d} {motivo}".strip())

    # ── inventario ────────────────────────────────────────────────────────────────────────────────────────
    def inventario(self, enenos_id):
        """-> [(serie, pieza4)] en el orden de compra."""
        return [(f["serie"], bytes(f["pieza"])) for f in
                self.con.execute("SELECT serie, pieza FROM inventario WHERE enenos_id=? ORDER BY serie", (int(enenos_id),))]

    def comprar(self, enenos_id, pieza, moneda, precio):
        """Descuenta y agrega en UNA transacción. -> serie, o None si no alcanza."""
        col = "cash" if moneda == "cash" else "oro"
        c = self.con
        c.execute("BEGIN IMMEDIATE")
        try:
            saldo = c.execute(f"SELECT {col} FROM jugadores WHERE enenos_id=?", (int(enenos_id),)).fetchone()[0]
            if saldo < precio:
                c.execute("ROLLBACK")
                return None
            c.execute(f"UPDATE jugadores SET {col}={col}-? WHERE enenos_id=?", (int(precio), int(enenos_id)))
            serie = c.execute("INSERT INTO inventario (enenos_id, pieza, comprado) VALUES (?,?,?)",
                              (int(enenos_id), bytes(pieza), int(time.time()))).lastrowid
            c.execute("INSERT INTO movimientos (enenos_id, cuando, que, detalle) VALUES (?,?,?,?)",
                      (int(enenos_id), int(time.time()), "compra", f"{bytes(pieza).hex()} {precio} {col} serie={serie}"))
            c.execute("COMMIT")
            return serie
        except Exception:
            c.execute("ROLLBACK")
            raise

    def anotar(self, enenos_id, que, detalle=""):
        self.con.execute("INSERT INTO movimientos (enenos_id, cuando, que, detalle) VALUES (?,?,?,?)",
                         (int(enenos_id), int(time.time()), que, detalle))
