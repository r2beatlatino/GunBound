# -*- coding: utf-8 -*-
"""boletos — el canje: un pase de Cuenta Eñeños se cambia por un BOLETO corto que el cliente usa de contraseña.

Por qué hace falta: el cliente de 2013 sólo sabe entrar con usuario y contraseña (≤ 12 letras cada uno), y además
usa la contraseña para armar la clave del cifrado. El pase (un JWT de ~300 letras) no entra ahí.

    launcher ──pase──▶ POST /canje ──▶ {usuario: "<Eñeños ID>", ticket: "<12 letras>", servidor: "host:puerto"}
    launcher ──abre GunBound.exe con usuario + ticket (cifrados en el argumento) ──▶ broker ──▶ mundo

Es lo MISMO que hace EDA (`POST /eda/pase` → usuario + ticket). El boleto:
  · lo inventa el server, al azar; vale `GB_BOLETO_HORAS` (12 h): el cliente lo vuelve a mandar cada vez que entra
    a un mundo, así que tiene que durar lo que dura la sesión del juego abierto;
  · un canje nuevo de la misma cuenta REEMPLAZA al anterior (el boleto viejo deja de servir);
  · vive en memoria: si el server se reinicia, el jugador vuelve a tocar JUGAR (igual que con un corte).
"""
import secrets
import string
import time

LETRAS = string.ascii_letters + string.digits
LARGO = 12                       # lo que entra en el campo de contraseña del login (0x1010)
LARGO_FICHA = 24                 # ficha corta del launcher (24 alfanuméricos, 10 min)


class Boletos:
    def __init__(self, horas=12):
        self.vida = horas * 3600
        self._por_id = {}          # id_personaje -> (boleto, vence)

    def emitir(self, enenos_id, ahora=None):
        ahora = time.time() if ahora is None else ahora
        boleto = "".join(secrets.choice(LETRAS) for _ in range(LARGO))
        self._por_id[int(enenos_id)] = (boleto, ahora + self.vida)
        if len(self._por_id) > 20_000:
            self.limpiar(ahora)
        return boleto

    def vigente(self, enenos_id, ahora=None):
        """El boleto vigente de ese personaje, o None."""
        ahora = time.time() if ahora is None else ahora
        par = self._por_id.get(int(enenos_id))
        if not par or par[1] < ahora:
            return None
        return par[0]

    def anular(self, enenos_id):
        self._por_id.pop(int(enenos_id), None)

    def limpiar(self, ahora=None):
        ahora = time.time() if ahora is None else ahora
        for k, (_, v) in list(self._por_id.items()):
            if v < ahora:
                del self._por_id[k]


class Fichas:
    """Fichas temporales de launcher: `ficha -> cuenta` (para crear/elegir personaje sin gastar otro pase)."""

    def __init__(self, segundos=600):
        self.vida = segundos
        self._por_ficha = {}       # ficha -> (cuenta, vence)

    def emitir(self, cuenta, ahora=None):
        ahora = time.time() if ahora is None else ahora
        ficha = "".join(secrets.choice(LETRAS) for _ in range(LARGO_FICHA))
        self._por_ficha[ficha] = (int(cuenta), ahora + self.vida)
        if len(self._por_ficha) > 20_000:
            self.limpiar(ahora)
        return ficha

    def cuenta(self, ficha, ahora=None):
        """El Eñeños ID de esa ficha vigente, o None si falta o venció."""
        if not ficha or not isinstance(ficha, str):
            return None
        ahora = time.time() if ahora is None else ahora
        par = self._por_ficha.get(ficha)
        if not par or par[1] < ahora:
            if par:
                del self._por_ficha[ficha]
            return None
        return par[0]

    def anular(self, ficha):
        self._por_ficha.pop(ficha, None)

    def limpiar(self, ahora=None):
        ahora = time.time() if ahora is None else ahora
        for k, (_, v) in list(self._por_ficha.items()):
            if v < ahora:
                del self._por_ficha[k]
