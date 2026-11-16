# -*- coding: utf-8 -*-
"""probar_entrada — pase → canje → boleto → login al mundo → canal. Con el server de verdad en un hilo."""
import json
import urllib.request

from arnes import Banco, ServerDePrueba
from robot import Robot, canjear, lista_de_mundos
from servidor.paquete import texto_c

b = Banco("probar_entrada")

with ServerDePrueba(ip_publica="", broker_publico="juego.ejemplo:8372", oro_inicial=1234, cash_inicial=55) as srv:
    # ── el broker ──────────────────────────────────────────────────────────────────────────────────────────
    crudo = lista_de_mundos(*srv.broker)
    b.igual(crudo[4] | crudo[5] << 8, 0x1102, "el broker contesta la lista")
    cuerpo = crudo[6:]
    b.igual(cuerpo[3], 1, "un mundo")
    n = cuerpo[7]
    nombre = cuerpo[8:8 + n].decode("latin-1")
    b.igual(nombre, srv.aj.nombre_mundo, "nombre del mundo")
    resto = cuerpo[8 + n:]
    resto = resto[1 + resto[0]:]                        # la descripción
    b.igual(bytes(resto[0:4]), bytes([127, 0, 0, 1]), "sin GB_IP_PUBLICA anuncia la IP por la que llegó")
    b.igual(resto[4] << 8 | resto[5], srv.mundo[1], "anuncia el puerto del mundo (big endian)")
    b.igual(bytes(resto[12:16]), bytes((0xFB, 100, 0, 1)), "los 3 bytes del Legacy y «habilitado» al final")

    # ── la salud ───────────────────────────────────────────────────────────────────────────────────────────
    with urllib.request.urlopen(srv.url_canje.replace("/canje", "/salud"), timeout=5) as r:
        salud = json.loads(r.read())
    b.igual((salud["ok"], salud["juego"]), (True, "gunbound"), "/salud")

    # ── el canje ───────────────────────────────────────────────────────────────────────────────────────────
    codigo, r1 = canjear(srv.url_canje, srv.pase(10000570))
    b.igual(codigo, 200, "canje con un pase bueno")
    b.igual(r1.get("usuario"), "10000570", "el usuario es el Eñeños ID")
    b.igual(len(r1.get("ticket", "")), 12, "el boleto entra en la contraseña (12)")
    b.igual(r1.get("servidor"), "juego.ejemplo:8372", "le dice al launcher el broker público")
    b.igual((r1.get("nick"), r1.get("nuevo")), ("GB10000570", True), "nace con nick provisorio")
    codigo, _ = canjear(srv.url_canje, srv.pase(10000570, aud="gunbound-prueba"))
    b.igual(codigo, 401, "control: pase del server de prueba → 401")
    p = srv.pase(10000571)
    canjear(srv.url_canje, p)
    b.igual(canjear(srv.url_canje, p)[0], 409, "control: el mismo pase dos veces → 409")
    j = srv.en_el_lazo(lambda: srv.srv.base.jugador(10000570))
    b.igual((j.oro, j.cash), (1234, 55), "saldos iniciales de GB_ORO_INICIAL / GB_CASH_INICIAL")

    # ── el login ───────────────────────────────────────────────────────────────────────────────────────────
    r = Robot(*srv.mundo)
    resp = r.login(r1["usuario"], r1["ticket"])
    b.igual(bytes(resp[0:2]), b"\0\0", "login: estado 0 (adentro)")
    b.igual(texto_c(resp[6:18]), "GB10000570", "login: el nick en +6")
    b.igual(resp[18], 0, "login: género en +18 (0 = varón)")
    b.igual(len(resp) > 89, True, "login: 89 bytes + la cola cifrada")
    cola, bien = r.descifrar(resp[89:], 0x1012)
    b.ver(bien, "login: la cola cifrada cierra con la clave del boleto")
    b.igual(int.from_bytes(cola[12:16], "little"), 55, "login: el cash va en la cola")
    cash, bien = r.descifrar(r.esperar(0x1032), 0x1032)
    b.igual(int.from_bytes(cash[0:4], "little"), 55, "0x1032 cash")
    canal = r.esperar(0x2001)
    b.ver(canal is not None and canal[0:2] == b"\0\0", "0x2001 al entrar")
    r.al_lobby()
    me = r.esperar(0x200E)
    b.ver(me is not None and texto_c(me[1:13]) == "GB10000570", "al llegar al lobby se presenta él mismo (0x200E)")
    b.igual(len(me or b""), 30, "ficha del canal: 30 bytes")

    # un segundo jugador: el primero lo ve llegar y el segundo ve a los dos
    _, r2d = canjear(srv.url_canje, srv.pase(10000572))
    r2 = Robot(*srv.mundo)
    r2.login(r2d["usuario"], r2d["ticket"])
    llega = r.esperar(0x200E)
    b.ver(llega is not None and texto_c(llega[1:13]) == "GB10000572", "el que estaba ve llegar al nuevo")
    r2.al_lobby()
    vistos = {texto_c(x[1:13]) for x in r2.todos(0x200E)}
    b.igual(vistos, {"GB10000570", "GB10000572"}, "el nuevo ve a los dos (él incluido)")

    # chat: llega a los dos con el nick
    r2.mandar_cifrado(0x2010, bytes([4]) + b"hola")
    for quien, rr in (("1", r), ("2", r2)):
        dato = rr.esperar(0x201F)
        txt, _ = rr.descifrar(dato or b"", 0x201F)
        b.ver(txt[1:13].rstrip(b"\0") == b"GB10000572" and txt[14:18] == b"hola", f"el chat le llega al {quien}")

    # ── controles del login ────────────────────────────────────────────────────────────────────────────────
    malo = Robot(*srv.mundo)
    b.igual(bytes(malo.login(r1["usuario"], "boletoFALSO1")[:2]), b"\x11\x00", "control: boleto equivocado → 0x11")
    malo2 = Robot(*srv.mundo)
    b.igual(bytes(malo2.login("99999999", "loquesea")[:2]), b"\x10\x00", "control: sin canje → 0x10")
    # entrar de nuevo con la misma cuenta corta la conexión vieja
    r3 = Robot(*srv.mundo)
    r3.login(r1["usuario"], r1["ticket"])
    try:
        r.esperar(0x9999, 1.0)
        b.ver(False, "la conexión vieja tendría que cortarse")
    except (ConnectionError, OSError):
        b.ver(True, "")
    # un canje nuevo invalida el boleto viejo
    canjear(srv.url_canje, srv.pase(10000572))
    r4 = Robot(*srv.mundo)
    b.igual(bytes(r4.login(r2d["usuario"], r2d["ticket"])[:2]), b"\x11\x00", "control: el boleto viejo deja de servir")
    for x in (r, r2, r3, r4, malo, malo2):
        x.cerrar()

# sin la clave de Cuenta Eñeños el canje contesta 503 (y no deja entrar a nadie)
with ServerDePrueba() as srv2:
    srv2.srv.verificador.clave = None
    b.igual(canjear(srv2.url_canje, srv2.pase(1))[0], 503, "control: sin clave pública → 503")
b.fin()
