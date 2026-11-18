# El cliente de Eñeños

Se arma en la PC, a partir del GunBound Legacy original, sin tocarlo:

```bash
python herramientas/parchar_cliente.py                 # C:\GunBound-Legacy → D:\Gunbound\Cliente-Enenos
python herramientas/parchar_cliente.py --comprobar     # qué parches tiene
```

⛔ El cliente no va al repo (es de Softnyx/Legacy). Para repartirlo a los jugadores va por el servidor de parches de
Eñeños, como el de R2Beat.

## Los parches (todos medidos)

| # | dónde | qué | por qué |
|---|---|---|---|
| 1 | GunBound.exe 0x4FE0C8 | se borra el import de `DualSoft.dll` | es la «protección» de Legacy: autentica contra SU server (15.204.128.129), HWID, mascotas y bonos. Sin ella el juego habla el protocolo de siempre |
| 2 | 5 × `push 80000002` | HKLM → HKCU | no hace falta ser administrador; cada usuario de Windows tiene lo suyo |
| 3 | 0x1CE081 | `softnyx\Legacy` → `softnyx\Enenos` | no pisa ni lee la configuración del Legacy instalado |
| 4 | 0x40C3EC (6 NOP) | «¿ya hay uno abierto?» → seguir | varias instancias (probar con varios jugadores en una PC) |
| 5 | dxwnd.dll +0x4202A (`jne`→`jmp`) | DxWnd deja enganchar más de un juego | sin esto la 2.ª instancia la cierra DxWnd (`exit(0)`, medido con Frida) |
| 6 | GunBound.exe 0x4D8FD (`add eax, 4E20` → `7D0`) | el P2P pasa al TÚNEL a los **2 s** sin noticias del compañero (era 20 s) | pedido de Benja: UDP directo primero, túnel rápido. El manejador (0x44D5E0) sólo prende «este va por túnel» y reenvía lo pendiente: no corta a nadie |
| 7 | GunBound.exe 0x4D8CF (`add edx, 1388` → `3E8`) | ping al compañero cada **1 s** (era 5 s) | con plazo de 2 s y pings cada 5, un directo sano pero callado pasaría al túnel |
| 8 | GunBound.exe 0xAB5EE (`push 6`→`push 2`) y 0xCF59E (`push 1`→`push 2`) | del logo DIRECTO al selector de servidor | Benja: «3 o 4 transiciones; lo ideal, una sola con arte original». Era logo → logo 2 → título → selector |
| 9 | GunBound.exe 0x515C07 (`push 57AF98` → `call 55ED00`) + un cave de 180 bytes en 0x55ED00 | el **medidor de tiro** se elige: DWORD `PlayBackStyle` de HKCU\Software\softnyx\Enenos → 1 `play_back_blu1.img` (Milimétrico), 2 `play_back_blu2.img` (Métrico), otro o sin valor `play_back_blue.img` (Normal) | el exe tenía el Normal fijo; en Legacy lo cambiaba DualSoft.dll (y una copia en `lua15.dll`, que en nuestro cliente **no se carga nunca**: medido 18-nov). El cave está en el relleno de ceros del final del código viejo (nada apunta ahí) y guarda todos los registros. **Medido 18-nov** con Frida en el cargador de imágenes (0x52AB20, id 0x1C20) en una práctica: 2 → blu2, 1 → blu1, 0 → blue, sin valor → blue (`investigacion/medidor_de_tiro_medido.png`). Lo pidió la sesión del launcher para «Opciones del juego» |

**Los datos que cambia** (además del exe): `graphics.xfs` con el arte ORIGINAL de GunBound WC (GIS 557,
`herramientas/arte_original/`, rearmado con `herramientas/rearmar_xfs.py`): la única pantalla de arranque es el
título de World Champion, y vuelven el fondo de carga de partida y el del selector («WORLD LIST»). `avatar.xfs`:
la tienda SÓLO ORO (`herramientas/avatar_xfs.py`). Medido con el juego (16-nov): una pantalla y al selector
(`investigacion/arranque_una_pantalla_medido.png`), «LOADING» original al entrar a una partida, «Gold only» en la
tienda. ⚠ Quedan con arte de Legacy el fondo de la SALA («OPCIONES DE SALA») y el logo del lobby: otros recursos.

Los parches 1 a 3 son de Codex (laboratorio, 13-nov); 4 a 7, del 16-nov; el 8, de Codex (16-nov).
Medido con 6 y 7 (dos clientes, una PC): entró a la sala 02:59:10 → primer túnel 02:59:12 → la partida empezó al
primer «Start»; turnos y disparos bien, 42 mensajes por el túnel, nadie se fue.

## La ventana

La trae Legacy con **DxWnd** (`ddraw.dll` + `dxwnd.dll` + `dxwnd.dxw`): sin él el juego no arranca. DxWnd escala:
el juego dibuja en 800×600 lógicos y la ventana mide 1600×1032; los clics llegan escalados (medido).
⚠ **El registro tiene TIPOS**: `InterfaceMode`, `Background`, `ShootingMode`, `Effect3D`, `ShowTurn`… son binarios de
UN byte (PowerShell los muestra como `{1}`, pero NO son ese texto). Escritos como texto, el juego lee el `{` (0x7B)
como modo de interfaz y dibuja el HUD MEZCLADO (panel WEAPON clásico vacío con el selector redondo encima; medido el
16-nov, lo vio Benja). Con el byte, el HUD sale como en el laboratorio de Codex. `ScreenDetail` = `1600x1200`
(lo que trae el `dxwnd.dxw`).

## Cómo lee el mouse y el teclado (importa para probar sin tocar la PC)

- La POSICIÓN y los botones, por mensajes de la ventana (WM_MOUSEMOVE / WM_LBUTTONDOWN…), pero sólo si cree que su
  ventana es la de adelante (`GetForegroundWindow`). El juego corre a 20 FPS: un clic de menos de 50 ms se pierde.
- El TECLADO del juego (disparar con espacio), por DirectInput8 (`dinput8.dll`, cargada a mano).
- El texto (chat, título de sala) va a una caja `Edit` OCULTA: la que está activa es la segunda hija de la ventana.
- ⚠ El juego llama a `SetCursorPos` (mueve el cursor de verdad) cuando cree que tiene el foco: la mesa lo anula.
