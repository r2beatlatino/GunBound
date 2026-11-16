# -*- coding: utf-8 -*-
"""probar_personajes — dos personajes por cuenta, creados desde el launcher (pase → ficha → crear → canje).
Decisiones de Benja (16-nov): 2 por cuenta, género libre, nacen pollito, el país se cambia después."""
import json
import struct
import urllib.error
import urllib.request
from pathlib import Path

from arnes import Banco, ServerDePrueba
from robot import Robot
from servidor import rangos
from servidor.base import DESPLAZAMIENTO_2

b = Banco("probar_personajes")


def post(srv, ruta, datos, cabeceras=None):
    url = srv.url_canje.replace("/canje", ruta)
    req = urllib.request.Request(url, data=json.dumps(datos).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **(cabeceras or {})})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def entrar(srv, canje):
    r = Robot(*srv.mundo)
    return r, r.login(canje["usuario"], canje["ticket"])


CUENTA = 90000031
with ServerDePrueba() as srv:
    # ── la lista y el país sugerido ────────────────────────────────────────────────────────────────────────
    st, d = post(srv, "/personajes", {"pase": srv.pase(CUENTA)}, {"CF-IPCountry": "AR"})
    b.igual((st, d.get("personajes"), d.get("maximo"), d.get("pais_sugerido")), (200, [], 2, 9),
            "cuenta nueva: sin personajes, máximo 2, país sugerido por la cabecera (AR = 9)")
    ficha = d["ficha"]
    st, d2 = post(srv, "/personajes", {"pase": srv.pase(CUENTA)})
    b.igual(d2.get("pais_sugerido"), 0, "control: sin cabecera de país, sugerido 0 («?»)")
    b.igual(post(srv, "/personajes", {"pase": "basura"})[0], 401, "control: pase inválido → 401")

    # ── crear ──────────────────────────────────────────────────────────────────────────────────────────────
    b.igual(post(srv, "/personajes/crear", {"ficha": ficha, "nick": "a", "genero": "f", "pais": 9})[0], 400,
            "nick inválido → 400")
    b.igual(post(srv, "/personajes/crear", {"ficha": "x" * 24, "nick": "Ana_1", "genero": "f", "pais": 9})[0], 401,
            "control: ficha que no existe → 401")
    st, d = post(srv, "/personajes/crear", {"ficha": ficha, "nick": "Ana_1", "genero": "f", "pais": 9})
    b.igual((st, [p["id"] for p in d["personajes"]]), (200, [CUENTA]), "el 1.º tiene el id de la cuenta")
    st, d = post(srv, "/personajes/crear", {"ficha": ficha, "nick": "Ana_2", "genero": "f", "pais": 157})
    ids = [p["id"] for p in d["personajes"]]
    b.igual((st, ids), (200, [CUENTA, DESPLAZAMIENTO_2 + CUENTA]), "el 2.º: las dos mujeres, ids distintos")
    b.ver(all(p["rango"] == rangos.POLLITO and p["gp"] == 0 for p in d["personajes"]), "los dos nacen pollito")
    b.igual(post(srv, "/personajes/crear", {"ficha": ficha, "nick": "Ana_3", "genero": "m", "pais": 0})[0], 403,
            "un 3.º → 403 (máximo 2)")
    _, otra = post(srv, "/personajes", {"pase": srv.pase(90000032)})
    b.igual(post(srv, "/personajes/crear", {"ficha": otra["ficha"], "nick": "ana_1", "genero": "m", "pais": 0})[0],
            409, "nick ocupado (sin importar mayúsculas) → 409")

    # ── cambiar el país después ────────────────────────────────────────────────────────────────────────────
    st, d = post(srv, "/personajes/pais", {"ficha": ficha, "personaje": ids[1], "pais": 208})
    b.igual((st, d["personajes"][1]["pais"]), (200, 208), "el país se cambia después (Uruguay)")
    b.igual(post(srv, "/personajes/pais", {"ficha": otra["ficha"], "personaje": ids[1], "pais": 1})[0], 403,
            "control: el personaje de otra cuenta → 403")

    # ── canje del personaje elegido y login ────────────────────────────────────────────────────────────────
    b.igual(post(srv, "/canje", {"ficha": otra["ficha"], "personaje": ids[1]})[0], 403,
            "control: canjear un personaje ajeno → 403")
    st, c2 = post(srv, "/canje", {"ficha": ficha, "personaje": ids[1]})
    b.igual((st, c2.get("usuario")), (200, str(ids[1])), "canje con ficha: el usuario es el id del personaje 2")
    r2, l2 = entrar(srv, c2)
    b.igual(l2[6:11].tobytes() if hasattr(l2, "tobytes") else bytes(l2[6:11]), b"Ana_2", "entra como Ana_2")
    b.igual(l2[18], 1, "con el byte de mujer")
    b.igual(struct.unpack("<4h", bytes(l2[27:35])), (19, 19, 19, 208), "pollito con la bandera elegida")

    # una persona, un personaje adentro: entrar con el 1 corta al 2
    st, c1 = post(srv, "/canje", {"ficha": ficha, "personaje": ids[0]})
    r1, l1 = entrar(srv, c1)
    b.igual(bytes(l1[6:11]), b"Ana_1", "entra como Ana_1")
    try:
        r2.esperar(0xFFFF, 1.0)
        cortado = False
    except (ConnectionError, OSError):
        cortado = True
    b.ver(cortado, "al entrar con el otro personaje de la misma cuenta, el anterior queda afuera")

    # el canje viejo con {"pase"} sigue siendo el personaje 1
    st, c = post(srv, "/canje", {"pase": srv.pase(CUENTA)})
    b.igual((st, c.get("usuario")), (200, str(CUENTA)), "canje con pase solo = personaje 1 (como antes)")

    # GM por cuenta: el 2.º personaje del GM (90000001) también es GM
    _, g = post(srv, "/personajes", {"pase": srv.pase(90000001)})
    post(srv, "/personajes/crear", {"ficha": g["ficha"], "nick": "GM_uno", "genero": "m", "pais": 0})
    st, d = post(srv, "/personajes/crear", {"ficha": g["ficha"], "nick": "GM_dos", "genero": "m", "pais": 0})
    _, cg = post(srv, "/canje", {"ficha": g["ficha"], "personaje": d["personajes"][1]["id"]})
    _, lg = entrar(srv, cg)
    b.igual(struct.unpack("<h", bytes(lg[27:29]))[0], rangos.GM, "el 2.º personaje de una cuenta GM es GM (20)")
    b.igual(d["personajes"][1]["rango_nombre"], "GM", "la lista trae el NOMBRE del rango (para la tarjeta)")

    # ── la lista de países para el menú del launcher (GET, sin pase: es pública) ───────────────────────────
    with urllib.request.urlopen(srv.url_canje.replace("/canje", "/gunbound/paises"), timeout=5) as r:
        paises = json.loads(r.read())["paises"]
    por_n = {p["n"]: p for p in paises}
    b.igual(por_n[0], {"n": 0, "nombre": "Sin país", "iso": None}, "/paises: el 0 es «sin país» («?» en el juego)")
    b.igual((por_n[9]["nombre"], por_n[9]["iso"]), ("Argentina", "AR"), "/paises: 9 = Argentina, AR")
    b.igual((por_n[208]["iso"], por_n[157]["iso"]), ("UY", "PE"), "/paises: el número es el del juego (Uruguay, Perú)")
    b.igual(len(paises), 1 + len(json.loads((Path(__file__).resolve().parent.parent / "servidor" / "datos" /
                                              "paises.json").read_text("utf-8"))["paises"]),
            "/paises: todos los de paises.json + el 0 (derivado, no a mano)")
    b.ver(all(p["iso"] is None or (len(p["iso"]) == 2 and p["iso"].isupper()) for p in paises), "/paises: iso de 2 letras o null")
    st, _ = post(srv, "/paises", {})
    b.igual(st, 404, "control: /paises por POST no existe")
b.fin()
