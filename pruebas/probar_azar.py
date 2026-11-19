# -*- coding: utf-8 -*-
"""probar_azar — el móvil «aleatorio» se sortea en CADA partida (19-nov: a Benja le tocó 2 veces seguidas el mismo
y a un amigo 3: el server pisaba la elección con el primer sorteo y lo repetía en todas las partidas de esa sala)."""
import random
import types

from arnes import Banco
from servidor import partida
from servidor.sesion import AL_AZAR

b = Banco("probar_azar")

mundo = types.SimpleNamespace(prob_dragon=0, mapas={1: {
    "positions_a_side": [{"x_min": 10, "x_max": 20, "y": 0}] * 8,
    "positions_b_side": [{"x_min": 10, "x_max": 20, "y": 0}] * 8}})


def jugador(casilla, m1=AL_AZAR, m2=AL_AZAR):
    return types.SimpleNamespace(casilla=casilla, nick=f"j{casilla}", equipo=casilla % 2, movil1=m1, movil2=m2)


def sala(js):
    return types.SimpleNamespace(mapa=1, ajustes=bytes.fromhex("b2620000"), jugadores=js)


def moviles(inicio, x):
    """(m1, m2) de cada jugador, leídos del 0x3432 armado (22 bytes por jugador después de la cabecera)."""
    cab = len(partida.ajustes_de_partida(x.ajustes, len(x.jugadores))) + 1 + 2
    return [(inicio[cab + 22 * i + 14], inicio[cab + 22 * i + 15]) for i in range(len(x.jugadores))]


random.seed(1119)
a, c = jugador(0), jugador(1, m1=3, m2=7)
x = sala([a, c])
vistos = []
for _ in range(40):
    vistos.append(moviles(partida.armar_inicio(mundo, x, solo=True), x))

b.igual((a.movil1, a.movil2), (AL_AZAR, AL_AZAR), "la elección «aleatorio» sigue siendo aleatorio después de 40 partidas")
distintos = {v[0][0] for v in vistos}
b.ver(len(distintos) >= 8, f"en 40 partidas el aleatorio da muchos móviles distintos (dio {len(distintos)})")
repetidos = sum(1 for i in range(1, len(vistos)) if vistos[i][0][0] == vistos[i - 1][0][0])
b.ver(repetidos <= 10, f"no se repite siempre el anterior ({repetidos} de 39 seguidos iguales)")
b.ver(all(0 <= v[0][0] <= 18 and 0 <= v[0][1] <= 18 for v in vistos), "lo sorteado es un móvil válido (nunca 0xFF)")
b.ver(a.moviles_en_juego == vistos[-1][0], "queda anotado lo que salió en la partida en curso")
# control al revés: el que ELIGIÓ un móvil juega siempre con ése (el sorteo no lo toca)
b.ver(all(v[1] == (3, 7) for v in vistos), "el que eligió móviles fijos juega siempre con ésos")
b.igual((c.movil1, c.movil2), (3, 7), "y su elección no cambia")

# control: el código viejo (pisar la elección) repetía el mismo en TODAS — se reproduce a mano para ver que la
# prueba lo distinguiría
viejo = jugador(0)
fijos = []
for _ in range(10):
    if viejo.movil1 == AL_AZAR:
        viejo.movil1 = partida._movil_al_azar(mundo)
    fijos.append(viejo.movil1)
b.ver(len(set(fijos)) == 1, "control: con el código viejo salían 10 iguales (la prueba de arriba lo habría cazado)")
b.fin()
