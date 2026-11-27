# -*- coding: utf-8 -*-
"""entrada — cómo entra un jugador al mundo.

    cliente ── 0x1000 ─────────────▶ server ── 0x1001 ficha (4 bytes al azar)
    cliente ── 0x1010 login ───────▶ server ── 0x1012 (sí o no) · 0x1032 cash · 0x2001 el canal

El login (0x1010) trae:
    [0:16]   el usuario, con el cifrado ESTÁTICO          → el Eñeños ID en texto (lo puso el launcher)
    [16:32]  un bloque estático más (no se usa)
    [32: ]   cifrado DINÁMICO: [0:12] la contraseña (= el boleto del canje) · [0x14:0x16] la versión del cliente
La clave dinámica sale de usuario + contraseña + ficha: para descifrar, el server tiene que saber de antemano qué
contraseña espera ⇒ el boleto vigente de ese Eñeños ID (`boletos.py`).

La respuesta 0x1012 del cliente Legacy (v179), medida por su lector (rama 0x004F1FDE):
    +0  WORD estado (0 = adentro) · +2 DWORD único · +6 nick (12) · +18 género (0 = varón) · +19 gremio (8)
    +27 insignias (8: rango total, temporada, ícono visible, país) · +37 puesto total (4) · +49 puesto país (4)
    +61 GP (4) · +69 oro (4) · ceros hasta 89 bytes
    y CIFRADO: [funciones del mundo, % de GP, % de oro, cash, funciones, 0]
"""
from . import canal, cifrado, rangos
from .paquete import fijo, texto_c, u32
from .registro import log

ANTES_DEL_LOGIN = {0x1000, 0x1010, 0x0000}

NO_EXISTE = bytes.fromhex("1000")
CLAVE_MALA = bytes.fromhex("1100")

# lo que el mundo tiene prendido (máscara): avatares, y los efectos del clima. Medido: sin esto no hay viento.
AVATARES = 1 << 4
EFECTOS = (1 << 13) | (1 << 14) | (1 << 15) | (1 << 16) | (1 << 17) | (1 << 18) | (1 << 19)
FUNCIONES = AVATARES | EFECTOS


def ficha(mundo, s, cuerpo):
    s.enviar(0x1001, s.ficha)


def vivo(mundo, s, cuerpo):
    pass                                     # 0x0000: «sigo acá»


def login(mundo, s, cuerpo):
    if s.jugador is not None:
        return
    if len(cuerpo) < 32 + 16:
        s.enviar(0x1012, NO_EXISTE)
        return
    usuario = texto_c(cifrado.descifrar_estatico(cuerpo[0:16]))
    boleto = mundo.boletos.vigente(int(usuario)) if usuario.isdigit() else None
    if boleto is None:
        log("ENTRADA", f"{s.ip}: «{usuario}» sin boleto vigente (¿tocó JUGAR hace más de {mundo.aj.boleto_horas} h?)")
        s.enviar(0x1012, NO_EXISTE)
        return
    s.preparar_clave(usuario, boleto)
    datos, control_bien = s.descifrar(cuerpo[32:], 0x1010)
    if not control_bien or texto_c(datos[0:12]) != boleto:
        log("ENTRADA", f"{s.ip}: «{usuario}» con boleto equivocado")
        s.enviar(0x1012, CLAVE_MALA)
        return
    j = mundo.base.jugador(int(usuario))
    if j is None or j.baneado:
        log("ENTRADA", f"{s.ip}: «{usuario}» {'baneado' if j else 'sin jugador'}")
        s.enviar(0x1012, NO_EXISTE)
        return
    s.version = datos[0x14] | (datos[0x15] << 8) if len(datos) >= 0x16 else 0
    # Una PERSONA, un personaje adentro a la vez: el que entra corta al que estaba (sea el mismo personaje o el
    # otro de la misma cuenta). Así nadie juega con sus dos personajes juntos (p. ej. en la misma sala).
    for viejo in mundo.sesiones_de_cuenta(j.cuenta):
        log("ENTRADA", f"{j.nick}: la cuenta {j.cuenta} ya estaba adentro con {viejo.nick} ({viejo.ip}); se corta")
        mundo.desconectar(viejo)
    lugar = _lugar_libre(mundo)
    if lugar is None:
        log("ENTRADA", f"{s.ip}: canal lleno (255 jugadores), no entra {j.nick}")
        s.enviar(0x1012, NO_EXISTE)
        return
    s.jugador = j
    s.lugar_canal = lugar
    mundo.sesiones.append(s)
    mundo.base.tocar(j.enenos_id)
    log("ENTRADA", f"{s} adentro · cliente v{s.version} · {len(mundo.sesiones)} en línea")

    puesto_total, puesto_pais = mundo.base.puestos(j.enenos_id)
    r = bytearray(89)
    r[2:6] = s.unico
    r[6:18] = fijo(j.nick, 12)
    r[18] = j.byte_genero
    r[19:27] = fijo(j.gremio, 8)
    r[27:35] = rangos.insignias(j)
    r[37:41] = u32(puesto_total)
    r[49:53] = u32(puesto_pais)
    r[61:65] = u32(j.gp)
    r[69:73] = u32(j.oro)
    cola = u32(FUNCIONES) + u32(100) + u32(100) + u32(j.cash) + u32(FUNCIONES) + bytes(4)
    s.enviar(0x1012, bytes(r) + s.cifrar(cola, 0x1012))
    avisar_cash(s)
    canal.entrar(mundo, s, 0xFFFF)           # el Legacy entra solo al canal: no manda pedido


def avisar_cash(s):
    s.enviar_cifrado(0x1032, u32(s.jugador.cash))


def buscar(mundo, s, cuerpo):
    """0x1020: el cliente pregunta por alguien (por su nick)."""
    datos, _ = s.descifrar(cuerpo, 0x1020)
    pedido = texto_c(datos[0:12])
    otro = mundo.base.por_nick(pedido) if pedido else None
    if otro is None:
        s.enviar_cifrado(0x1021, bytes(12 + 12 + 8 + 4), rtc=0)
        return
    s.enviar_cifrado(0x1021, fijo(otro.nick, 12) + fijo(otro.nick, 12) + fijo(otro.gremio, 8)
                     + rangos.insignias(otro)[:4], rtc=0)


def _lugar_libre(mundo):
    usados = {x.lugar_canal for x in mundo.sesiones}
    for i in range(255):
        if i not in usados:
            return i
    return None                              # no hay lugar libre; entrada.login debe rechazar


ATIENDE = {0x1000: ficha, 0x0000: vivo, 0x1010: login, 0x1020: buscar}
