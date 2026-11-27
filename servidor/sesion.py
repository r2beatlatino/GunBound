# -*- coding: utf-8 -*-
"""sesion — UNA conexión de un jugador con el mundo: lo que es de la CONEXIÓN, no de la sala ni de la cuenta.

⚠ Lo que es de la sala (mapa, ajustes, quién es la llave) vive en `Sala`; acá sólo el lugar del jugador en ella
   (casilla, equipo, móviles). Mezclar las dos cosas es el bug que más se repite en estos servers.
"""
import secrets
import time

from . import cifrado, paquete
from .paquete import u16
from .registro import log

SIN_LUGAR = -1
AL_AZAR = 0xFF          # móvil «al azar»
TOPE_SALIDA = 2_000_000  # bytes pendientes de mandar a una conexión que no lee


class Sesion:
    def __init__(self, escritor, direccion, traza=False):
        self.traza = traza
        self.escritor = escritor
        self.ip = direccion[0] if direccion else "0.0.0.0"
        self.puerto_origen = direccion[1] if direccion else 0
        self.desde = int(time.time())           # cuándo se conectó (lo muestra el panel del Coordinador)
        self.enviado = 0                        # bytes mandados por esta conexión (la secuencia sale de acá)
        self.ficha = secrets.token_bytes(4)     # la que se manda en 0x1001: entra en la clave dinámica
        self.unico = secrets.token_bytes(4)
        self.jugador = None                     # base.Jugador, después del login
        self.usuario = ""                       # lo que el cliente usó de usuario (el Eñeños ID en texto)
        self.boleto = ""                        # la «contraseña»: entra en la clave dinámica
        self._clave = None
        self.version = 0
        self.lugar_canal = SIN_LUGAR
        self.canal = 0
        self.presentado = False                 # ¿ya se le mandó quién está en el canal? (canal.presentar)
        # en la sala
        self.sala = None
        self.casilla = SIN_LUGAR
        self.equipo = 0
        self.movil1 = AL_AZAR
        self.movil2 = AL_AZAR
        self.listo = False
        self.p2p_directo = False                # lo pone el mundo según GB_P2P (sala.ficha_ocupante)
        self.cerrada = False

    # ── identidad ─────────────────────────────────────────────────────────────────────────────────────────
    @property
    def nick(self):
        return self.jugador.nick if self.jugador else "?"

    @property
    def enenos_id(self):
        return self.jugador.enenos_id if self.jugador else 0

    def __repr__(self):
        return f"<{self.nick}#{self.enenos_id} {self.ip}>"

    # ── cifrado ───────────────────────────────────────────────────────────────────────────────────────────
    def preparar_clave(self, usuario, boleto):
        self.usuario, self.boleto = usuario, boleto
        self._clave = cifrado.clave_dinamica(usuario, boleto, self.ficha)

    @property
    def clave(self):
        return self._clave

    def descifrar(self, datos, comando):
        if self._clave is None:
            return b"", False
        return cifrado.descifrar(datos, self._clave, comando)

    def cifrar(self, datos, comando):
        # ⚠ El relleno es SIEMPRE de 1 a 12 bytes (si ya era múltiplo de 12 se agregan 12): así lo hacía el server
        #   con el que se midió el cliente Legacy, y no se cambia sin medir.
        datos = bytes(datos)
        datos += bytes(12 - len(datos) % 12)
        return cifrado.cifrar(datos, self._clave, comando)

    # ── mandar ────────────────────────────────────────────────────────────────────────────────────────────
    def enviar(self, comando, cuerpo=b"", rtc=None):
        if self.cerrada or self.escritor is None:
            return
        if rtc is not None:
            cuerpo = u16(rtc) + bytes(cuerpo)
        crudo = paquete.armar(self.enviado, comando, cuerpo)
        if self.traza:
            log("TRAZA", f"{self.nick} ← 0x{comando:04X} ({len(cuerpo)}) {bytes(cuerpo[:64]).hex()}")
        self.enviado += len(crudo)
        try:
            self.escritor.write(crudo)
        except Exception as e:                                          # noqa: BLE001
            log("MUNDO", f"{self}: no pude mandar 0x{comando:04X}: {e}")
            self.cerrada = True
            return
        transporte = getattr(self.escritor, "transport", None)
        if transporte is not None and transporte.get_write_buffer_size() > TOPE_SALIDA:
            # sólo drena la conexión que está leyendo: uno que no lee nunca haría crecer la memoria sin fin
            log("MUNDO", f"{self}: más de {TOPE_SALIDA // 1_000_000} MB sin leer, se corta")
            self.cerrada = True
            transporte.abort()                  # close() esperaría a vaciar un buffer que nadie lee

    def enviar_cifrado(self, comando, datos, rtc=None):
        self.enviar(comando, self.cifrar(datos, comando), rtc=rtc)

    def cerrar(self):
        self.cerrada = True
        try:
            if self.escritor is not None:
                self.escritor.close()
        except Exception:                                               # noqa: BLE001
            pass
