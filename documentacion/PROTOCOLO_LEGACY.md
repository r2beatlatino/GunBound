# El protocolo del cliente GunBound Legacy (v179) — lo MEDIDO

> Todo lo de acá se sacó de dos lados: el **lector** del mensaje en `GunBound.exe` (la dirección va al lado) o una
> **traza** con el juego de verdad (`GB_TRAZA=1`, 16-nov-2026, dos clientes por la mesa). Lo que no está medido
> dice ⚠. El formato del Serv2 / del emulador de jglim NO vale para este cliente salvo donde se dice.

## El sobre

`[largo total WORD][secuencia WORD][comando WORD][cuerpo]`. La secuencia la comprueba el cliente en lo que recibe:
`((total_mandado_por_esa_conexión × 0x43FD) & 0xFFFF) − 0x53FD`. El broker manda su primer mensaje con 0xCBEB fijo.
`rtc` = un WORD de resultado al principio del cuerpo (0 = bien).

Cifrado: AES-128 ECB. Estático (clave fija) sólo para el usuario del login. Dinámico: clave = SHA-0 de
usuario + contraseña + ficha (4 bytes del 0x1001), truncado a 16, DWORDs dados vuelta; cada 12 bytes de datos llevan
4 de control = 0x8631607E + comando. Comprobado con un 0x3432 real (pruebas/probar_basicos.py).

## Entrar

| | formato | dónde |
|---|---|---|
| argumento del exe | AES(clave `FAEE85F2…`) de usuario 16 + contraseña 16 + 16 ceros, en HEX mayúscula; es TODA la línea de comandos (sin la ruta del exe adelante: con ella el juego se cierra) | medido (laboratorio de Codex + mesa) |
| broker 0x1102 | `00 00 01` cantidad · por mundo: lugar,0,0 · largo+nombre · largo+descripción · IP(4) · puerto BE · ocupación BE ×2 · cupo BE · **`FB 64 00`** · habilitado | sin los 3 bytes sale «In Maintenance» |
| login 0x1010 | [0:16] usuario (estático) · [16:32] otro bloque (no se usa) · [32:] dinámico: contraseña [0:12], versión [0x14:0x16] = 179 | traza |
| 0x1012 | 89 bytes: +2 único(4) · +6 nick(12) · **+18 género** (0 = varón) · +19 gremio(8) · +27 rango · +29 rango temp. · ceros; y cifrado: funciones, %GP, %oro, cash, funciones, 0 | lector 0x004F1FDE |
| 0x2001 en la pantalla de servidores | sólo «entraste»: el cliente mira el estado y pide 0x6000 y 0x1090. **La lista que trae se descarta** | lector 0x4F27BF |
| la lista del canal | se arma con **0x200E**, uno por jugador, ficha de 30 bytes: lugar · nick(12) · género · avatar(8) · rango · rango temp. · 4 ceros. Se manda al llegar el **primer 0x6004 vacío** (lo último que pide el lobby al armarse) e incluye al propio jugador (sin él, su chat sale sin nombre) | mesa, dos clientes |
| 0x1090 → 0x1091 | `00 00` · móvil 1 · móvil 2 · 6 ceros. Sin respuesta, no pasa al lobby | Codex |
| 0x6000 → 0x6001 | **sin cifrar**: rtc · cantidad · por pieza 14 bytes (serie 4 · pieza 4 · puesta 1 · 5 ceros). Cifrado → se cae | Codex |

## El lobby y las salas

| | formato | dónde |
|---|---|---|
| 0x2103 (lista) | rtc · cantidad (byte) · 0 · hasta 9 renglones: id WORD · largo+nombre · mapa · ajustes(4) · **2 bytes** · jugadores · cupo · jugando · con clave | lector 0x4CB55A (sin los 2 bytes: «FULL 0/0») |
| 0x2120 (crear) | largo+título · ajustes(4) · clave(4) · cupo | traza |
| 0x2111 (entrar) | rtc · 00 01 · id WORD · largo+nombre · mapa · ajustes(4) · 8×FF · cupo · cantidad · fichas de 49 | lector 0x4CB8C5 |
| ficha de ocupante | casilla · nick(12) · **género** · IP · puerto · IP · puerto · móvil 1 · móvil 2 · equipo · **listo** · avatar(8) · 4 WORD (rangos; +5 a los 3 primeros) · cantidad de piezas extra WORD + DWORD c/u · **1 byte** | lector 0x4CBA60 |
| 0x3010 (llegó alguien, al resto) | la misma ficha **sin «listo» ni el byte final** (47) | lector 0x4102E0 |
| ajustes de la sala | 4 bytes del cliente; [2] = modo (00 solo · 44 score · 08 tag · 0C jewel), bit 0 = lado | traza |
| «Ready» | viaja entre los clientes por P2P; el del invitado se apaga solo si no hay conexión P2P con el anfitrión | mesa |

## La partida

| | formato | dónde |
|---|---|---|
| 0x3430 (empezar) | lo manda la llave: 4 bytes (semilla) | traza |
| 0x3432 (cifrado) | ajustes(4) · mapa · cantidad WORD · 22 por jugador (casilla · nick 12 · equipo · móvil 1 · móvil 2 · X · Y · turno) · FFFF · semilla(4) · 6 × (2 + 0) | lector 0x004ECDAB + partida jugada |
| túnel 0x4500 (manda) | `01 00` · **casilla destino** · datagrama (empieza con su largo: WORD & 0x3FFF) | emisor 0x44D530 |
| túnel 0x4501 (recibe) | **casilla de quien manda** · datagrama. Con el byte de destino de más, el que recibe se CIERRA | lector 0x4106DC → 0x44D4C0 |
| UDP directo | cada cliente escucha en 8363. Bucle por compañero (0x44D89D): ping si hace 5 s que no le manda nada; si hace **20 s** que no recibe nada, 0x44D5E0 lo pasa al túnel para siempre (no lo corta). Con el original, si nadie empezaba la partida a los ~30 s de eso, el invitado se iba de la sala | lector + mesa |

★ El cliente de Eñeños baja esos tiempos a **2 s** y ping cada **1 s** (parches 6 y 7): UDP directo primero y, si no
anda, el túnel enseguida. Por omisión el server anuncia la IP real (`GB_P2P=directo`, como el original); para
probar varios clientes en UNA PC va `GB_P2P=tunel` (dirección vacía: todo por el túnel). ⚠ El directo entre casas
distintas, sin medir todavía.

## Lo que falta medir (ver PENDIENTE.md)

- El cobro del premio al terminar (0x4412: el server no acredita oro ni GP todavía).
- El paginado de salas (más de 9), el rechazo de entrada a una sala (hoy va un aviso por chat), regalos.
- `GB_P2P=directo` con jugadores de casas distintas.
