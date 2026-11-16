# -*- coding: utf-8 -*-
"""ventanas — ver y manejar los clientes abiertos SIN tocar el mouse ni el teclado de la PC.

    python herramientas/ventanas.py lista
    python herramientas/ventanas.py foto [carpeta]              una foto por ventana (PrintWindow: no la tapa nada)
    python herramientas/ventanas.py clic <pid> <x> <y>          clic en coordenadas DEL CLIENTE (las de la foto)
    python herramientas/ventanas.py texto <pid> "hola /ayuda"   escribe (WM_CHAR)
    python herramientas/ventanas.py tecla <pid> enter|esc|tab
    python herramientas/ventanas.py ordenar                     las acomoda en mosaico

Los clics y las teclas van como MENSAJES a la ventana (PostMessage): el cursor de verdad no se mueve.
⚠ Si el juego leyera el mouse por DirectInput, esto no le llegaría: se mide con la foto de después.
"""
import ctypes
import ctypes.wintypes as W
import sys
import time
from pathlib import Path

u32 = ctypes.windll.user32
g32 = ctypes.windll.gdi32
CLASE = "Softnyx"
WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP = 0x0200, 0x0201, 0x0202
WM_KEYDOWN, WM_KEYUP, WM_CHAR = 0x0100, 0x0101, 0x0102
TECLAS = {"enter": 0x0D, "esc": 0x1B, "tab": 0x09, "espacio": 0x20, "izq": 0x25, "arriba": 0x26, "der": 0x27,
          "abajo": 0x28, "f1": 0x70, "f5": 0x74, "borrar": 0x08}


def ventanas():
    """-> [(hwnd, pid, título, (x, y, ancho, alto))] de los GunBound visibles."""
    res = []

    @ctypes.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    def cb(h, _):
        c = ctypes.create_unicode_buffer(64)
        u32.GetClassNameW(h, c, 64)
        if c.value == CLASE and u32.IsWindowVisible(h):
            p = W.DWORD()
            u32.GetWindowThreadProcessId(h, ctypes.byref(p))
            t = ctypes.create_unicode_buffer(128)
            u32.GetWindowTextW(h, t, 128)
            r = W.RECT()
            u32.GetWindowRect(h, ctypes.byref(r))
            res.append((h, p.value, t.value, (r.left, r.top, r.right - r.left, r.bottom - r.top)))
        return True

    u32.EnumWindows(cb, 0)
    return sorted(res, key=lambda v: v[1])


def de_pid(pid):
    for v in ventanas():
        if v[1] == int(pid):
            return v[0]
    raise SystemExit(f"no hay ventana del PID {pid}")


def foto(hwnd, ruta):
    from PIL import Image

    class BIH(ctypes.Structure):
        _fields_ = [("biSize", W.DWORD), ("biWidth", W.LONG), ("biHeight", W.LONG), ("biPlanes", W.WORD),
                    ("biBitCount", W.WORD), ("biCompression", W.DWORD), ("biSizeImage", W.DWORD),
                    ("a", W.LONG), ("b", W.LONG), ("c", W.DWORD), ("d", W.DWORD)]

    r = W.RECT()
    u32.GetClientRect(hwnd, ctypes.byref(r))
    w, h = r.right, r.bottom
    hdc = u32.GetDC(hwnd)
    mdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, h)
    g32.SelectObject(mdc, bmp)
    u32.PrintWindow(hwnd, mdc, 3)
    bi = BIH(ctypes.sizeof(BIH), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 4)
    g32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB").save(ruta)
    g32.DeleteObject(bmp)
    g32.DeleteDC(mdc)
    u32.ReleaseDC(hwnd, hdc)
    return ruta


def _lp(x, y):
    return (int(y) << 16) | (int(x) & 0xFFFF)


def clic(hwnd, x, y, doble=False):
    u32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, _lp(x, y))
    time.sleep(0.05)
    for _ in range(2 if doble else 1):
        u32.PostMessageW(hwnd, WM_LBUTTONDOWN, 1, _lp(x, y))
        time.sleep(0.06)
        u32.PostMessageW(hwnd, WM_LBUTTONUP, 0, _lp(x, y))
        time.sleep(0.06)


def texto(hwnd, t):
    for ch in t:
        u32.PostMessageW(hwnd, WM_CHAR, ord(ch), 1)
        time.sleep(0.02)


def tecla(hwnd, nombre):
    vk = TECLAS[nombre]
    u32.PostMessageW(hwnd, WM_KEYDOWN, vk, 1)
    time.sleep(0.05)
    if vk == 0x0D:
        u32.PostMessageW(hwnd, WM_CHAR, 0x0D, 1)
    u32.PostMessageW(hwnd, WM_KEYUP, vk, 0xC0000001)


def ordenar():
    vs = ventanas()
    for i, (h, _, _, (x, y, w, alto)) in enumerate(vs):
        u32.SetWindowPos(h, 0, 20 + (i % 2) * (w // 2), 20 + (i // 2) * (alto // 3), 0, 0, 0x0001 | 0x0004 | 0x0010)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "lista":
        for v in ventanas():
            print(*v)
    elif a[0] == "foto":
        dest = Path(a[1] if len(a) > 1 else ".")
        dest.mkdir(parents=True, exist_ok=True)
        for h, pid, _, _ in ventanas():
            print(foto(h, dest / f"gb_{pid}.png"))
    elif a[0] == "clic":
        clic(de_pid(a[1]), a[2], a[3], doble="--doble" in a)
    elif a[0] == "texto":
        texto(de_pid(a[1]), a[2])
    elif a[0] == "tecla":
        tecla(de_pid(a[1]), a[2])
    elif a[0] == "ordenar":
        ordenar()
