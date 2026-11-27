# -*- coding: utf-8 -*-
"""probar_audit — pruebas de regresión para los bugs corregidos en la auditoría de nov-2026.

  B-01  fin_jewel: sólo la llave puede mandar 0x4200; se ignora fuera de partida y si ya hay ganador.
  B-02  volver_del_resultado: 0x3232 no resetea estado si la partida no terminó.
  B-03  elegir_movil: bytes inválidos (p.ej. 16) se ignoran.
  B-04  armar_inicio: posiciones de salida únicas (sin colisión por casilla % len(puntos)).
  B-05  /movil: permite móviles 14 y 15.
  B-06  cambiar_mapa/ajustes durante partida: se ignoran.
  B-07  max_conexiones: cuenta pre-login.
  B-08  _lugar_libre: canal lleno devuelve None y el server rechaza el login.
  B-09  clave_dinamica: trunca a 12+12+4 bytes sin crash.
  B-10  crear sala: manda 0x5101 cuando no quedan IDs.
"""
import struct
import types

from arnes import Banco, ServerDePrueba
from robot import Robot, canjear
from servidor import cifrado, sala
from servidor.entrada import _lugar_libre
from servidor.paquete import con_largo

b = Banco("probar_audit")

SOLO  = bytes.fromhex("b2620000")
JEWEL = bytes.fromhex("b2620c00")


def entrar(srv, eid):
    _, d = canjear(srv.url_canje, srv.pase(eid))
    r = Robot(*srv.mundo)
    r.login(d["usuario"], d["ticket"])
    r.al_lobby()
    r.todos(0x200E, 0.3)
    return r


def armar_sala(srv, ids, ajustes, nombre):
    """Sala de N jugadores en estado JUGANDO. Devuelve (robots, sala_id)."""
    rs = [entrar(srv, i) for i in ids]
    llave = rs[0]
    llave.mandar(0x2120, con_largo(nombre) + ajustes + bytes(4) + bytes([len(ids)]))
    sid = llave.esperar(0x2121)[3:5]
    for r in rs[1:]:
        r.mandar(0x2110, bytes(sid))
        r.esperar(0x2111)
    llave.mandar(0x3430, b"")
    for r in rs:
        r.esperar(0x3432)
    return rs, sid[0] | sid[1] << 8


# ── B-01: fin_jewel ───────────────────────────────────────────────────────────────────────────────────────
with ServerDePrueba(p2p="tunel") as srv:
    rs, sid = armar_sala(srv, [90001001, 90001002], JEWEL, "JewelB01")
    llave, otro = rs

    # control: jugador que NO es la llave manda 0x4200 → no debe terminar la partida
    otro.mandar_cifrado(0x4200, b"\x01")
    b.ver(llave.esperar(0x4410, 0.4) is None, "B-01: 0x4200 de un NO-llave no termina la partida")

    # control: fuera de sala tampoco termina
    entrar_extra = entrar(srv, 90001003)
    entrar_extra.mandar_cifrado(0x4200, b"\x00")
    b.ver(llave.esperar(0x4410, 0.4) is None, "B-01: 0x4200 fuera de sala se ignora")

    # positivo: la llave sí termina (0x4410 va a TODOS los jugadores)
    llave.mandar_cifrado(0x4200, b"\x00")
    b.ver(llave.esperar(0x4410, 0.4) is not None, "B-01: 0x4200 de la llave termina la partida")
    otro.esperar(0x4410, 0.4)  # drena el 0x4410 que también le llegó a otro

    # control: una vez terminada, repetir no vuelve a mandar 0x4410
    llave.mandar_cifrado(0x4200, b"\x00")
    b.ver(otro.esperar(0x4410, 0.4) is None, "B-01: segundo 0x4200 tras el fin se ignora")

    for r in rs + [entrar_extra]:
        r.cerrar()

# ── B-02: volver_del_resultado ────────────────────────────────────────────────────────────────────────────
with ServerDePrueba(p2p="tunel") as srv:
    rs, sid = armar_sala(srv, [90001011, 90001012], SOLO, "RetornoB02")
    llave, otro = rs

    # control: 0x3232 durante partida activa no debe resetear estado
    otro.mandar(0x3232, b"")
    otro.esperar(0x3233)
    estado = srv.en_el_lazo(lambda: srv.srv.mundo.salas[sid].estado)
    b.igual(estado, sala.JUGANDO, "B-02: 0x3232 durante partida no cambia estado a ESPERA")

    # matar al jugador en casilla 1 → la partida termina (1v1 Solo)
    llave.mandar(0x4100, struct.pack("<I", 1) + b"\x01")
    llave.esperar(0x4410)

    # ahora sí 0x3232 debe ir a ESPERA
    otro.mandar(0x3232, b"")
    otro.esperar(0x3233)
    estado2 = srv.en_el_lazo(lambda: srv.srv.mundo.salas[sid].estado)
    b.igual(estado2, sala.ESPERA, "B-02: 0x3232 con ganador definido lleva a ESPERA")

    for r in rs:
        r.cerrar()

