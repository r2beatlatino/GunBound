# El mapa del cliente — viento, rangos, bandera, GM y la red vieja

> 16-nov-2026. Lectura estática de `GunBound.exe` v179 (y de `DualSoft.dll`), más `graphics.xfs` decodificado.
> El detalle con direcciones está en `investigacion/`; acá van las respuestas cortas. **MEDIDO** = leído en el
> código o en los datos del cliente; **INFERIDO** = sacado de servers viejos o de nombres.

| tema | en detalle |
|---|---|
| viento, turnos, sincronía P2P, plazos de red | `investigacion/PARTIDA_VIENTO_Y_RED.md` |
| rangos, GP, bandera, nick/género, la tabla de mensajes | `investigacion/CUENTA_RANGOS_BANDERA_OPCODES.md` (+ `rangos_rank2.png`, `paises_*.png`) |
| comandos «/», GM, mensajes raros, lo que hacía DualSoft | `investigacion/GM_COMANDOS_Y_EXTRAS.md` |
| ★ cuánto GP y oro paga cada partida (lo calcula el CLIENTE; formato del 0x4412, topes) | `investigacion/PAGOS_GP_Y_ORO.md` (Codex) |
| la tienda: formato de `avatar.xfs`, precios y permisos de moneda (todo en oro) | `investigacion/TIENDA_AVATAR_XFS.md` (Codex) |

## El viento — ya anda, y no es del server (MEDIDO)

- El server sólo pone la **semilla** del 0x3432. Con ella cada cliente arma lo mismo: el viento inicial, los 12
  climas del mapa y una tabla de 1024 azares compartida.
- Cada vuelta de turnos, **el que arma el turno** saca viento nuevo (fuerza 0..26, ángulo 0..359) con `rand()` y lo
  reparte por P2P dentro del mensaje de turno (0xC300). Por eso las dos ventanas muestran el mismo viento.
- Opción de sala bit 0x10000: viento desde el arranque + variación ±1 por turno. Muerte súbita, Thor e ítems:
  también los resuelven los clientes.
- ⇒ No hay nada que hacer en el server para el viento.

## Rangos — «pollito» es el 19 (MEDIDO)

- Van **4 WORD** de rango (0x1012 desde +27, 0x200E y fichas de sala): 1.º total (permisos), 2.º temporada (no se
  dibuja), **3.º el ícono que se ve**, **4.º el país** (la bandera, dibujada arriba del ícono).
- Ícono = cuadro `valor + 5` de `rank2.img`: **19 pollito** · 18 madera … 0 rubí · −1 diamante · −2/−3 dragón
  azul/rojo · −4 dragón plateado (el mejor) · **20 GM** (el cliente le saca el límite de flood y le da permisos).
  Del 21 en adelante hay íconos especiales (VIP, estrellas, coronas) que el cliente no trata distinto.
- ✅ 16-nov: el server calcula el rango del GP (`servidor/rangos.py`, cortes de TorHammer) y lo manda con el país.
  **Medido con el juego**: subiéndole el GP a una cuenta y volviendo a entrar, el ícono progresa de pollito a dragón
  plateado con la bandera AR (`investigacion/escalera_de_rangos_medida.png`). Antes iba 0 ⇒ varita de rubí con «?».
- ⚠ **El cliente no tiene tabla automática**: el original la corría el server de noche (BatchGIS). Acá se
  recalcula sola cada vez que entra (`/gp` desde el chat de GM, mañana el panel).
