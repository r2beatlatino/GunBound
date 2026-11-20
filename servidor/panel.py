# -*- coding: utf-8 -*-
"""panel — la puerta INTERNA para el panel del Coordinador Eñeños («contrato del panel v1»).

El contrato vive en el repo del Coordinador (`documentacion/CONTRATO_PANEL.md`). En corto: el Coordinador decide
QUIÉN puede qué; el juego sólo EJECUTA y ANOTA quién lo pidió. Vive en el mismo HTTP que el canje (`web.py`),
bajo `/interno/panel/…`, SIN el prefijo `/gunbound` (así lo que entra por Caddy, que siempre lo trae, no llega acá).

    GET  capacidades                      {"juego", "version": 1, "acciones", "monedas", "entorno"}
    GET  salud                            {"en_linea", "jugando", "detalle": [{"nombre", "valor"}]}
    GET  conectados                       {"filas": [{"id", "nick", "enenos_id", "donde", "desde", "ip"}]}
    GET  buscar?q=                        {"filas": [{"id", "nick", "enenos_id", "conectado", "resumen"}]}  (tope 50)
    GET  ficha/<id>                       {"id", "nick", "enenos_id", "conectado", "baneado", "campos", "monedas",
                                           "personajes", "movimientos"}
    POST aviso   {texto, a: todos|uno, id?}   {"ok", "llego_a"}          (lo mismo que /aviso del chat)
    POST echar   {id, motivo?}                {"ok"} · 404 si no está    (lo mismo que cuando entra otra vez)
    POST moneda  {id, moneda, cantidad}       {"ok", "antes", "despues"} (lo mismo que /dar; nunca deja negativo)

`id` = el id del PERSONAJE (el «usuario» del juego; ver base.py). `enenos_id` = la CUENTA (el Eñeños ID).

SEGURIDAD
- Toda ruta pide `X-Ficha-Interna` == `R2_CUENTAS_FICHA_INTERNA` (tiempo constante). Sin la variable, con otra
  ficha o sin ella: 404, como si no existiera.
- Si el pedido trae `X-Forwarded-For` vino por un proxy (Caddy lo pone siempre) ⇒ 404: el Coordinador llama por la
  red de adentro, directo. Es la segunda llave, por si un día una regla de Caddy deja pasar `/interno`.
- Todo POST pide además `X-R2: 1` (403). Cada cambio se anota con `X-Coordinador-Quien`: en el log y, si es de un
  jugador, en su `movimientos` (columna `quien`).
- Nunca sale una contraseña, un boleto ni una ficha (el juego no guarda contraseñas: entra con el pase).
"""
import hmac
import json
import time
import urllib.parse

from . import comandos, rangos
from .base import DESPLAZAMIENTO_2
from .registro import log
from .sala import JUGANDO

PREFIJO = "/interno/panel"
VERSION = 1
ACCIONES = ["ver", "aviso", "echar", "moneda"]
# las dos monedas del juego: las columnas `oro` y `cash` de `jugadores` (las mismas de la tienda y de /dar)
MONEDAS = [{"id": "oro", "nombre": "Oro"}, {"id": "cash", "nombre": "Cash"}]
TOPE_BUSCAR = 50
TOPE_MOVIMIENTOS = 20
TOPE_AVISO = 200                   # letras: el chat del cliente es corto
TOPE_MOTIVO = 200
TOPE_CANTIDAD = 1_000_000_000      # por pedido, para un lado o el otro
TOPE_QUIEN = 80

NO_EXISTE = (404, {"error": "No existe."})


def es_suya(ruta):
    """¿La ruta (sin la consulta) es de esta puerta? Se mira ANTES de sacar el prefijo /gunbound."""
    return ruta == PREFIJO or ruta.startswith(PREFIJO + "/")


def _cab(cabeceras, nombre):
    for k, v in (cabeceras or {}).items():
        if k.lower() == nombre:
            return v
    return None


