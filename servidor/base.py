# -*- coding: utf-8 -*-
"""base — los jugadores de GunBound, en SQLite (`<GB_ESTADO>/gunbound.db`). Es lo ÚNICO que no se reconstruye.

La persona es `cuenta` (el Eñeños ID del `sub` del pase). Cada cuenta puede tener varios personajes
(`ajustes.PERSONAJES_POR_CUENTA`, 2 por omisión). Por historia, la columna `enenos_id` de `jugadores` es el **id del
personaje** (es el «usuario» del juego y la clave que usan sesiones, boletos e inventario):
  · personaje 1: `id = cuenta` (así las cuentas anteriores a este cambio no se rompen)
  · personaje 2: `id = DESPLAZAMIENTO_2 + cuenta` (`1_000_000_000 + cuenta`, ver `id_personaje`)
⛔ No hay contraseñas acá: el que entra trae un pase.

El AVATAR (lo que el jugador tiene puesto) son 8 bytes: 4 casillas de 2 bytes (cuerpo, cabeza, ojos, bandera).
El bit 0x80 del segundo byte de cada casilla dice el género (0x80 = varón). Sin nada puesto, un varón es
`00 80 00 80 00 80 00 00` y una mujer `00 00 00 00 00 00 00 00`.
Cada pieza del inventario son 4 bytes: código (2) + casilla (2).
"""
import json
import re
import sqlite3
import time
from pathlib import Path

from .ajustes import DIR_DATOS_JUEGO, PERSONAJES_POR_CUENTA

AVATAR_VARON = bytes.fromhex("0080008000800000")
AVATAR_MUJER = bytes(8)
VARON, MUJER = 0, 1          # el byte de género del login (0x1012 +18): 0 = varón
# los Eñeños ID son menores; el «usuario» del juego entra en 16 dígitos
DESPLAZAMIENTO_2 = 1_000_000_000
RX_NICK = re.compile(r"^[A-Za-z0-9_]{3,12}$")
PAISES = {int(k) for k in json.loads((DIR_DATOS_JUEGO / "paises.json").read_text("utf-8"))["paises"]}


def id_personaje(cuenta, n):
    """El id del personaje `n` (1, 2, …) de esa cuenta."""
    cuenta, n = int(cuenta), int(n)
    if n < 1:
        raise ValueError(f"número de personaje inválido: {n}")
    return cuenta if n == 1 else (n - 1) * DESPLAZAMIENTO_2 + cuenta


ESQUEMA = """
CREATE TABLE IF NOT EXISTS jugadores (
    enenos_id       INTEGER PRIMARY KEY,
    cuenta          INTEGER,
    nick            TEXT NOT NULL UNIQUE COLLATE NOCASE,
    genero          INTEGER NOT NULL DEFAULT 0,
    avatar          BLOB NOT NULL,
    oro             INTEGER NOT NULL DEFAULT 0,
    cash            INTEGER NOT NULL DEFAULT 0,
    gp              INTEGER NOT NULL DEFAULT 0,
    -- rango y rango_temporada ya no se usan (quedan en el esquema por bases viejas; el rango sale de GP/rango_fijo)
    rango           INTEGER NOT NULL DEFAULT 10,
    rango_temporada INTEGER NOT NULL DEFAULT 10,
    pais            INTEGER NOT NULL DEFAULT 0,
    rango_fijo      INTEGER,
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
    detalle     TEXT NOT NULL DEFAULT '',
    quien       TEXT NOT NULL DEFAULT ''      -- quién lo pidió desde afuera («coordinador:<login>»); '' = el juego
);
CREATE INDEX IF NOT EXISTS movimientos_dueno ON movimientos(enenos_id, id);
"""


class Jugador:
    __slots__ = ("enenos_id", "cuenta", "nick", "genero", "avatar", "oro", "cash", "gp", "pais",
                 "rango_fijo", "gremio", "baneado", "es_gm")

    def __init__(self, fila, es_gm=False):
        for k in self.__slots__:
            if k != "es_gm":
                setattr(self, k, fila[k])
        self.avatar = bytes(self.avatar)
        self.es_gm = bool(es_gm)

    @property
    def byte_genero(self):
        return MUJER if self.genero else VARON