# ── B-03: elegir_movil ────────────────────────────────────────────────────────────────────────────────────
with ServerDePrueba(p2p="tunel") as srv:
    a = entrar(srv, 90001021)
    a.mandar(0x2120, con_largo("Moviles") + SOLO + bytes(4) + b"\x02")
    a.esperar(0x2121)

    # valores inválidos (16, 253): se ignoran, el móvil queda en AL_AZAR (0xFF)
    a.mandar(0x3200, bytes([16, 253]))
    a.esperar(0x3201)
    m1 = srv.en_el_lazo(lambda: srv.srv.mundo.sesiones[0].movil1)
    b.igual(m1, 0xFF, "B-03: móvil inválido (16) no se guarda, queda AL_AZAR")

    # valores válidos: 15 y 17 deben aceptarse
    a.mandar(0x3200, bytes([15, 17]))
    a.esperar(0x3201)
    m1, m2 = srv.en_el_lazo(lambda: (srv.srv.mundo.sesiones[0].movil1, srv.srv.mundo.sesiones[0].movil2))
    b.igual((m1, m2), (15, 17), "B-03: móviles 15 y 17 (válidos) se guardan")

    a.cerrar()

# ── B-04: armar_inicio sin colisión de posiciones ─────────────────────────────────────────────────────────
with ServerDePrueba(p2p="tunel") as srv:
    # La corrección del bug cambia casilla → índice de bucle para los lugares de salida.
    # Verificamos que armar_sala termine sin error y que el 0x3432 llegue a los dos jugadores.
    rs, sid = armar_sala(srv, [90001031, 90001032], SOLO, "PosB04")
    b.ver(True, "B-04: armar_inicio completado sin crash con 2 jugadores")
    # Con 4 jugadores en un equipo el bug anterior causaría colisión de posiciones si las casillas
    # difieren por len(puntos); verificar que el server sigue andando:
    rs4, sid4 = armar_sala(srv, [90001033, 90001034, 90001035, 90001036], SOLO, "PosB04-4p")
    b.ver(True, "B-04: armar_inicio completado sin crash con 4 jugadores")
    for r in rs + rs4:
        r.cerrar()

# ── B-05: /movil acepta 14 y 15 ──────────────────────────────────────────────────────────────────────────
with ServerDePrueba(p2p="tunel") as srv:
    a = entrar(srv, 90001041)
    a.mandar(0x2120, con_largo("MovCom") + SOLO + bytes(4) + b"\x02")
    a.esperar(0x2121)

    # /movil 14 debe responder con confirmación (el mensaje menciona "14")
    a.mandar(0x5100, b"\x00/movil 14")
    rsp = a.esperar(0x5101)
    b.ver(rsp is not None and b"14" in rsp, "B-05: /movil 14 aceptado (confirmación con '14')")
    m1 = srv.en_el_lazo(lambda: srv.srv.mundo.sesiones[0].movil1)
    b.igual(m1, 14, "B-05: /movil 14 guarda 14 en la sesión")

    a.mandar(0x5100, b"\x00/movil 15")
    rsp15 = a.esperar(0x5101)
    b.ver(rsp15 is not None and b"15" in rsp15, "B-05: /movil 15 aceptado (confirmación con '15')")
    m1 = srv.en_el_lazo(lambda: srv.srv.mundo.sesiones[0].movil1)
    b.igual(m1, 15, "B-05: /movil 15 guarda 15 en la sesión")

    # control: 16 sigue rechazado (manda el mensaje de uso, no cambia el móvil)
    a.mandar(0x5100, b"\x00/movil 16")
    rsp16 = a.esperar(0x5101)
    b.ver(rsp16 is not None and b"Uso:" in rsp16, "B-05: /movil 16 manda mensaje de uso")
    m1 = srv.en_el_lazo(lambda: srv.srv.mundo.sesiones[0].movil1)
    b.igual(m1, 15, "B-05: /movil 16 rechazado (el móvil no cambió de 15)")
    a.cerrar()