def _entero(v):
    """Un número entero de JSON (no bool) o un texto de dígitos. -> int o None."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.strip().isascii() and v.strip().lstrip("-").isdigit() and len(v.strip()) <= 19:
        return int(v.strip())
    return None


def _texto_limpio(v, tope):
    """Sin saltos de línea ni caracteres de control (van al chat del cliente). -> str (puede quedar vacío)."""
    if not isinstance(v, str):
        return None
    return " ".join("".join(c if c.isprintable() else " " for c in v).split())[:tope + 1]


def _fecha(t):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(t)) if t else "—"


def _duracion(s):
    s = int(s)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m = s // 60
    return (f"{d} d " if d else "") + f"{h} h {m} min"


class Panel:
    def __init__(self, ajustes, base, mundo):
        self.aj = ajustes
        self.base = base
        self.mundo = mundo
        self.inicio = time.time()

    # ── la puerta ─────────────────────────────────────────────────────────────────────────────────────────
    def atender(self, metodo, ruta, cuerpo, cabeceras):
        ficha = self.aj.ficha_interna or ""
        dada = _cab(cabeceras, "x-ficha-interna")
        if not ficha or not isinstance(dada, str) or not hmac.compare_digest(dada.encode("utf-8"), ficha.encode("utf-8")):
            return NO_EXISTE
        if _cab(cabeceras, "x-forwarded-for") is not None:
            log("PANEL", f"⚠ pedido con la ficha buena pero por un proxy (X-Forwarded-For): {metodo} {ruta[:80]} — 404")
            return NO_EXISTE
        if metodo == "POST" and _cab(cabeceras, "x-r2") != "1":
            return 403, {"error": "Falta la cabecera X-R2."}
        camino, _, consulta = ruta.partition("?")
        sub = camino[len(PREFIJO):].strip("/")

        if metodo == "GET":
            if sub == "capacidades":
                return 200, self.capacidades()
            if sub == "salud":
                return 200, self.salud()
            if sub == "conectados":
                return 200, {"filas": [self._fila_conectado(s) for s in list(self.mundo.sesiones)]}
            if sub == "buscar":
                q = (urllib.parse.parse_qs(consulta).get("q") or [""])[0]
                if not q.strip():
                    return 400, {"error": "Escriba un apodo, un id de personaje o un Eñeños ID."}
                return 200, {"filas": [self._fila_busqueda(j) for j in self.base.buscar(q, TOPE_BUSCAR)]}
            if sub.startswith("ficha/"):
                pid = _entero(sub[len("ficha/"):])
                j = self.base.jugador(pid) if pid is not None and 0 < pid < 2 ** 62 else None
                if j is None:
                    return 404, {"error": "No existe ese jugador."}
                return 200, self.ficha(j)
            return NO_EXISTE

        if metodo == "POST" and sub in ("aviso", "echar", "moneda"):
            try:
                datos = json.loads((cuerpo or b"").decode("utf-8") or "{}")
            except (ValueError, UnicodeDecodeError):
                datos = None
            if not isinstance(datos, dict):
                return 400, {"error": "El cuerpo del pedido no es un JSON válido."}
            quien = _texto_limpio(_cab(cabeceras, "x-coordinador-quien") or "", TOPE_QUIEN)[:TOPE_QUIEN] \
                or "coordinador:(sin nombre)"
            return getattr(self, sub)(datos, quien)
        return NO_EXISTE

    # ── ver ───────────────────────────────────────────────────────────────────────────────────────────────
    def capacidades(self):
        return {"juego": "gunbound", "version": VERSION, "acciones": list(ACCIONES), "monedas": [dict(m) for m in MONEDAS],
                "entorno": self.aj.entorno}

    def salud(self):
        salas = list(self.mundo.salas.values())
        en_partida = sum(len(x.jugadores) for x in salas if x.estado == JUGANDO)
        return {
            "en_linea": True,
            "jugando": len(self.mundo.sesiones),
            "detalle": [
                {"nombre": "Entorno", "valor": self.aj.entorno},
                {"nombre": "Conectados", "valor": len(self.mundo.sesiones)},
                {"nombre": "En partida", "valor": en_partida},
                {"nombre": "Salas abiertas", "valor": len(salas)},
                {"nombre": "Partidas en curso", "valor": sum(1 for x in salas if x.estado == JUGANDO)},
                {"nombre": "Personajes registrados", "valor": self.base.contar()},
                {"nombre": "Cupo del mundo", "valor": self.aj.capacidad_mundo},
                {"nombre": "Encendido hace", "valor": _duracion(time.time() - self.inicio)},
            ],
        }

    def _donde(self, s):
        x = s.sala
        if x is None:
            return "Lobby"
        return f"Sala {x.id} «{x.nombre}» ({'en partida' if x.estado == JUGANDO else 'esperando'})"

    def _fila_conectado(self, s):
        return {"id": s.enenos_id, "nick": s.nick, "enenos_id": s.jugador.cuenta if s.jugador else None,
                "donde": self._donde(s), "desde": s.desde, "ip": s.ip}

    @staticmethod
    def _numero(j):
        return (j.enenos_id - j.cuenta) // DESPLAZAMIENTO_2 + 1 if j.cuenta is not None else 1

    def _rango_txt(self, j):
        r = rangos.rango_de(j)
        return rangos.NOMBRES.get(r, str(r)) + (" (fijo)" if j.rango_fijo is not None else "")

    def _fila_busqueda(self, j):
        resumen = f"{self._rango_txt(j)} · {j.gp} GP · personaje n.º {self._numero(j)}"
        if j.baneado:
            resumen += " · suspendido"
        return {"id": j.enenos_id, "nick": j.nick, "enenos_id": j.cuenta,
                "conectado": self.mundo.sesion_de(j.enenos_id) is not None, "resumen": resumen}

    def ficha(self, j):
        s = self.mundo.sesion_de(j.enenos_id)
        creado, ultimo = self.base.fechas(j.enenos_id) or (0, 0)
        puesto, puesto_pais = self.base.puestos(j.enenos_id)
        campos = [
            {"nombre": "Personaje", "valor": f"n.º {self._numero(j)} de la cuenta"},
            {"nombre": "Rango", "valor": self._rango_txt(j)},
            {"nombre": "GP", "valor": j.gp},
            {"nombre": "Puesto general", "valor": puesto},
            {"nombre": "Puesto en su país", "valor": puesto_pais or "—"},
            {"nombre": "País", "valor": self.mundo.paises.get(j.pais) or "Sin país"},
            {"nombre": "Género", "valor": "Mujer" if j.genero else "Varón"},
            {"nombre": "Gremio", "valor": j.gremio or "—"},
            {"nombre": "GM", "valor": "Sí" if (j.es_gm or j.cuenta in self.aj.gm) else "No"},
            {"nombre": "Prendas en el inventario", "valor": len(self.base.inventario(j.enenos_id))},
            {"nombre": "Alta", "valor": _fecha(creado)},
            {"nombre": "Última entrada al mundo", "valor": _fecha(ultimo)},
            {"nombre": "Ahora", "valor": self._donde(s) if s else "Desconectado"},
        ]
        movs = [{"cuando": m["cuando"], "que": m["que"] + (f": {m['detalle']}" if m["detalle"] else ""),
                 "quien": m["quien"] or None}
                for m in self.base.movimientos(j.enenos_id, TOPE_MOVIMIENTOS)]
        return {
            "id": j.enenos_id, "nick": j.nick, "enenos_id": j.cuenta, "conectado": s is not None,
            "baneado": bool(j.baneado), "campos": campos, "monedas": {"oro": j.oro, "cash": j.cash},
            "personajes": [{"id": p.enenos_id, "nick": p.nick} for p in self.base.personajes(j.cuenta)],
            "movimientos": movs,
        }

    # ── cambiar (cada uno se anota con quién lo pidió) ────────────────────────────────────────────────────
    def aviso(self, d, quien):
        texto = _texto_limpio(d.get("texto"), TOPE_AVISO)
        if not texto:
            return 400, {"error": "Escriba el texto del aviso."}
        if len(texto) > TOPE_AVISO:
            return 400, {"error": f"El aviso es demasiado largo (máximo {TOPE_AVISO} letras)."}
        a = d.get("a")
        if a == "todos":
            n = comandos.avisar(self.mundo, texto)
            log("PANEL", f"{quien}: aviso a todos ({n}): {texto}")
            return 200, {"ok": True, "llego_a": n}
        if a == "uno":
            pid = _entero(d.get("id"))
            s = self.mundo.sesion_de(pid) if pid is not None else None
            if s is None:
                return 404, {"error": "Ese jugador no está conectado."}
            n = comandos.avisar(self.mundo, texto, s)
            self.base.anotar(s.enenos_id, "aviso", texto, quien=quien)
            log("PANEL", f"{quien}: aviso a {s}: {texto}")
            return 200, {"ok": True, "llego_a": n}
        return 400, {"error": "Indique a quién: «todos» o «uno» (con su id)."}

    def echar(self, d, quien):
        pid = _entero(d.get("id"))
        if pid is None:
            return 400, {"error": "Falta el id del jugador."}
        motivo = _texto_limpio(d.get("motivo") or "", TOPE_MOTIVO)
        if motivo is None:
            return 400, {"error": "El motivo tiene que ser un texto."}
        motivo = motivo[:TOPE_MOTIVO]
        s = self.mundo.sesion_de(pid)
        if s is None:
            return 404, {"error": "Ese jugador no está conectado."}
        comandos.avisar(self.mundo, "Un moderador te desconecto." + (f" Motivo: {motivo}" if motivo else ""), s)
        # lo mismo que hace el mundo cuando la misma cuenta entra otra vez (entrada.login): lo saca de la sala
        # (avisando a los demás), del canal y de la lista, y cierra la conexión
        self.mundo.desconectar(s)
        self.base.anotar(pid, "echado", motivo, quien=quien)
        log("PANEL", f"{quien}: echó a {s}" + (f" · motivo: {motivo}" if motivo else ""))
        return 200, {"ok": True}

    def moneda(self, d, quien):
        pid, cantidad, moneda = _entero(d.get("id")), _entero(d.get("cantidad")), d.get("moneda")
        if moneda not in {m["id"] for m in MONEDAS}:
            return 400, {"error": "Esa moneda no existe en GunBound (oro o cash)."}
        if cantidad is None or cantidad == 0 or abs(cantidad) > TOPE_CANTIDAD:
            return 400, {"error": f"La cantidad tiene que ser un número entero distinto de 0 (como mucho "
                                  f"{TOPE_CANTIDAD:,} por vez).".replace(",", ".")}
        j = self.base.jugador(pid) if pid is not None and 0 < pid < 2 ** 62 else None
        if j is None:
            return 404, {"error": "No existe ese jugador."}
        antes = getattr(j, moneda)
        # la misma suma que /dar (base.sumar: MAX(0, …), nunca deja negativo), anotada con quién la pidió
        self.base.sumar(pid, motivo="panel", quien=quien, **{moneda: cantidad})
        j2 = self.base.jugador(pid)
        despues = getattr(j2, moneda)
        s = self.mundo.sesion_de(pid)
        if s is not None:
            s.jugador = j2            # como tienda._fresco: lo que el server lea de la sesión ya es lo nuevo
        log("PANEL", f"{quien}: {moneda} {cantidad:+d} a {j2.nick} #{pid} ({antes} → {despues})")
        return 200, {"ok": True, "antes": antes, "despues": despues}