class Base:
    def __init__(self, ruta, gm=()):
        self.gm = set(int(x) for x in gm)
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(self.ruta), isolation_level=None)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA journal_mode=WAL")
        self.con.execute("PRAGMA foreign_keys=ON")
        self.con.executescript(ESQUEMA)
        # migración para bases creadas antes de sumar país, rango fijo y cuenta
        cols = {f["name"] for f in self.con.execute("PRAGMA table_info(jugadores)")}
        if "pais" not in cols:
            self.con.execute("ALTER TABLE jugadores ADD COLUMN pais INTEGER NOT NULL DEFAULT 0")
        if "rango_fijo" not in cols:
            self.con.execute("ALTER TABLE jugadores ADD COLUMN rango_fijo INTEGER")
        if "cuenta" not in cols:
            self.con.execute("ALTER TABLE jugadores ADD COLUMN cuenta INTEGER")
            self.con.execute("UPDATE jugadores SET cuenta = enenos_id WHERE cuenta IS NULL")
        self.con.execute("CREATE INDEX IF NOT EXISTS jugadores_cuenta ON jugadores(cuenta)")
        if "quien" not in {f["name"] for f in self.con.execute("PRAGMA table_info(movimientos)")}:
            self.con.execute("ALTER TABLE movimientos ADD COLUMN quien TEXT NOT NULL DEFAULT ''")

    def cerrar(self):
        self.con.close()

    # ── jugadores ─────────────────────────────────────────────────────────────────────────────────────────
    def _armar(self, fila):
        if not fila:
            return None
        cuenta = fila["cuenta"] if fila["cuenta"] is not None else fila["enenos_id"]
        return Jugador(fila, es_gm=cuenta in self.gm)

    def jugador(self, enenos_id):
        f = self.con.execute("SELECT * FROM jugadores WHERE enenos_id=?", (int(enenos_id),)).fetchone()
        return self._armar(f)

    def por_nick(self, nick):
        f = self.con.execute("SELECT * FROM jugadores WHERE nick=?", (nick,)).fetchone()
        return self._armar(f)

    def personajes(self, cuenta):
        """Los personajes de esa cuenta (persona), ordenados por id."""
        filas = self.con.execute("SELECT * FROM jugadores WHERE cuenta=? ORDER BY enenos_id", (int(cuenta),)).fetchall()
        return [self._armar(f) for f in filas]

    def crear_personaje(self, cuenta, nick, mujer: bool, pais: int, oro, cash, maximo=PERSONAJES_POR_CUENTA):
        """Crea un personaje para `cuenta` en el primer número libre. -> (Jugador | None, motivo | None)."""
        if not isinstance(nick, str) or not RX_NICK.match(nick):
            return None, "nick inválido (3 a 12: letras, números o _)"
        if isinstance(pais, bool):
            return None, "país inválido"
        try:
            pais = int(pais)
        except (TypeError, ValueError):
            return None, "país inválido"
        if pais != 0 and pais not in PAISES:
            return None, "país inválido"
        cuenta = int(cuenta)
        actuales = self.personajes(cuenta)
        if len(actuales) >= maximo:
            return None, f"ya tiene el máximo de {maximo} personajes"
        if self.por_nick(nick) is not None:
            return None, "ese nick ya está ocupado"
        usados = {j.enenos_id for j in actuales}
        pid = next(id_personaje(cuenta, n) for n in range(1, maximo + 1) if id_personaje(cuenta, n) not in usados)
        genero = MUJER if mujer else VARON
        avatar = AVATAR_MUJER if mujer else AVATAR_VARON
        ahora = int(time.time())
        try:
            self.con.execute(
                "INSERT INTO jugadores (enenos_id, cuenta, nick, genero, avatar, pais, oro, cash, creado, ultimo) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (pid, cuenta, nick, genero, avatar, pais, int(oro), int(cash), ahora, ahora),
            )
        except sqlite3.IntegrityError:
            return None, "ese nick ya está ocupado"
        self.anotar(pid, "nace", f"cuenta={cuenta} pais={pais} oro={int(oro)} cash={int(cash)}")
        return self.jugador(pid), None

    def crear_si_falta(self, enenos_id, oro, cash):
        """Para el canje viejo con `{"pase"}` (sin ficha): crea el personaje 1 si la cuenta no tiene ninguno."""
        cuenta = int(enenos_id)
        actuales = self.personajes(cuenta)
        if actuales:
            return actuales[0], False
        pid = id_personaje(cuenta, 1)
        ahora = int(time.time())
        nick = f"GB{cuenta}"[:12]
        self.con.execute(
            "INSERT INTO jugadores (enenos_id, cuenta, nick, genero, avatar, oro, cash, creado, ultimo) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (pid, cuenta, nick, VARON, AVATAR_VARON, oro, cash, ahora, ahora),
        )
        self.anotar(pid, "nace", f"cuenta={cuenta} oro={oro} cash={cash}")
        return self.jugador(pid), True

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

    def sumar(self, enenos_id, oro=0, cash=0, gp=0, motivo="", quien=""):
        """Suma (o resta) entre 0 y el tope de un DWORD (el cliente los lee como u32): lo que no alcanza queda en 0."""
        self.con.execute("UPDATE jugadores SET oro=MIN(4294967295, MAX(0, oro+?)), cash=MIN(4294967295, MAX(0, cash+?)), "
                         "gp=MIN(4294967295, MAX(0, gp+?)) WHERE enenos_id=?",
                         (int(oro), int(cash), int(gp), int(enenos_id)))
        self.anotar(enenos_id, "saldo", f"oro{oro:+d} cash{cash:+d} gp{gp:+d} {motivo}".strip(), quien=quien)

    def poner_gp(self, enenos_id, gp):
        gp = max(0, int(gp))
        self.con.execute("UPDATE jugadores SET gp=? WHERE enenos_id=?", (gp, int(enenos_id)))
        self.anotar(enenos_id, "gp", str(gp))

    def poner_pais(self, enenos_id, pais):
        pais = int(pais)
        self.con.execute("UPDATE jugadores SET pais=? WHERE enenos_id=?", (pais, int(enenos_id)))
        self.anotar(enenos_id, "pais", str(pais))

    def poner_rango_fijo(self, enenos_id, rango):
        val = None if rango is None else int(rango)
        self.con.execute("UPDATE jugadores SET rango_fijo=? WHERE enenos_id=?", (val, int(enenos_id)))
        self.anotar(enenos_id, "rango_fijo", "auto" if val is None else str(val))

    def puestos(self, enenos_id):
        """-> (puesto_total, puesto_en_su_pais); 1 = el de más GP. El de país es 0 si `pais` es 0."""
        f = self.con.execute("SELECT gp, pais FROM jugadores WHERE enenos_id=?", (int(enenos_id),)).fetchone()
        if f is None:
            return 0, 0
        total = self.con.execute("SELECT COUNT(*) + 1 FROM jugadores WHERE gp > ?", (f["gp"],)).fetchone()[0]
        if f["pais"] == 0:
            return total, 0
        en_pais = self.con.execute("SELECT COUNT(*) + 1 FROM jugadores WHERE pais = ? AND gp > ?",
                                   (f["pais"], f["gp"])).fetchone()[0]
        return total, en_pais

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

    def anotar(self, enenos_id, que, detalle="", quien=""):
        self.con.execute("INSERT INTO movimientos (enenos_id, cuando, que, detalle, quien) VALUES (?,?,?,?,?)",
                         (int(enenos_id), int(time.time()), que, detalle, quien or ""))

    def movimientos(self, enenos_id, n=20):
        """Los últimos `n` del personaje, del más nuevo al más viejo: [{cuando, que, detalle, quien}]."""
        return [dict(f) for f in self.con.execute(
            "SELECT cuando, que, detalle, quien FROM movimientos WHERE enenos_id=? ORDER BY id DESC LIMIT ?",
            (int(enenos_id), int(n)))]

    # ── para el panel del Coordinador (servidor/panel.py) ─────────────────────────────────────────────────
    def fechas(self, enenos_id):
        """-> (creado, ultimo) en epoch, o None."""
        f = self.con.execute("SELECT creado, ultimo FROM jugadores WHERE enenos_id=?", (int(enenos_id),)).fetchone()
        return (f["creado"], f["ultimo"]) if f else None

    def contar(self):
        return self.con.execute("SELECT COUNT(*) FROM jugadores").fetchone()[0]

    def buscar(self, q, tope=50):
        """Por apodo (una parte, sin importar mayúsculas), por id del personaje o por Eñeños ID (la cuenta: trae
        todos sus personajes). Los que calzan por número van primero. -> [Jugador] (como mucho `tope`)."""
        q = (q or "").strip()[:64]
        if not q:
            return []
        filas = []
        if q.isascii() and q.isdigit() and len(q) <= 18:     # más largo no entra en un INTEGER de SQLite
            n = int(q)
            filas += self.con.execute("SELECT * FROM jugadores WHERE enenos_id=? OR cuenta=? ORDER BY enenos_id",
                                      (n, n)).fetchall()
        # «!» escapa los comodines de LIKE: un «_» en el apodo (muy común) es una letra, no «cualquiera»
        patron = "%" + q.replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%"
        filas += self.con.execute("SELECT * FROM jugadores WHERE nick LIKE ? ESCAPE '!' ORDER BY ultimo DESC LIMIT ?",
                                  (patron, int(tope))).fetchall()
        vistos, salida = set(), []
        for f in filas:
            if f["enenos_id"] not in vistos:
                vistos.add(f["enenos_id"])
                salida.append(self._armar(f))
        return salida[:tope]