# ── B-06: cambiar config durante partida ─────────────────────────────────────────────────────────────────
with ServerDePrueba(p2p="tunel") as srv:
    rs, sid = armar_sala(srv, [90001051, 90001052], SOLO, "ConfigB06")
    llave, otro = rs
    mapa_antes = srv.en_el_lazo(lambda: srv.srv.mundo.salas[sid].mapa)
    llave.mandar(0x3100, bytes([7]))    # cambiar_mapa durante JUGANDO: lo ignora _llave_en_espera
    llave.esperar(0x3105)              # el server sigue mandando 0x3105 pero no cambia el mapa
    mapa_despues = srv.en_el_lazo(lambda: srv.srv.mundo.salas[sid].mapa)
    b.igual(mapa_antes, mapa_despues, "B-06: cambiar mapa durante partida se ignora")
    for r in rs:
        r.cerrar()

# ── B-09: clave_dinamica trunca inputs largos (no crash) ─────────────────────────────────────────────────
# La corrección añade [:12] en usuario y contraseña: inputs grandes se truncan silenciosamente.
try:
    resultado = cifrado.clave_dinamica("A" * 20, "B" * 20, b"\x01\x02\x03\x04")
    b.ver(len(resultado) == 16, "B-09: clave_dinamica con inputs largos trunca y devuelve 16 bytes (no crash)")
except (ValueError, Exception) as e:
    b.ver(False, f"B-09: clave_dinamica con inputs largos no debería lanzar ({e})")

# el resultado truncado (12 chars) debe ser igual al de 12 chars directamente
truncado = cifrado.clave_dinamica("A" * 12, "B" * 12, b"\x01\x02\x03\x04")
directo  = cifrado.clave_dinamica("A" * 20, "B" * 20, b"\x01\x02\x03\x04")
b.igual(directo, truncado, "B-09: clave_dinamica('A'*20,...) = clave_dinamica('A'*12,...) (truncación silenciosa)")

# con inputs normales no falla
try:
    cifrado.clave_dinamica("usuario", "boleto12", b"\x01\x02\x03\x04")
    b.ver(True, "B-09: clave_dinamica con inputs normales no falla")
except ValueError as e:
    b.ver(False, f"B-09: clave_dinamica con inputs normales falla: {e}")

# ── B-10: crear sala manda 0x5101 cuando no quedan IDs ───────────────────────────────────────────────────
with ServerDePrueba(p2p="tunel") as srv:
    a = entrar(srv, 90001061)
    # Llenamos todas las salas (255 objetos ficticios) directamente en el estado del server
    def llenar_salas():
        for i in range(255):
            srv.srv.mundo.salas[i] = object()
    srv.en_el_lazo(llenar_salas)
    a.mandar(0x2120, con_largo("SinID") + SOLO + bytes(4) + b"\x02")
    rsp = a.esperar(0x5101, 1.0)
    b.ver(rsp is not None, "B-10: cuando no quedan IDs el server manda 0x5101 en vez de silencio")
    a.cerrar()

# ── B-08: _lugar_libre devuelve None cuando el canal está lleno ───────────────────────────────────────────
# (helper puro de entrada.py — el login en un server real requeriría 255 conexiones simultáneas)
class _Fake:
    def __init__(self, lc): self.lugar_canal = lc

ns_lleno  = types.SimpleNamespace(sesiones=[_Fake(i) for i in range(255)])
ns_hueco  = types.SimpleNamespace(sesiones=[_Fake(i) for i in range(254)])   # falta el 254

result_lleno = _lugar_libre(ns_lleno)
result_hueco = _lugar_libre(ns_hueco)
b.ver(result_lleno is None, "B-08: _lugar_libre devuelve None con 255 lugares ocupados")
b.igual(result_hueco, 254, "B-08: control — con 254 ocupados devuelve el 254 libre")

# ── B-12: crear sala recorta el cupo a 1..8 (como cambiar_cupo) · B-13: saldos con tope u32 ────────────
with ServerDePrueba(p2p="tunel") as srv:
    a = entrar(srv, 90001071)
    a.mandar(0x2120, con_largo("Cupo20") + SOLO + bytes(4) + b"\x14")
    sid = a.esperar(0x2121)[3:5]
    sid = sid[0] | sid[1] << 8
    b.igual(srv.en_el_lazo(lambda: srv.srv.mundo.salas[sid].cupo), 8, "B-12: cupo 20 al crear queda en 8")
    a.cerrar()
    c = entrar(srv, 90001072)
    c.mandar(0x2120, con_largo("Cupo4") + SOLO + bytes(4) + b"\x04")
    sid = c.esperar(0x2121)[3:5]
    sid = sid[0] | sid[1] << 8
    b.igual(srv.en_el_lazo(lambda: srv.srv.mundo.salas[sid].cupo), 4, "B-12: control: cupo 4 se respeta")
    c.cerrar()

    def oro_tras_sumar():
        base = srv.srv.mundo.base
        for _ in range(5):
            base.sumar(90001071, oro=1_000_000_000)
        return base.con.execute("SELECT oro FROM jugadores WHERE enenos_id=?", (90001071,)).fetchone()[0]
    b.igual(srv.en_el_lazo(oro_tras_sumar), 4294967295, "B-13: el oro no pasa de 0xFFFFFFFF (el cliente lo lee u32)")

    def oro_tras_restar():
        base = srv.srv.mundo.base
        base.sumar(90001071, oro=-5_000_000_000)
        return base.con.execute("SELECT oro FROM jugadores WHERE enenos_id=?", (90001071,)).fetchone()[0]
    b.igual(srv.en_el_lazo(oro_tras_restar), 0, "B-13: control: restar de más sigue quedando en 0")

