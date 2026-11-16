# -*- coding: utf-8 -*-
"""rangos — el rango por GP, la bandera del país y los 4 WORD de insignias que lee el cliente.

En el GunBound original los rangos hasta 6000 GP iban por GP fijo y desde 6900 GP por PUESTO en el ranking
(actualización diaria); acá usamos la versión de GP fijo de TorHammer para todos los niveles. El cliente NO tiene
tabla propia: el rango lo decide siempre el server y el cliente dibuja el cuadro `valor + 5` de `rank2.img`
(19 = pollito, 18 … 0 = rubí, -1 … -4 = dragón plateado, 20 = GM).

Las 4 insignias (8 bytes, signed WORD little endian) siempre van en este orden:
    1. rango total (permisos; 20 = GM) · 2. rango de temporada (no se dibuja) · 3. ícono visible · 4. país (0 = «?»).
"""
from .paquete import u16

POLLITO = 19
GM = 20

# Cortes fijos de TorHammer: (gp_mínimo, rango), ordenados de menor a mayor.
TABLA_GP = [
    (0, 19),
    (1100, 18),
    (1200, 17),
    (1500, 16),
    (1800, 15),
    (2300, 14),
    (2800, 13),
    (3500, 12),
    (4200, 11),
    (5100, 10),
    (6000, 9),
    (6900, 8),
    (8173, 7),
    (9940, 6),
    (13077, 5),
    (16025, 4),
    (21985, 3),
    (27281, 2),
    (35335, 1),
    (51222, 0),
    (107916, -1),
    (199629, -2),
    (227295, -3),
    (238204, -4),
]

NOMBRES = {
    19: "Pollito",
    18: "Hacha de madera",
    17: "Hacha de madera doble",
    16: "Martillo de piedra",
    15: "Martillo de piedra doble",
    14: "Hacha",
    13: "Hacha doble",
    12: "Hacha de plata",
    11: "Hacha de plata doble",
    10: "Hacha de oro",
    9: "Hacha de oro doble",
    8: "Hacha de batalla",
    7: "Hacha de batalla+",
    6: "Batalla de plata",
    5: "Batalla de plata+",
    4: "Batalla de oro",
    3: "Batalla de oro+",
    2: "Violeta",
    1: "Zafiro",
    0: "Rubi",
    -1: "Diamante",
    -2: "Dragon azul",
    -3: "Dragon rojo",
    -4: "Dragon plateado",
    20: "GM",
}


def rango_por_gp(gp):
    """El rango que corresponde a esa cantidad de GP (por debajo de 0 devuelve Pollito)."""
    gp = int(gp)
    for minimo, rango in reversed(TABLA_GP):
        if gp >= minimo:
            return rango
    return POLLITO


def siguiente(gp):
    """-> (próximo_rango, gp_que_falta), o None si ya alcanzó el máximo."""
    gp = max(0, int(gp))
    for minimo, rango in TABLA_GP:
        if minimo > gp:
            return rango, minimo - gp
    return None


def rango_de(j):
    """El rango efectivo de `j`: GM pisa todo, después `rango_fijo`, y si es None va por GP."""
    if j.es_gm:
        return GM
    if j.rango_fijo is not None:
        return int(j.rango_fijo)
    return rango_por_gp(j.gp)


def insignias(j):
    """Los 8 bytes (4 WORD) de rango y país que van en login, canal y salas."""
    r = rango_de(j)
    return u16(r) + u16(r) + u16(r) + u16(j.pais)
