# -*- coding: utf-8 -*-
"""arnes — lo común del banco: contar verdes y rojas, y levantar el server en un hilo con una clave de prueba.

★ Regla del banco (la misma que en R2Beat): toda prueba tiene su CONTROL al revés — el caso que DEBE fallar.
  Una prueba que nunca puede dar rojo no prueba nada.
"""
import asyncio
import os
import secrets
import sys
import tempfile
import threading
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from servidor import firma_ed25519 as ed, pase, registro  # noqa: E402
from servidor.__main__ import Server  # noqa: E402
from servidor.ajustes import Ajustes  # noqa: E402

registro.silenciar(os.environ.get("GB_VER_LOG") != "1")


class Banco:
    def __init__(self, nombre):
        self.nombre = nombre
        self.verdes = 0
        self.rojas = []

    def ver(self, condicion, que):
        if condicion:
            self.verdes += 1
        else:
            self.rojas.append(que)
            print(f"  ✗ {que}", flush=True)

    def igual(self, real, esperado, que):
        self.ver(real == esperado, f"{que}: esperaba {esperado!r}, salió {real!r}")

    def fin(self):
        estado = "VERDE" if not self.rojas else "ROJO"
        print(f"{self.nombre}: {estado} · {self.verdes} bien, {len(self.rojas)} mal", flush=True)
        sys.exit(0 if not self.rojas else 1)


class ServerDePrueba:
    """El server entero (broker, mundo, web) en un hilo, con puertos al azar y una base nueva en una carpeta temporal."""

    def __init__(self, **ajustes):
        self.semilla = secrets.token_bytes(32)
        self.dir = tempfile.mkdtemp(prefix="gb_prueba_")
        base = dict(entorno="prueba-banco", dir_estado=self.dir, escucha="127.0.0.1", escucha_http="127.0.0.1",
                    puerto_broker=0, puerto_mundo=0, puerto_http=0, pase_juego="gunbound", gm={90000001})
        base.update(ajustes)
        self.aj = Ajustes(**base)
        self.srv = None
        self.lazo = asyncio.new_event_loop()
        self._hilo = threading.Thread(target=self._correr, daemon=True)

    def _correr(self):
        asyncio.set_event_loop(self.lazo)
        self.lazo.run_forever()

    def __enter__(self):
        self._hilo.start()

        async def crear():                       # la base (SQLite) se crea y se usa en el MISMO hilo
            self.srv = Server(self.aj, clave_publica=ed.publica(self.semilla))
            await self.srv.arrancar()

        asyncio.run_coroutine_threadsafe(crear(), self.lazo).result(10)
        return self

    def __exit__(self, *a):
        self.lazo.call_soon_threadsafe(self.srv.cerrar)
        time.sleep(0.1)
        self.lazo.call_soon_threadsafe(self.lazo.stop)

    def en_el_lazo(self, f):
        """Corre `f()` dentro del hilo del server (para mirar su estado sin pisarlo)."""
        fut = asyncio.run_coroutine_threadsafe(_llamar(f), self.lazo)
        return fut.result(5)

    @property
    def broker(self):
        return ("127.0.0.1", self.srv.broker.puerto)

    @property
    def mundo(self):
        return ("127.0.0.1", self.srv.mundo.puerto)

    @property
    def url_canje(self):
        return f"http://127.0.0.1:{self.srv.web.puerto}/canje"

    def pase(self, enenos_id, aud="gunbound", **kw):
        return pase.firmar_pase(self.semilla, aud, enenos_id, **kw)


async def _llamar(f):
    return f()
