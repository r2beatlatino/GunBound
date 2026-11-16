# -*- coding: utf-8 -*-
"""mesa — varios clientes de GunBound manejados por API, sin tocar el mouse ni el teclado de la PC.

    python herramientas/mesa.py                     arranca la mesa (http://127.0.0.1:8399) y se queda
    python herramientas/mesa.py abrir 90000001      abre un cliente para ese Eñeños ID (canje con pase de PRUEBA)
    python herramientas/mesa.py lista
    python herramientas/mesa.py foto <n> [archivo]  (n = el número de la mesa, 1, 2, …)
    python herramientas/mesa.py clic <n> <x> <y>    coordenadas de la foto
    python herramientas/mesa.py texto <n> "hola" [caja]   escribe en la caja de texto (0, 1…) sin mandar
    python herramientas/mesa.py decir <n> "hola" [caja]   escribe y aprieta Enter (el chat)
    python herramientas/mesa.py tecla <n> enter [segundos]   (espacio 1.5 = disparar con fuerza)
    python herramientas/mesa.py log <n>             lo que anotó el agente adentro del juego
    python herramientas/mesa.py cerrar [n]

Cada cliente se abre con Frida y `mesa_agente.js` adentro: los BOTONES y las teclas le llegan por DirectInput de
mentira; la POSICIÓN del mouse, por mensajes a su ventana. ⚠ Cerrar la mesa cierra los juegos que abrió.
"""
import json
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "herramientas"))
sys.path.insert(0, str(RAIZ))

PUERTO = 8399
DIK = {"enter": 0x1C, "esc": 0x01, "tab": 0x0F, "espacio": 0x39, "izq": 0xCB, "der": 0xCD, "arriba": 0xC8,
       "abajo": 0xD0, "borrar": 0x0E, "f1": 0x3B, "f5": 0x3F}


