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

Los parches 1 a 3 son de Codex (laboratorio, 13-nov); 4 y 5, de esta sesión.

## La ventana

La trae Legacy con **DxWnd** (`ddraw.dll` + `dxwnd.dll` + `dxwnd.dxw`): sin él el juego no arranca. DxWnd escala:
el juego dibuja en 800×600 lógicos y la ventana mide 1600×1032; los clics llegan escalados (medido).
`InterfaceMode` {0} y {1} en el registro: en la partida se ven iguales (comparado el 16-nov).

## Cómo lee el mouse y el teclado (importa para probar sin tocar la PC)

- La POSICIÓN y los botones, por mensajes de la ventana (WM_MOUSEMOVE / WM_LBUTTONDOWN…), pero sólo si cree que su
  ventana es la de adelante (`GetForegroundWindow`). El juego corre a 20 FPS: un clic de menos de 50 ms se pierde.
- El TECLADO del juego (disparar con espacio), por DirectInput8 (`dinput8.dll`, cargada a mano).
- El texto (chat, título de sala) va a una caja `Edit` OCULTA: la que está activa es la segunda hija de la ventana.
- ⚠ El juego llama a `SetCursorPos` (mueve el cursor de verdad) cuando cree que tiene el foco: la mesa lo anula.