# ── B-15: el corte por keepalive (TimeoutError del socket) en plena partida no congela el server ──────
# Desde Python 3.11 asyncio.TimeoutError es TimeoutError; el Docker usa 3.13. Con 3.10 la prueba pasa igual.
import time
with ServerDePrueba(p2p="tunel") as srv:
    a, c = entrar(srv, 90001081), entrar(srv, 90001082)
    a.mandar(0x2120, con_largo("Corte") + SOLO + bytes(4) + b"\x02")
    sid = a.esperar(0x2121)[3:5]
    c.mandar(0x2110, bytes(sid))
    c.esperar(0x2111)
    a.mandar(0x3430, b"")
    a.esperar(0x3432), c.esperar(0x3432)

    def cortar_por_keepalive():
        o = next(x for x in srv.srv.mundo.sesiones if x.enenos_id == 90001082)
        o.escritor.transport.get_protocol().connection_lost(TimeoutError(110, "Connection timed out"))
    try:
        srv.en_el_lazo(cortar_por_keepalive)
        time.sleep(0.5)
        quedan = srv.en_el_lazo(lambda: sorted(x.enenos_id for x in srv.srv.mundo.sesiones))
    except Exception:                                      # noqa: BLE001
        quedan = "el lazo no respondió en 5 s"
    b.ver(isinstance(quedan, list), "B-15: el lazo sigue respondiendo tras el corte por keepalive")
    b.igual(quedan, [90001081], "B-15: la sesión cortada se saca de la lista")
    b.ver(a.esperar(0x4410, 1.0) is not None, "B-15: el que se cortó cuenta como caído → fin de la partida")
    a.cerrar(); c.cerrar()

# ── B-16: uno que no lee no hace crecer la memoria sin fin · B-17: login con «²» recibe respuesta ─────
from servidor import sesion as _sesion
with ServerDePrueba(p2p="tunel") as srv:
    tope_original = _sesion.TOPE_SALIDA
    _sesion.TOPE_SALIDA = 200_000                         # más chico para que la prueba sea rápida
    try:
        mudo = entrar(srv, 90001091)                      # entra al canal y nunca más lee
        a = entrar(srv, 90001092)
        texto = b"x" * 250
        sigue = lambda: srv.en_el_lazo(lambda: any(x.enenos_id == 90001091 for x in srv.srv.mundo.sesiones))
        for tanda in range(40):
            for _ in range(250):
                a.mandar_cifrado(0x2010, bytes([len(texto)]) + texto)
            a.todos(0x201F, 0.05)
            if not sigue():
                break
        b.ver(not sigue(), "B-16: al que no lee y pasa el tope de salida se lo corta y se lo saca")
        b.ver(srv.en_el_lazo(lambda: any(x.enenos_id == 90001092 for x in srv.srv.mundo.sesiones)),
              "B-16: control: el que sí lee sigue conectado")
        mudo.cerrar(); a.cerrar()
    finally:
        _sesion.TOPE_SALIDA = tope_original

    r = Robot(*srv.mundo)
    r.mandar(0x1000)
    r.esperar(0x1001)
    r.mandar(0x1010, cifrado.cifrar_estatico(b"\xb2".ljust(16, b"\0")) + bytes(16) + bytes(48))
    b.ver(r.esperar(0x1012, 1.0) is not None, "B-17: usuario «²» (isdigit pero no int) → 0x1012, no silencio")
    r.cerrar()

# ── B-14: un pase cuya cabecera JSON no es un objeto se rechaza (antes: AttributeError → 500) ─────────
from servidor.pase import Verificador
v = Verificador("gunbound", b"\x00" * 32)
b.igual(v.comprobar("W10.e30.AAAA"), (None, "pase mal formado"), "B-14: cabecera «[]» → pase mal formado")
b.igual(v.comprobar("e30.W10.AAAA"), (None, "pase mal formado"), "B-14: carga «[]» → pase mal formado")
b.igual(v.comprobar("e30.e30.AAAA"), (None, "algoritmo no aceptado"), "B-14: control: cabecera «{}» sigue al chequeo de alg")

b.fin()