class Mesa:
    def __init__(self, canje, cliente, ventana):
        import frida
        self.frida = frida
        self.canje, self.cliente, self.ventana = canje, Path(cliente), ventana
        self.juegos = {}            # n -> {pid, id, script, sesion}
        self.n = 0
        self.lock = threading.Lock()

    def abrir(self, enenos_id, juego="gunbound", canje=None):
        import jugar
        from servidor import cifrado
        r = jugar.canjear(canje or self.canje, jugar.pase_de_prueba(int(enenos_id), juego))
        host, _, puerto = r["servidor"].rpartition(":")
        jugar.escribir_registro(self.cliente, host, puerto, self.ventana)
        # ⚠ el juego toma TODA la línea de comandos como el argumento cifrado: sin la ruta del exe adelante
        pid = self.frida.spawn(str(self.cliente / "GunBound.exe"), argv=[cifrado.argumento_cliente(r["usuario"], r["ticket"])],
                               cwd=str(self.cliente))
        ses = self.frida.attach(pid)
        sc = ses.create_script((RAIZ / "herramientas" / "mesa_agente.js").read_text("utf-8"))
        sc.on("message", lambda m, d: print(f"[agente {enenos_id}]", m, flush=True))
        ses.on("detached", lambda motivo, *x: print(f"[agente {enenos_id}] se desprendió: {motivo} {x}", flush=True))
        sc.load()
        self.frida.resume(pid)
        with self.lock:
            self.n += 1
            self.juegos[self.n] = {"pid": pid, "id": int(enenos_id), "nick": r["nick"], "script": sc, "sesion": ses}
            return self.n, pid, r["nick"]

    def hwnd(self, n):
        import ventanas
        pid = self.juegos[n]["pid"]
        for h, p, _, _ in ventanas.ventanas():
            if p == pid:
                return h
        raise KeyError(f"el juego {n} no tiene ventana")

    def clic(self, n, x, y, doble=False):
        import ventanas
        h = self.hwnd(n)
        sc = self.juegos[n]["script"]
        sc.exports_sync.ventana(h)
        # el juego guarda «estoy activo» de los mensajes de activación: se le mandan (no le roban el foco a nadie)
        ventanas.u32.PostMessageW(h, 0x001C, 1, 0)        # WM_ACTIVATEAPP (sí)
        ventanas.u32.PostMessageW(h, 0x0006, 1, 0)        # WM_ACTIVATE (WA_ACTIVE)
        ventanas.u32.PostMessageW(h, 0x0007, 0, 0)        # WM_SETFOCUS
        time.sleep(0.1)
        ventanas.u32.PostMessageW(h, ventanas.WM_MOUSEMOVE, 0, ventanas._lp(x, y))
        time.sleep(0.15)
        for i in range(2 if doble else 1):
            # ⚠ el juego corre a 20 FPS: un botón apretado menos de un cuadro (50 ms) a veces no lo ve. Se lo deja
            #   apretado 120 ms. El 2.º de un doble clic va como WM_LBUTTONDBLCLK.
            ventanas.u32.PostMessageW(h, 0x0203 if i else ventanas.WM_LBUTTONDOWN, 1, ventanas._lp(x, y))
            sc.exports_sync.boton(True)
            time.sleep(0.12)
            ventanas.u32.PostMessageW(h, ventanas.WM_LBUTTONUP, 0, ventanas._lp(x, y))
            sc.exports_sync.boton(False)
            time.sleep(0.12)

    def mover(self, n, x, y):
        import ventanas
        ventanas.u32.PostMessageW(self.hwnd(n), ventanas.WM_MOUSEMOVE, 0, ventanas._lp(x, y))

    def edits(self, n):
        """Las cajas de texto ocultas del juego (Edit): el juego dibuja su contenido como chat / campos."""
        import ctypes
        import ctypes.wintypes as W
        import ventanas
        res = []

        @ctypes.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
        def cb(h, _):
            c = ctypes.create_unicode_buffer(32)
            ventanas.u32.GetClassNameW(h, c, 32)
            if c.value == "Edit":
                res.append(h)
            return True

        ventanas.u32.EnumChildWindows(self.hwnd(n), cb, 0)
        return res

    def texto(self, n, t, caja=0, enter=False):
        """Escribe en la caja de texto `caja` (0 = la primera Edit) y, si `enter`, la manda."""
        import ventanas
        cajas = self.edits(n)
        destino = cajas[caja] if cajas else self.hwnd(n)
        for ch in t:
            ventanas.u32.PostMessageW(destino, ventanas.WM_CHAR, ord(ch), 1)
            time.sleep(0.02)
        if enter:
            time.sleep(0.3)
            ventanas.u32.PostMessageW(destino, ventanas.WM_KEYDOWN, 0x0D, 0x001C0001)
            ventanas.u32.PostMessageW(destino, ventanas.WM_CHAR, 0x0D, 0x001C0001)
            ventanas.u32.PostMessageW(destino, ventanas.WM_KEYUP, 0x0D, 0xC01C0001)

    def tecla(self, n, nombre, segundos=0.12):
        """Una tecla: por mensaje a la ventana Y por DirectInput (el juego lee el teclado por los dos lados).
        `segundos` = cuánto se la mantiene (para disparar: la fuerza crece mientras se mantiene el espacio)."""
        import ventanas
        sc = self.juegos[n]["script"]
        sc.exports_sync.ventana(self.hwnd(n))
        if nombre in ventanas.TECLAS and segundos <= 0.2:
            ventanas.tecla(self.hwnd(n), nombre)
        if nombre in DIK:
            sc.exports_sync.tecla(DIK[nombre], True)
            time.sleep(segundos)
            sc.exports_sync.tecla(DIK[nombre], False)

    def foto(self, n, ruta):
        import ventanas
        return str(ventanas.foto(self.hwnd(n), ruta))

    def log(self, n):
        return self.juegos[n]["script"].exports_sync.log()

    def lista(self):
        salida = []
        for n, j in self.juegos.items():
            try:
                self.hwnd(n)
                vivo = True
            except KeyError:
                vivo = False
            salida.append({"n": n, "pid": j["pid"], "id": j["id"], "nick": j["nick"], "ventana": vivo})
        return salida

    def cerrar(self, n=None):
        for k in ([n] if n else list(self.juegos)):
            j = self.juegos.pop(k, None)
            if j:
                try:
                    self.frida.kill(j["pid"])
                except Exception:                                       # noqa: BLE001
                    pass


