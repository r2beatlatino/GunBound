# -*- coding: utf-8 -*-
"""robot — un cliente de GunBound de mentira, para el banco. Habla el protocolo como el Legacy medido.

    r = Robot(*srv.mundo); r.login(usuario, boleto)       → espera el 0x1012 y el 0x2001
    r.mandar(0x2120, cuerpo) · r.mandar_cifrado(0x2010, datos) · r.esperar(0x2121)

⚠ El robot prueba que el server es COHERENTE consigo mismo y con lo medido; que ande con el juego de verdad se
   prueba con la mesa (herramientas/mesa.py). El login lo arma como el cliente medido (bloque estático del usuario,
   un bloque más que el server no usa, y el bloque dinámico con la contraseña en [0:12] y la versión en [0x14]).
"""
import json
import os
import secrets
import socket
import struct
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from servidor import cifrado, paquete  # noqa: E402

VERSION = 179


def canjear(url, el_pase):
    req = urllib.request.Request(url, data=json.dumps({"pase": el_pase}).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def lista_de_mundos(host, puerto):
    s = socket.create_connection((host, puerto), 5)
    s.sendall(paquete.armar(0, 0x1100, b""))
    cort = paquete.Cortador()
    while True:
        for crudo in cort.meter(s.recv(4096)):
            s.close()
            return crudo


class Robot:
    def __init__(self, host, puerto):
        self.s = socket.create_connection((host, puerto), 5)
        self.s.settimeout(5)
        self.cort = paquete.Cortador()
        self.cola = []
        self.enviado = 0
        self.clave = None
        self.usuario = ""

    def cerrar(self):
        try:
            self.s.close()
        except OSError:
            pass

    # ── mandar ────────────────────────────────────────────────────────────────────────────────────────────
    def mandar(self, comando, cuerpo=b""):
        crudo = paquete.armar(self.enviado, comando, cuerpo)
        self.enviado += len(crudo)
        self.s.sendall(crudo)

    def mandar_cifrado(self, comando, datos):
        datos = bytes(datos)
        datos += bytes(12 - len(datos) % 12) if len(datos) % 12 else b""
        self.mandar(comando, cifrado.cifrar(datos, self.clave, comando))

    # ── recibir ───────────────────────────────────────────────────────────────────────────────────────────
    def _leer(self, plazo):
        self.s.settimeout(max(0.05, plazo))
        try:
            pedazo = self.s.recv(65536)
        except socket.timeout:
            return False
        if not pedazo:
            raise ConnectionError("el server cortó")
        for crudo in self.cort.meter(pedazo):
            self.cola.append((crudo[4] | (crudo[5] << 8), crudo[6:]))
        return True

    def esperar(self, comando, plazo=3.0):
        """El primer mensaje con ese comando (los demás quedan en la cola). -> cuerpo, o None si no llegó."""
        fin = time.time() + plazo
        while True:
            for i, (c, cuerpo) in enumerate(self.cola):
                if c == comando:
                    del self.cola[i]
                    return cuerpo
            restante = fin - time.time()
            if restante <= 0:
                return None
            self._leer(restante)

    def todos(self, comando, plazo=0.5):
        salida = []
        while True:
            c = self.esperar(comando, plazo)
            if c is None:
                return salida
            salida.append(c)

    def descifrar(self, cuerpo, comando):
        return cifrado.descifrar(cuerpo, self.clave, comando)

    # ── entrar ────────────────────────────────────────────────────────────────────────────────────────────
    def login(self, usuario, contrasena, version=VERSION):
        self.usuario = usuario
        self.mandar(0x1000)
        ficha = self.esperar(0x1001)
        self.clave = cifrado.clave_dinamica(usuario, contrasena, ficha)
        dinamico = bytearray(36)
        dinamico[0:12] = contrasena.encode("latin-1")[:12].ljust(12, b"\0")
        dinamico[0x14:0x16] = struct.pack("<H", version)
        cuerpo = (cifrado.cifrar_estatico(usuario.encode().ljust(16, b"\0")) + secrets.token_bytes(16)
                  + cifrado.cifrar(bytes(dinamico), self.clave, 0x1010))
        self.mandar(0x1010, cuerpo)
        return self.esperar(0x1012)

    def al_lobby(self):
        """Lo que hace el Legacy al llegar al lobby: 0x6000, 0x1090, … y el 0x6004 vacío al final."""
        self.mandar(0x6000)
        self.mandar(0x1090, b"\x00")
        self.mandar(0x6004)
        self.esperar(0x1091)