- GP por rango (INFERIDO, TorHammer): 0–1099 pollito, 1100 madera, 1200, 1500, 1800, 2300, 2800, 3500, 4200, 5100,
  6000; de ahí para arriba el original iba **por puesto** (#1 dragón plateado, #2–5 rojo, #6–25 azul, después por %).
- El GP y el oro se ven en «Mi info» y salen **sólo** del 0x1012 (+61 GP, +69 oro; +37 TRank, +49 CRank): ✅ ya van;
  el cambio se ve recién al volver a entrar.

## La bandera «?» — es un país, no un ítem (MEDIDO)

`nationcode.img`: 246 códigos de dos letras, **0 = «?»**, en el orden de la tabla `country_reference` de Softnyx:
9 AR · 28 BR · 39 CL · 131 MX · 157 PE · 207 US · 208 UY · 212 VE. Va en el 4.º WORD de rango.

## Nick y género — el cliente no tiene pantalla para eso (MEDIDO, por barrido)

Ninguna de sus 231 clases crea nick ni elige género (`NameChangeDlg` es el título de la SALA). Sigue siendo cosa
nuestra: `/nombre`, `/genero` o el launcher; se ve al volver a entrar.

## GM y comandos «/» (MEDIDO)

- El cliente atiende solo: `/help`, susurros (`/m`, `/to`), `/kick <nick>` (de la LLAVE de la sala → 0x3150),
  `/go`, `/iniciar` (→ 0x3430), `/quit`, `/ipconfig`, `/clear`, más escondidos (espectador, móvil por número,
  `/qz` con rango 19). **Cualquier otro «/…» va al server por 0x5100** (ahí viven `/practica`, `/aviso`, `/dar`…).
- El GM es el **rango 20**; no hay bit de GM en «funciones». No hay menús de GM en el cliente: echar, silenciar y
  avisos son del server, con lo que el cliente ya trae:
  - **0x1FFF** `[motivo]`: corta y muestra el cartel (echar). **0x1FFA** `[segundos]`: aviso de mantenimiento.
  - **0x5101** con prefijo de color: `!` sistema, `@` rojo, `#` naranja, `$` verde, `%` azul, `^` violeta.
- ⚠ El chat de SALA viaja P2P: un mute del server sólo calla el lobby.
- Al sacar DualSoft se perdieron mascotas, emotes Alt+1..0, el aviso de turno, color de gremio y su antitrampa
  (que además mandaba el HWID a un server de ellos). Los «BONUS GP» 0x7A31/0x7A32 eran sólo un cartel.
- Corrección: los 0x5001/0x5013/0x7000…/0x8014 que creíamos mensajes son **códigos de error** (el switch de
  0x445D70 es sobre el resultado, no sobre el comando). 0xF000 = «Double Logined».

## La red vieja — por qué se colgaba o echaba gente

| qué | dónde | qué hace | estado |
|---|---|---|---|
| paso al túnel | 0x44D8FD | 20 s sin noticias ⇒ túnel para siempre | ✅ parche 6 (2 s) + 7 (ping 1 s) |
| vigilante de reloj | 0x416C60 | 11 intervalos seguidos fuera de 350–650 ms ⇒ **cierra con código 9 («hack»)** | ⚠ el falso positivo clásico con la PC trabada; candidato a parche |
| vigilante de votos de la llave | 0x4D8B88 | cada 30 s da por votado al que falta; al 6.º manda **0x4000** (echar al mudo) | ⚠ el server todavía no atiende 0x4000 |
| reenvío P2P | 0x44EAC0 | sin límite de intentos | candidato a parche |
| esperas sin plazo | 0xC300/0xC306/0xC40B, 0x4413 | esperan para siempre | se cuelga si el otro no contesta |
| TCP con el server | — | el cliente no manda nada periódico; sólo se entera de un corte por FD_CLOSE | ✅ del lado nuestro, ver abajo |
| anti-flood del chat | — | >5 en 10 s: aviso; la 2.ª vez cierra (código 0x1A) | del cliente |

✅ **Arreglado el 16-nov en el server:** cortaba a los 10 min de silencio TCP, y jugando por P2P directo el cliente
no manda nada por TCP ⇒ una partida larga echaba a todos. Ahora en partida no se corta por silencio y el socket
lleva el keepalive del sistema (descubre una PC caída en ~2 min). `pruebas/probar_silencio.py`, con su control.
