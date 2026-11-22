# -*- coding: utf-8 -*-
"""canal — el lobby: quién está, y el chat.

0x2001 (entrar al canal), medido con el Legacy: [00 00][canal WORD][lugar más alto][cantidad] + una FICHA de
30 bytes por jugador + el anuncio del canal en texto:
    lugar (1) · nick (12) · género (1) · avatar (8) · insignias (8: rango total, temporada, ícono visible, país)
⚠ Con 33 bytes (la ficha del Serv2, con gremio y sin género) el Legacy lee corrido y no entra al lobby.

0x200E (alguien llegó) y 0x200F (alguien se fue) les avisan a los que ya están. 0x200E lleva la misma ficha de
30 bytes (medido con dos clientes: el que estaba ve al nuevo).

★ MEDIDO (16-nov, dos clientes): el Legacy NO arma la lista del canal con 0x2001. En la pantalla de servidores el
  0x2001 sólo dice «entraste» (lector 0x4F27BF: mira el estado y pide 0x6000 y 0x1090) y la lista se descarta.
  ⇒ Al que entra se le presenta cada uno de los que ya estaban con un 0x200E, recién cuando ya está en el lobby
  (en su primer 0x6004 vacío, que es lo último que pide el lobby al armarse: `presentar`). Él va incluido.
"""
from . import rangos
from .paquete import fijo, u8, u16
from .registro import log


def ficha(s):
    j = s.jugador
    return u8(s.lugar_canal) + fijo(j.nick, 12) + u8(j.byte_genero) + j.avatar + rangos.insignias(j)


def entrar(mundo, s, pedido):
    """Pone a `s` en el canal (al entrar al mundo, o al volver de una sala) y les avisa a los demás."""
    s.canal = 0 if pedido == 0xFFFF else pedido
    s.presentado = False
    presentes = [x for x in mundo.en_canal() if x is not s] + [s]
    mas_alto = max(x.lugar_canal for x in presentes)
    cuerpo = bytearray(b"\x00\x00" + u16(s.canal) + u8(mas_alto) + u8(len(presentes)))
    for x in presentes:
        cuerpo += ficha(x)
    cuerpo += mundo.aj.anuncio_canal.encode("latin-1", "replace")
    s.enviar(0x2001, bytes(cuerpo))
    for x in presentes:
        if x is not s:
            x.enviar(0x200E, ficha(s))


def presentar(mundo, s):
    """Le manda al recién llegado un 0x200E por cada uno que está en el canal, ÉL INCLUIDO: el cliente busca el
    nombre de quien habla por su lugar en esta lista, y sin él mismo su propio chat sale sin nombre (medido)."""
    for x in mundo.en_canal():
        s.enviar(0x200E, ficha(x))


def avisar_salida(mundo, s):
    """Se fue del canal (a una sala o del juego): los del canal lo sacan de la lista."""
    if s.lugar_canal < 0:
        return
    for x in mundo.en_canal():
        if x is not s:
            x.enviar(0x200F, u8(s.lugar_canal))


def pedir_canal(mundo, s, cuerpo):
    """0x2000: el jugador pide un canal (los dos últimos bytes).

    ★ MEDIDO (16-nov, Eñeños): al ABANDONAR una partida el Legacy no manda 0x3001 (salir de la sala): manda este
      0x2000 directo. Si no se lo saca de la sala acá, el server lo sigue teniendo adentro y su próximo «Create»
      (0x2120) se ignora callado ⇒ no puede crear ni entrar a otra sala hasta reconectar."""
    if s.sala is not None:
        from . import sala  # sala importa canal: acá adentro, para no hacer un ciclo
        sala.sacar_de_sala(mundo, s)
    pedido = cuerpo[-2] | (cuerpo[-1] << 8) if len(cuerpo) >= 2 else 0xFFFF
    entrar(mundo, s, pedido)


def chat(mundo, s, cuerpo):
    """0x2010: cifrado, [largo][texto]. Se reparte a los del canal (o a los de la sala, si está en una)."""
    datos, bien = s.descifrar(cuerpo, 0x2010)
    if not bien or not datos:
        return
    texto = datos[1:1 + datos[0]]
    log("CHAT", f"{s.nick}: {texto.decode('latin-1')}")
    salida = u8(s.lugar_canal) + fijo(s.nick, 12) + u8(len(texto)) + texto
    destino = s.sala.jugadores if s.sala else mundo.en_canal()
    for x in destino:
        x.enviar_cifrado(0x201F, salida)


ATIENDE = {0x2000: pedir_canal, 0x2010: chat}
