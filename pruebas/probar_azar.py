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

# ── la tabla del sorteo (19-nov, Benja eligió 5 %): como el Serv3 — los 16 normales parejos, 5 % especiales mitad y mitad
import os
from servidor import ajustes as aj
from servidor.partida import ESPECIALES, MOVILES

def sorteo(prob, n):
    m = types.SimpleNamespace(prob_dragon=prob)
    return [partida._movil_al_azar(m) for _ in range(n)]

random.seed(5)
sin = sorteo(0, 8000)
b.igual(sorted(set(sin)), list(range(16)), "sin especiales salen los 16 normales, 14 y 15 incluidos (y nada más)")
b.ver(min(sin.count(i) for i in range(16)) > 8000 / 16 * 0.8, "los 16 salen parejos (ninguno por debajo del 80 % de lo justo)")
todo = sorteo(100, 2000)
b.igual(sorted(set(todo)), sorted(ESPECIALES), "al 100 % sólo salen Dragón y Caballero")
b.ver(abs(todo.count(17) - todo.count(18)) < 200, f"Dragón y Caballero mitad y mitad ({todo.count(17)} / {todo.count(18)})")
cinco = sorteo(5, 40000)
pct = 100 * sum(1 for v in cinco if v in ESPECIALES) / len(cinco)
b.ver(4.5 <= pct <= 5.5, f"al 5 % salen especiales cerca del 5 % (dio {pct:.2f} %)")
# control al revés: al 2 % (el valor viejo) la misma cuenta NO cae en la franja del 5 % — la prueba distingue
dos = sorteo(2, 40000)
pct2 = 100 * sum(1 for v in dos if v in ESPECIALES) / len(dos)
b.ver(not (4.5 <= pct2 <= 5.5), f"control: al 2 % dio {pct2:.2f} %, fuera de la franja del 5 %")
# control al revés: con la lista vieja (0..13) el 14 y el 15 no salían nunca — la primera comprobación lo habría cazado
viejo = MOVILES[:]
partida.MOVILES[:] = list(range(14))
try:
    b.ver({14, 15}.isdisjoint(sorteo(0, 4000)), "control: con la lista vieja el 14 y el 15 no salían nunca")
finally:
    partida.MOVILES[:] = viejo

# el ajuste: 5 si no se dice nada; GB_ESPECIALES lo cambia; fuera de 0..100 se recorta
os.environ.pop("GB_ESPECIALES", None)
b.igual(aj.Ajustes().prob_especiales, 5, "sin GB_ESPECIALES el aleatorio usa 5 %")
os.environ["GB_ESPECIALES"] = "2"
b.igual(aj.Ajustes().prob_especiales, 2, "GB_ESPECIALES=2 lo baja a 2 %")
os.environ["GB_ESPECIALES"] = "500"
b.igual(aj.Ajustes().prob_especiales, 100, "un valor fuera de rango se recorta a 100")
os.environ.pop("GB_ESPECIALES", None)
b.fin()
