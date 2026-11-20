# -*- coding: utf-8 -*-
"""probar_panel — la puerta interna del panel del Coordinador (`/interno/panel/…`, servidor/panel.py), contrato v1.

Cada regla con su control al revés: sin ficha / con otra / sin la variable → 404 · por un proxy o con el prefijo
de Caddy → 404 · POST sin X-R2 → 403 · moneda suma y anota QUIÉN · restar nunca deja negativo · buscar por apodo,
id y Eñeños ID · lo no implementado → 404 · `capacidades` = exactamente lo que responde.
"""
import json
import secrets
import sqlite3
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from arnes import Banco, ServerDePrueba
from robot import Robot, canjear
from servidor import panel as P
from servidor.base import DESPLAZAMIENTO_2, Base

b = Banco("probar_panel")
FICHA = "ficha-del-banco-" + secrets.token_hex(12)
QUIEN = "coordinador:banco"
CUENTA_A, CUENTA_B = 90000041, 90000042


def pedir(srv, metodo, ruta, datos=None, ficha=FICHA, x_r2=True, quien=QUIEN, extra=None):
    h = {}
    if ficha is not None:
        h["X-Ficha-Interna"] = ficha
    if quien:
        h["X-Coordinador-Quien"] = quien
    cuerpo = None
    if metodo == "POST":
        h["Content-Type"] = "application/json"
        if x_r2:
            h["X-R2"] = "1"
        cuerpo = json.dumps(datos if datos is not None else {}).encode("utf-8")
    h.update(extra or {})
    req = urllib.request.Request(f"http://127.0.0.1:{srv.srv.web.puerto}{ruta}", data=cuerpo, method=metodo, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def ruta(sub):
    return P.PREFIJO + "/" + sub


def en_base(srv, f):
    return srv.en_el_lazo(lambda: f(srv.srv.base))


def entrar(srv, cuenta):
    st, c = canjear(srv.url_canje, srv.pase(cuenta))
    r = Robot(*srv.mundo)
    r.login(c["usuario"], c["ticket"])
    return r


def textos_del_sistema(r, plazo=1.0):
    return [bytes(x).split(b"\0")[0].decode("latin-1") for x in r.todos(0x5101, plazo)]


# ═══ una base de antes (movimientos sin «quien») se migra sola y no pierde nada ═══════════════════════════════════
vieja = Path(tempfile.mkdtemp(prefix="gb_vieja_")) / "gunbound.db"
c = sqlite3.connect(str(vieja))
c.execute("CREATE TABLE movimientos (id INTEGER PRIMARY KEY AUTOINCREMENT, enenos_id INTEGER NOT NULL, "
          "cuando INTEGER NOT NULL, que TEXT NOT NULL, detalle TEXT NOT NULL DEFAULT '')")
c.execute("INSERT INTO movimientos (enenos_id, cuando, que, detalle) VALUES (7, 1, 'compra', 'vieja')")
c.commit()
b.ver("quien" not in {f[1] for f in c.execute("PRAGMA table_info(movimientos)")}, "control: la base vieja no tiene «quien»")
c.close()
bv = Base(vieja)
b.igual(bv.movimientos(7), [{"cuando": 1, "que": "compra", "detalle": "vieja", "quien": ""}],
        "base vieja: se suma la columna «quien» y el movimiento de antes sigue")
bv.cerrar()

# ═══ sin la variable R2_CUENTAS_FICHA_INTERNA la puerta no existe ════════════════════════════════════════════════
with ServerDePrueba(ficha_interna="") as srv0:
    b.igual(pedir(srv0, "GET", ruta("capacidades"))[0], 404, "sin la variable: con una ficha cualquiera → 404")
    b.igual(pedir(srv0, "GET", ruta("capacidades"), ficha="")[0], 404, "sin la variable: con la ficha vacía → 404")
    b.igual(pedir(srv0, "GET", "/salud", ficha=None)[0], 200, "control: el resto del HTTP sigue andando (/salud)")

with ServerDePrueba(ficha_interna=FICHA) as srv:
    # personajes: A tiene dos (uno con «_» en el apodo), B uno; «Ana9x» es la trampa del comodín «_» de LIKE
    en_base(srv, lambda B: B.crear_personaje(CUENTA_A, "Lucia_x", True, 9, 100_000, 20_000))
    en_base(srv, lambda B: B.crear_personaje(CUENTA_A, "Lucia_2", True, 157, 100_000, 20_000))
    en_base(srv, lambda B: B.crear_personaje(CUENTA_B, "Ana9x", True, 0, 100_000, 20_000))
    ID_A1, ID_A2, ID_B = CUENTA_A, DESPLAZAMIENTO_2 + CUENTA_A, CUENTA_B

    # ── la ficha ───────────────────────────────────────────────────────────────────────────────────────────────
    st, cap = pedir(srv, "GET", ruta("capacidades"))
    b.igual(st, 200, "con la ficha buena: capacidades → 200")
    b.igual(pedir(srv, "GET", ruta("capacidades"), ficha=None)[0], 404, "control: sin ficha → 404")
    b.igual(pedir(srv, "GET", ruta("capacidades"), ficha="otra")[0], 404, "control: con otra ficha → 404")
    b.igual(pedir(srv, "GET", ruta("capacidades"), ficha=FICHA[:-1] + ("0" if FICHA[-1] != "0" else "1"))[0], 404,
            "control: con una ficha del mismo largo que difiere en la última letra → 404")
    b.igual(pedir(srv, "POST", ruta("moneda"), {"id": ID_A1, "moneda": "oro", "cantidad": 1}, ficha="otra")[0], 404,
            "control: un POST con otra ficha → 404 (y no 403: la puerta no se deja ver)")

    # ── no se llega por Caddy ──────────────────────────────────────────────────────────────────────────────────
    b.igual(pedir(srv, "GET", "/gunbound" + ruta("capacidades"))[0], 404,
            "con el prefijo de Caddy (/gunbound/interno/panel/…) y la ficha buena → 404")
    b.igual(pedir(srv, "GET", "/gunbound-prueba" + ruta("capacidades"))[0], 404, "ídem con /gunbound-prueba → 404")
    b.igual(pedir(srv, "GET", ruta("capacidades"), extra={"X-Forwarded-For": "203.0.113.9"})[0], 404,
            "por un proxy (X-Forwarded-For) con la ficha buena → 404")

    # ── POST sin X-R2 ─────────────────────────────────────────────────────────────────────────────────────────
    b.igual(pedir(srv, "POST", ruta("aviso"), {"texto": "hola", "a": "todos"}, x_r2=False)[0], 403,
            "POST sin X-R2 → 403")
    b.igual(pedir(srv, "POST", ruta("aviso"), {"texto": "hola", "a": "todos"}, extra={"X-R2": "0"})[0], 403,
            "POST con X-R2: 0 → 403")
    b.igual(pedir(srv, "POST", ruta("aviso"), {"texto": "hola", "a": "todos"})[0], 200, "control: con X-R2: 1 → 200")

    # ── capacidades = exactamente lo que responde (derivado de probar, no escrito a mano) ──────────────────────
    candidatas = {"ver": ("GET", "salud"), "aviso": ("POST", "aviso"), "echar": ("POST", "echar"),
                  "moneda": ("POST", "moneda"), "mute": ("POST", "mute"), "ban": ("POST", "ban"),
                  "item": ("POST", "item"), "apodo": ("POST", "apodo")}
    responde = {a for a, (m, r) in candidatas.items() if pedir(srv, m, ruta(r), {} if m == "POST" else None)[0] != 404}
    b.igual(set(cap["acciones"]), responde, "capacidades.acciones = las acciones cuya ruta responde")
    b.igual(len(cap["acciones"]), len(set(cap["acciones"])), "capacidades: sin repetidas")
    b.ver({"mute", "ban"}.isdisjoint(cap["acciones"]), "control: lo que no hace (mute, ban) no se anuncia")
    b.igual(([m["id"] for m in cap["monedas"]], cap["version"], cap["juego"]), (["oro", "cash"], 1, "gunbound"),
            "capacidades: monedas oro y cash, versión 1, juego gunbound")
    b.ver(all(m.get("nombre") for m in cap["monedas"]), "cada moneda tiene su nombre para el panel")

    # ── no implementado → 404 ──────────────────────────────────────────────────────────────────────────────────
    for m, r in (("GET", "usuarios"), ("GET", "salas"), ("POST", "mute"), ("GET", "aviso"), ("POST", "salud"),
                 ("GET", ""), ("DELETE", "ficha/" + str(ID_A1))):
        b.igual(pedir(srv, m, ruta(r) if r else P.PREFIJO, {} if m == "POST" else None)[0], 404,
                f"no implementado: {m} {r or '(raíz)'} → 404")

    # ── moneda: suma, anota quién, nunca negativo ──────────────────────────────────────────────────────────────
    st, d = pedir(srv, "POST", ruta("moneda"), {"id": ID_A1, "moneda": "oro", "cantidad": 500})
    b.igual((st, d), (200, {"ok": True, "antes": 100_000, "despues": 100_500}), "moneda: +500 oro → antes y después")
    b.igual(en_base(srv, lambda B: B.jugador(ID_A1).oro), 100_500, "moneda: quedó en la base")
    ult = en_base(srv, lambda B: B.movimientos(ID_A1, 1))[0]
    b.igual((ult["quien"], ult["que"]), (QUIEN, "saldo"), "moneda: el movimiento anota QUIÉN lo pidió")
    pedir(srv, "POST", ruta("moneda"), {"id": ID_A1, "moneda": "oro", "cantidad": 1}, quien="coordinador:otra")
    b.igual(en_base(srv, lambda B: B.movimientos(ID_A1, 1))[0]["quien"], "coordinador:otra",
            "control: otro que pide → otro nombre en la auditoría (no está escrito a mano)")
    b.igual(en_base(srv, lambda B: B.jugador(ID_A2).oro), 100_000, "control: el otro personaje de la cuenta, intacto")
    st, d = pedir(srv, "POST", ruta("moneda"), {"id": ID_A1, "moneda": "cash", "cantidad": -5})
    b.igual((st, d.get("antes"), d.get("despues")), (200, 20_000, 19_995), "control: restar resta (−5 cash)")
    st, d = pedir(srv, "POST", ruta("moneda"), {"id": ID_A1, "moneda": "cash", "cantidad": -P.TOPE_CANTIDAD})
    b.igual((st, d.get("despues")), (200, 0), "restar más de lo que tiene → queda en 0")
    b.igual(en_base(srv, lambda B: B.jugador(ID_A1).cash), 0, "…y en la base es 0, nunca negativo")
    for malo, que in (({"id": ID_A1, "moneda": "rcoin", "cantidad": 1}, "una moneda que no existe"),
                      ({"id": ID_A1, "moneda": "oro", "cantidad": 0}, "cantidad 0"),
                      ({"id": ID_A1, "moneda": "oro", "cantidad": True}, "cantidad booleana"),
                      ({"id": ID_A1, "moneda": "oro", "cantidad": "mucho"}, "cantidad que no es número"),
                      ({"id": ID_A1, "moneda": "oro", "cantidad": P.TOPE_CANTIDAD + 1}, "cantidad pasada del tope")):
        b.igual(pedir(srv, "POST", ruta("moneda"), malo)[0], 400, f"moneda con {que} → 400")
    b.igual(pedir(srv, "POST", ruta("moneda"), {"id": 123, "moneda": "oro", "cantidad": 1})[0], 404,
            "moneda a un id que no existe → 404")
    st, d = pedir(srv, "POST", ruta("moneda"), {"id": ID_A1, "moneda": "rcoin", "cantidad": 1})
    b.ver(isinstance(d.get("error"), str) and d["error"], "los errores vienen como {\"error\": texto}")

    # ── buscar ─────────────────────────────────────────────────────────────────────────────────────────────────
    def nicks(q):
        st, d = pedir(srv, "GET", ruta("buscar?q=") + urllib.request.quote(q))
        return st, [f["nick"] for f in d.get("filas", [])]
    b.igual(sorted(nicks("UCIA")[1]), ["Lucia_2", "Lucia_x"], "buscar por una parte del apodo, sin mayúsculas")
    b.igual(nicks(str(ID_A2))[1][:1], ["Lucia_2"], "buscar por el id del personaje 2 → él primero")
    b.igual(sorted(nicks(str(CUENTA_A))[1]), ["Lucia_2", "Lucia_x"], "buscar por Eñeños ID → los dos personajes")
    b.igual(nicks(str(CUENTA_B))[1], ["Ana9x"], "control: otro Eñeños ID → sólo los suyos")
    b.igual(nicks("a_x")[1], ["Lucia_x"], "el «_» del apodo es una letra (Ana9x no calza con «a_x»)")
    b.igual(nicks("zzz_nadie")[1], [], "control: nada calza → lista vacía")
    b.igual(pedir(srv, "GET", ruta("buscar?q="))[0], 400, "buscar sin q → 400")
    st, d = pedir(srv, "GET", ruta("buscar?q=") + str(CUENTA_A))
    b.ver(all(f["enenos_id"] == CUENTA_A and f["conectado"] is False and f["resumen"] for f in d["filas"]),
          "buscar: cada fila trae el Eñeños ID, conectado y un resumen")

    # ── ficha ──────────────────────────────────────────────────────────────────────────────────────────────────
    st, f = pedir(srv, "GET", ruta(f"ficha/{ID_A2}"))
    b.igual((st, f["id"], f["nick"], f["enenos_id"], f["conectado"], f["baneado"]),
            (200, ID_A2, "Lucia_2", CUENTA_A, False, False), "ficha: identidad del personaje 2")
    b.igual(f["monedas"], {"oro": 100_000, "cash": 20_000}, "ficha: las monedas (las mismas ids de capacidades)")
    b.igual([p["id"] for p in f["personajes"]], [ID_A1, ID_A2], "ficha: los personajes de la misma cuenta")
    campos = {c["nombre"]: c["valor"] for c in f["campos"]}
    b.igual((campos.get("Rango"), campos.get("GP"), campos.get("País")), ("Pollito", 0, srv.srv.mundo.paises[157]),
            "ficha: rango, GP y país en palabras (el nombre sale de paises.json, como en /rango)")
    b.ver(f["movimientos"] and f["movimientos"][0]["que"].startswith("nace"), "ficha: los movimientos (nace)")
    st, f1 = pedir(srv, "GET", ruta(f"ficha/{ID_A1}"))
    b.igual(f1["movimientos"][0]["quien"], QUIEN, "ficha: el último movimiento dice quién (el −10⁹ de cash)")
    b.ver(len(f1["movimientos"]) <= P.TOPE_MOVIMIENTOS, "ficha: como mucho 20 movimientos")
    plano = json.dumps(f1).lower()
    b.ver(not any(x in plano for x in ("pass", "hash", "boleto", "ticket", "clave", "token")),
          "ficha: nada de contraseñas, hashes, boletos ni claves")
    b.igual(pedir(srv, "GET", ruta("ficha/999"))[0], 404, "control: ficha de un id que no existe → 404")
    b.igual(pedir(srv, "GET", ruta("ficha/abc"))[0], 404, "control: ficha con un id que no es número → 404")

    # ── conectados, salud, aviso, echar (con un jugador adentro) ──────────────────────────────────────────────
    b.igual(pedir(srv, "GET", ruta("conectados"))[1], {"filas": []}, "conectados: nadie al principio")
    r = entrar(srv, CUENTA_A)
    r.al_lobby()
    st, d = pedir(srv, "GET", ruta("conectados"))
    fila = d["filas"][0] if d["filas"] else {}
    b.igual((st, len(d["filas"]), fila.get("id"), fila.get("nick"), fila.get("enenos_id"), fila.get("donde"),
             fila.get("ip")), (200, 1, ID_A1, "Lucia_x", CUENTA_A, "Lobby", "127.0.0.1"),
            "conectados: el que entró, con su Eñeños ID y dónde está")
    b.ver(abs(fila.get("desde", 0) - time.time()) < 30, "conectados: «desde» es la hora de conexión (epoch)")
    st, s = pedir(srv, "GET", ruta("salud"))
    b.igual((st, s["en_linea"], s["jugando"]), (200, True, 1), "salud: en línea, 1 jugando")
    b.ver(all(set(x) == {"nombre", "valor"} for x in s["detalle"]), "salud: detalle de {nombre, valor}")
    b.igual(pedir(srv, "GET", ruta(f"buscar?q={CUENTA_A}"))[1]["filas"][0]["conectado"], True,
            "buscar: ahora figura conectado")

    textos_del_sistema(r, 0.3)                                    # lo que haya quedado del lobby
    st, d = pedir(srv, "POST", ruta("aviso"), {"texto": "Mantenimiento en 5 minutos", "a": "uno", "id": ID_A1})
    b.igual((st, d), (200, {"ok": True, "llego_a": 1}), "aviso a uno → llegó a 1")
    b.ver("Mantenimiento en 5 minutos" in textos_del_sistema(r), "…y el jugador lo recibe por el chat del sistema")
    st, d = pedir(srv, "POST", ruta("aviso"), {"texto": "Hola a todos", "a": "todos"})
    b.igual((st, d.get("llego_a")), (200, 1), "aviso a todos → llegó a los que están (1)")
    b.ver("Hola a todos" in textos_del_sistema(r), "…y le llega")
    b.igual(pedir(srv, "POST", ruta("aviso"), {"texto": "x", "a": "uno", "id": ID_B})[0], 404,
            "control: aviso a uno que no está conectado → 404")
    b.igual(pedir(srv, "POST", ruta("aviso"), {"texto": "x", "a": "nadie"})[0], 400, "control: «a» inválido → 400")
    b.igual(pedir(srv, "POST", ruta("aviso"), {"texto": "  ", "a": "todos"})[0], 400, "control: aviso vacío → 400")
    b.igual(pedir(srv, "POST", ruta("aviso"), {"texto": "x" * (P.TOPE_AVISO + 1), "a": "todos"})[0], 400,
            "control: aviso de más de 200 letras → 400")

    b.igual(pedir(srv, "POST", ruta("echar"), {"id": ID_B})[0], 404, "control: echar a uno que no está → 404")
    st, d = pedir(srv, "POST", ruta("echar"), {"id": ID_A1, "motivo": "prueba del banco"})
    b.igual((st, d), (200, {"ok": True}), "echar al que está → ok")
    recibidos, cortado, fin = [], False, time.time() + 3
    try:
        while time.time() < fin:
            c = r.esperar(0x5101, 0.5)
            if c is not None:
                recibidos.append(bytes(c).split(b"\0")[0].decode("latin-1"))
    except (ConnectionError, OSError):
        cortado = True
    b.ver(cortado, "echar: el server le cierra la conexión")
    b.ver(any("prueba del banco" in t for t in recibidos), "echar: antes le llega el motivo por el chat del sistema")
    b.igual(pedir(srv, "GET", ruta("conectados"))[1]["filas"], [], "echar: ya no figura en conectados")
    b.igual(pedir(srv, "POST", ruta("echar"), {"id": ID_A1})[0], 404, "control: echarlo otra vez → 404 (no está)")
    ult = en_base(srv, lambda B: B.movimientos(ID_A1, 1))[0]
    b.igual((ult["que"], ult["detalle"], ult["quien"]), ("echado", "prueba del banco", QUIEN),
            "echar: queda anotado con el motivo y quién")
    r.cerrar()
b.fin()
