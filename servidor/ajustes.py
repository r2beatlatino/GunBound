# -*- coding: utf-8 -*-
"""ajustes — TODO lo que se configura desde afuera, en un solo lugar.

Cada entorno (prod / prueba) es el MISMO código con otro `.env`: ver `despliegue/ejemplo.env`.
Ninguna IP ni ruta está escrita en el resto del código: sale de acá.
"""
import os
from pathlib import Path

_DIR_SERVIDOR = Path(__file__).resolve().parent
DIR_DATOS_JUEGO = _DIR_SERVIDOR / "datos"          # tablas del juego que van DENTRO de la imagen (mapas, precios)


def _ent(nombre, omision):
    v = (os.environ.get(nombre) or "").strip()
    try:
        return int(v) if v else omision
    except ValueError:
        return omision


def _txt(nombre, omision=""):
    return (os.environ.get(nombre) or "").strip() or omision


def _lista_enteros(nombre):
    salida = set()
    for parte in _txt(nombre).replace(";", ",").split(","):
        parte = parte.strip()
        if parte.isdigit():
            salida.add(int(parte))
    return salida


class Ajustes:
    """Se lee UNA vez al arrancar (`cargar()`); las pruebas arman la suya con `Ajustes(**cambios)`."""

    def __init__(self, **cambios):
        # prod | prueba — sólo cambia el nombre en el log y el `aud` por omisión del pase
        self.entorno = _txt("GB_ENTORNO", "local")
        # dónde vive lo que NO se reconstruye: la base de los jugadores (un volumen de Docker)
        self.dir_estado = Path(_txt("GB_ESTADO", str(Path.cwd() / "estado")))
        # dónde escucha (dentro del contenedor / de la máquina)
        self.escucha = _txt("GB_ESCUCHA", "0.0.0.0")
        self.puerto_broker = _ent("GB_PUERTO_BROKER", 8372)
        self.puerto_mundo = _ent("GB_PUERTO_MUNDO", 8370)
        self.puerto_http = _ent("GB_PUERTO_HTTP", 8371)
        self.escucha_http = _txt("GB_ESCUCHA_HTTP", "127.0.0.1")   # afuera va detrás de Caddy (HTTPS)
        # lo que el broker ANUNCIA para el mundo: la IP por la que el jugador llega desde su casa.
        # Vacío = la IP por la que llegó al broker (sirve en la LAN y en la misma PC; en un VPS con NAT hay que ponerla)
        self.ip_publica = _txt("GB_IP_PUBLICA")
        self.puerto_mundo_publico = _ent("GB_PUERTO_MUNDO_PUBLICO", 0) or self.puerto_mundo
        # lo que el canje le dice al launcher para escribir en el registro del cliente: "host:puerto" del broker
        self.broker_publico = _txt("GB_BROKER_PUBLICO")
        # el pase de Cuenta Eñeños: `aud` que acepta ESTE server (gunbound / gunbound-prueba)
        self.pase_juego = _txt("GB_PASE_JUEGO", "gunbound-prueba" if self.entorno == "prueba" else "gunbound")
        self.clave_publica = _txt("GB_CUENTAS_CLAVE_PUBLICA")      # base64url / hex / JWKS
        self.url_cuentas = _txt("GB_CUENTAS_URL")                  # o se pide UNA vez /clave-publica al arrancar
        self.boleto_horas = _ent("GB_BOLETO_HORAS", 12)
        # el mundo que se ve en la lista
        self.nombre_mundo = _txt("GB_NOMBRE_MUNDO", "Eñeños")
        self.descripcion_mundo = _txt("GB_DESCRIPCION_MUNDO", "Avatar ON")
        self.capacidad_mundo = _ent("GB_CAPACIDAD", 200)
        self.anuncio_canal = _txt("GB_ANUNCIO_CANAL", "Bienvenido a GunBound en Eñeños. /ayuda para los comandos.")
        self.anuncio_sala = _txt("GB_ANUNCIO_SALA", "Solo en la sala: /practica en Jewel.")
        # la cuenta nueva
        self.oro_inicial = _ent("GB_ORO_INICIAL", 100_000)
        self.cash_inicial = _ent("GB_CASH_INICIAL", 20_000)
        # los Eñeños ID que pueden usar los comandos de GM (coma)
        self.gm = _lista_enteros("GB_GM")
        # prueba y laboratorio: dejar /practica a todos (en prod también: es para un jugador solo)
        self.max_conexiones = _ent("GB_MAX_CONEXIONES", 500)
        # directo (omisión) = UDP entre los jugadores; si no contesta, el cliente (parche 6) pasa al túnel a los 2 s
        # tunel = todo por el server desde el principio (para probar varios clientes en UNA PC: ahí el directo no anda)
        self.p2p = _txt("GB_P2P", "directo").lower()
        # 1 = anota cada mensaje que entra y sale (para medir con el cliente de verdad; en prod, apagado)
        self.traza = _txt("GB_TRAZA") == "1"
        for k, v in cambios.items():
            if not hasattr(self, k):
                raise AttributeError(f"ajuste desconocido: {k}")
            setattr(self, k, v)
        self.dir_estado = Path(self.dir_estado)

    @property
    def ruta_base(self):
        return self.dir_estado / "gunbound.db"


def cargar():
    return Ajustes()