def servir(mesa):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            largo = int(self.headers.get("Content-Length") or 0)
            p = json.loads(self.rfile.read(largo) or b"{}")
            try:
                orden = self.path.strip("/")
                if orden == "abrir":
                    r = mesa.abrir(p["id"], p.get("juego", "gunbound"), p.get("canje"))
                elif orden == "clic":
                    r = mesa.clic(int(p["n"]), int(p["x"]), int(p["y"]), bool(p.get("doble")))
                elif orden == "mover":
                    r = mesa.mover(int(p["n"]), int(p["x"]), int(p["y"]))
                elif orden == "texto":
                    r = mesa.texto(int(p["n"]), p["t"], int(p.get("caja", 0)), bool(p.get("enter")))
                elif orden == "tecla":
                    r = mesa.tecla(int(p["n"]), p["k"], float(p.get("seg", 0.12)))
                elif orden == "foto":
                    r = mesa.foto(int(p["n"]), p["ruta"])
                elif orden == "log":
                    r = mesa.log(int(p["n"]))
                elif orden == "cuenta":
                    r = mesa.juegos[int(p["n"])]["script"].exports_sync.cuenta()
                elif orden == "lista":
                    r = mesa.lista()
                elif orden == "cerrar":
                    r = mesa.cerrar(int(p["n"]) if p.get("n") else None)
                else:
                    raise KeyError(orden)
                cuerpo, codigo = json.dumps({"ok": True, "r": r}), 200
            except Exception as e:                                      # noqa: BLE001
                cuerpo, codigo = json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500
            b = cuerpo.encode()
            self.send_response(codigo)
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

    ThreadingHTTPServer(("127.0.0.1", PUERTO), H).serve_forever()


def pedir(orden, **datos):
    req = urllib.request.Request(f"http://127.0.0.1:{PUERTO}/{orden}", data=json.dumps(datos).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("--canje", default="http://127.0.0.1:8371/canje")
        ap.add_argument("--cliente", default=r"D:\Gunbound\Cliente-Enenos")
        ap.add_argument("--ventana", default="1024x768")
        o = ap.parse_args()
        print(f"mesa en http://127.0.0.1:{PUERTO}", flush=True)
        servir(Mesa(o.canje, o.cliente, o.ventana))
    else:
        orden, resto = a[0], a[1:]
        if orden == "abrir":
            # abrir <id> [juego] [url del canje]   (prueba: abrir 90000003 gunbound-prueba http://127.0.0.1:9371/canje)
            r = pedir("abrir", id=int(resto[0]), juego=resto[1] if len(resto) > 1 else "gunbound",
                      canje=resto[2] if len(resto) > 2 else None)
        elif orden in ("clic", "doble"):
            r = pedir("clic", n=resto[0], x=resto[1], y=resto[2], doble=orden == "doble")
        elif orden == "mover":
            r = pedir("mover", n=resto[0], x=resto[1], y=resto[2])
        elif orden in ("texto", "decir"):
            r = pedir("texto", n=resto[0], t=resto[1], caja=resto[2] if len(resto) > 2 else 0, enter=orden == "decir")
        elif orden == "tecla":
            r = pedir("tecla", n=resto[0], k=resto[1], seg=float(resto[2]) if len(resto) > 2 else 0.12)
        elif orden == "foto":
            ruta = resto[1] if len(resto) > 1 else str(RAIZ / "estado" / "fotos" / f"mesa_{resto[0]}.png")
            Path(ruta).parent.mkdir(parents=True, exist_ok=True)
            r = pedir("foto", n=resto[0], ruta=ruta)
        elif orden in ("log", "cuenta"):
            r = pedir(orden, n=resto[0])
        elif orden == "lista":
            r = pedir("lista")
        elif orden == "cerrar":
            r = pedir("cerrar", n=resto[0] if resto else None)
        else:
            raise SystemExit(__doc__)
        print(json.dumps(r, ensure_ascii=False, indent=1))
