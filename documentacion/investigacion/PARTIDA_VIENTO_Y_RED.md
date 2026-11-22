# La partida del GunBound Legacy v179 — viento, sincronía y plazos de red

> Lectura estática de `GunBound.exe` (SHA256 d03e0afe…), 16-nov-2026. Nada se ejecutó.
> **MEDIDO** = lo dice el código en esa dirección. **INFERIDO** = deducido (nombre de log, forma del código, emulador).
> Scripts: `scratchpad\gb\partida\` (`v.py` = ver código con cadenas; `arbol.py` = sacar el árbol de opcodes).
> ⚠ La función de log `0x4AAAB0` es un `ret` vacío: los mensajes de depuración están en el exe pero **no salen a ningún lado**.

---

## 0 · Lo más importante, en cinco renglones

1. **El viento lo decide la llave (anfitrión), no el server.** Sale de `rand()` del C local cada vuelta de turnos y viaja por P2P
   adentro del mensaje de turno `0xC300`. El server sólo pone la **semilla** del `0x3432`, que fija el clima de arranque, la lista de climas y una tabla de 1024 azares que todos comparten.
2. **La partida la sincroniza la llave con "votos"**: cada cliente manda `0xC302` (voto) y la llave, cuando tiene todos, manda `0xC303`. Si alguien no vota,
   **la llave espera 30 s, lo da por votado y sigue**; a la 6.ª vez manda **`0x4000 [casilla]` al server** (pedido de echarlo). **Hoy el server no atiende el `0x4000`.**
3. **El cliente no le manda nada periódico al server de juego** (no tiene keepalive TCP). Durante la partida todo va por P2P → con el `timeout=600` de
   `servidor/mundo.py:79` **una partida de más de 10 min corta a los que no tunelan.**
4. Hay un **vigilante de reloj** (`0x416C60`) que **cierra el juego con el código 9 ("hack")** si 11 veces seguidas el tic no cae entre 350 y 650 ms:
   **un candidato fuerte a los "falsos positivos"** con la PC trabada.
5. Hay **esperas sin plazo**: los mensajes "retenidos" (`0xC300`/`0xC306`/`0xC40B`) hasta que termina la animación local, y el `0x4413` al final.

---

## 1 · El viento y el "clima"

### 1.1 Lo que pone el server (MEDIDO)

| qué | dónde | detalle |
|---|---|---|
| semilla `0x3432` (DWORD al final) | lector `0x4ED61E` → `0x423B70(semilla)` | también la guarda en `0x8701C8` |
| marca de evento `0x3432` (WORD antes de la semilla) | `0x4ED4B4` | `FFFF` = ninguno; otro valor → `0x42AC60(evento)` ("Current Event is %d") |
| opciones de la sala (DWORD) | `[base+0x1FEB8]` (sale de los 4 bytes de ajustes) | bit `0x10000` = **viento al arranque + viento que varía turno a turno** |
| muerte súbita | `[base+0x240EF]` = activa · `[base+0x240F8]` = turno límite | aviso a 10 turnos del límite (`0x4EACBA`, texto 0x261) |

### 1.2 Lo que hace cada cliente con la semilla (MEDIDO, `0x423B70`)

Un generador propio, idéntico en todos: `x' = x·0x343FD + 0x5809315`; `estado += (x'·0x61 + 0x61) mod 1000001`.

| paso | resultado |
|---|---|
| lista de 12 climas `[0x26AEC + i·8]` | sale de los climas que **el mapa** tiene definidos (`[0x2C478…]`, por mapa y lado) y se baraja 31 veces |
| si opción `0x10000` | fuerza inicial = azar mod 26 · ángulo = azar mod `[0x5CF1D8]` (360, se carga en runtime) |
| si no | fuerza 0, ángulo 0 |
| `[0x26B64]` / `[0x26B6C]` | (azar & 15) − 8 / (azar mod 80) − 40 → fuerza y giro para los climas "de viento" (tipo 3) |
| tabla de 1024 azares `[0x26E28]` | la usan todos para cosas que tienen que salir iguales (tornado, rayo, fuerza: `0x424D10(k)`) |

### 1.3 Cada turno (MEDIDO, `0x423150`, lo arma quien manda el turno)

- `T` = número de turno `[0x28E50]`, `N` = jugadores `[0x25EC4]`. Una "vuelta" = `N` turnos. El clima de la vuelta es `lista[(T/N) & 7]`.
- Tipo 3 al empezar la vuelta: fuerza = `[0x26B64]`, ángulo += `[0x26B6C]` (mod 360).
- **Antes de cada vuelta nueva** (`(T+1) mod N == 0`): fuerza/giro nuevos con **`rand()` del C** (`0x54352A`): fuerza `rand()%27` (0..26), giro `rand()%180`. **Esto no es determinista: lo decide el que arma el turno.**
- Con la opción `0x10000`: fuerza += `{-1,0,1,0,1,0,-1,0}[T&7]` (tabla `0x5CE110`), recortada a **0..26**.
- Tipos 0/1/2 = fuerza / tornado / rayo: posición y ancho salen de la tabla compartida y de los rangos del mapa.

**Rango del viento (MEDIDO): fuerza 0..26 · ángulo 0..359.** El "12" que se vio está adentro.

### 1.4 Cómo viaja (MEDIDO)

`0xC300` "UDP_TURN" (armado `0x4E6455`, leído `0x4D210C` → `0x4EAB60` → `0x422B10`):

```
[casilla del turno][turno WORD][bloque de clima 32 bytes]
bloque: fuerza(1, con signo) · ángulo(WORD) · fuerza-de-vuelta(1) · giro(1) · ? · FF|(ancho,x) fuerza · FF|(…) tornado · FF|(…) rayo · …
```

**Quién lo manda (INFERIDO fuerte):** lo arma `0x4E5490` (que elige el turno). Lo corre cada cliente cuando le llega el `0xC303` tipo 15 (fin de turno),
pero tiene dos comparaciones de variables cifradas (`0x4E5D20`, `0x4E5DFB`) que dejan pasar a uno solo. Por la arquitectura (la llave junta votos y
reparte), **ese uno es la llave**. ⚠ Falta confirmar en vivo cuál de las variables `0x1A634/0x1A638/0x1A640/0x1A644` es "yo" y cuál "la llave"
(`0x1A634` = mi casilla y `0x1A640` = la llave están MEDIDAS en `0x4D119F` y `0x426E50`).

### 1.5 Lo demás

| cosa | quién decide | evidencia |
|---|---|---|
| orden inicial | **el server** (WORD "turno" por jugador en el `0x3432`) | lector `0x4ED449` lo guarda en `[0x2619E + i·2]` — MEDIDO |
| orden después | cada cliente con los "delays": el que dispara manda su delay en `0xC301` (`0x4D24D3`, WORD); se suma a su casilla (`0x416990`) y gana el menor | MEDIDO el suma; el "menor gana" es INFERIDO (`0x4E5490`, log "%d slot used time is %d") |
| tiempo del turno | 400 tics = **20 s** (20 tics/s × 20) puesto en `[+0x1304]` al elegir turno (`0x4E6272`) | MEDIDO el valor; qué pasa al vencer: INFERIDO (pasa turno con `0xC306`) |
| muerte súbita | la llave, con `0xC305` cuando `T ≥ [0x240F8]` y está activa (`0x4E63E2`) | MEDIDO el envío; el nombre es INFERIDO |
| Thor / satélite | cálculo local en cada cliente al resolver el disparo (`0x450C10`, "ThorSS target") | INFERIDO (no viaja nada propio) |
| ítems | el que los usa los manda por P2P (`0xC400/0xC401/0xC409` salen del código de armas `0x466ED2`, `0x493339`); las cajas que caen usan la tabla compartida | INFERIDO |
| eventos (`0x3432`) | el server, con la marca WORD | MEDIDO (`0x4ED4C0`) |

---

## 2 · Cómo se sincroniza la partida

### 2.1 La capa de transporte P2P (MEDIDO, `CCommP2P`, `0x44D860`)

Cada datagrama: `[WORD tipo(2 bits)|largo(14)][secuencia 1 byte][suma 1 byte][cuerpo]`.

| tipo (bits altos) | qué es | qué hace al recibir |
|---|---|---|
| `00` | control: `3` = acuse, `4` = acuse de un reenviado | borra el pendiente y mide el RTT (`0x44EB40`) |
| `01` (`0x4000`) | `0x4002` = ping (sólo refresca el reloj) · `0x4004` = paquete reenviado por otro (el 1.er byte es la casilla de origen) | contesta `4` |
| `10` (`0x8000`) | sin garantía | a la cola (`0x44E9C0`) |
| `11` (`0xC000`) | con garantía | ventana de 128 secuencias (`0x44E370`); siempre contesta `3` |

- La suma de control (byte 3) se comprueba en `0x44DAAA`; si no da, **se descarta en silencio**.
- **El bit alto del código de juego decide la garantía** (`0x44CCA5`): `0x8xxx/0xCxxx/0xFxxx` van con garantía.
- Un mensaje "a todos" (`casilla −1`, `0x44CC80`) **también se entrega a uno mismo** (bucle local `0x44CCF0`).

### 2.2 Los mensajes de juego por P2P (MEDIDO el árbol `0x4D104B` + el previo global `0x42643D`)

| código | nombre / función | evidencia |
|---|---|---|
| `0x0003` | aviso "X está con lag" (texto 0x260) | lo manda la llave cada 10 s (`0x4D8D0F`) |
| `0x0004` | aviso "X fue sacado" (texto 0x282) | lo manda la llave al 6.º vencimiento (`0x4D8CBD`) |
| `0x0307` | dispara un voto `0xC302` (sub-tipos 2, 0xE, 0xF) | `0x42648C` |
| `0x4001`…`0x4006` | estado de jugador / chat de partida (`0x4002` copia texto) | INFERIDO |
| `0x8000`…`0x8004`, `0x8100`…`0x8103`, `0x82FF`, `0x8600` | globales (sala/carga/evento) | `0x426410` |
| `0x8400` | **ficha del compañero con la versión interna (441)** | armado `0x4F05B0`; si la versión ajena es mayor → **código 0x15, cierra** (`0x426A0A`) |
| `0x8005`, `0x8006`, `0x8402`…`0x8408`, `0x8500` | jugada (movimiento, disparo, ítem…) | INFERIDO; `0x8500` responde a un `0x4102` (`0x4D0D8A`) |
| `0xC300` | **UDP_TURN**: turno + clima | §1.4 |
| `0xC301` | **UDP_ENDTURN**: el delay del que tiró | log en `0x4D2643` |
| `0xC302` | **voto de sincronía** `[tipo][turno DWORD]` (+DWORD si tipo 0xE) | `0x42651A`, `0x4D07B3` |
| `0xC303` | **sincronía cumplida** (sólo la llave): `[tipo][64 bytes de estado]` (+WORD + clima si tipo 0xE) | `0x426FB2` |
| `0xC304` | "me morí" (va junto al `0x4100` al server) | `0x4E925D` |
| `0xC305` | muerte súbita (INFERIDO) | `0x4E6421` |
| `0xC306` | **UDP_PASSTURN** | log en `0x4D267E` |
| `0xC308` | antes del primer turno (INFERIDO) | `0x4E6362` |
| `0xC309`, `0xC400`, `0xC401`, `0xC409`, `0xC40B`, `0xC801`, `0xF008`…`0xF00B`, `0xF00E` | disparo / ítems / fin / varios | INFERIDO |

### 2.3 Lo que va y viene con el server durante la partida

| | dirección | qué | evidencia |
|---|---|---|---|
| `0x4500` / `0x4501` | ida/vuelta | túnel | ya medido (PROTOCOLO_LEGACY.md) |
| `0x4100` | → server | "me morí": [causa DWORD][quién byte], sin cifrar | `0x4E91E3` (MEDIDO). ★ El server decide el fin (Serv3 DeadUser/CheckPlayEnd): `0x4102` a todos + `0x4410 [ganador]` si terminó — ver `FIN_DE_PARTIDA_Y_SCORE.md` |
| `0x4104` | → server | "reaparecí" (Score/Jewel), cifrado `[casilla]` | `0x463EC5` (MEDIDO); el Serv3 contesta `0x4105` y manda `0x4106 [casilla]` a todos |
| `0x4000` | → server | **`[casilla]`: la llave pide echar a uno que no responde** | `0x4D8C63` (MEDIDO) — **sin atender hoy** |
| `0x4200` | → server | fin de Jewel; el server lo reparte como `0x4410` | ya en el server |
| `0x4412` | → server | resultado, lo manda la llave (`0x414C80`); lo re-manda la llave nueva si cambia (`0x4D0671`) | MEDIDO |
| `0x3232` | → server | "volví del resultado", **15 s después** de que llega el `0x4413` (`0x4D8932`) | MEDIDO |
| `0x3020` | server → | alguien salió: muestra texto 0x25F; la llave rehace el turno (`0x4CFF2E`) | MEDIDO |
| `0x3400` | server → | **nueva llave**: si soy yo, cierro los votos pendientes; si no, **re-mando mis votos** a la llave nueva (`0x4D063F`) | MEDIDO |
| `0x4102` | server → | **la baja**: `[casilla][causa DWORD][quién]`, cifrado; Score: resta una vida; causa `0xF000` (se fue) y soy la llave → `0x8500` | MEDIDO (`0x4D0C92` + Serv3 `0x4180F0`) |
| `0x4410` / `0x4413` | server → | **fin** `[ganador]` (equipo, o casilla sin el bit `0x80`; `FF` empate) — su lector suma el bono de victoria (`0x4106F4`) / "terminó" (arranca los 15 s) | `0x4D0927` / `0x4D0F72` |
| `0x3FFF` | server → | la sala se cierra: manda `0x2000 FFFF` y sale | `0x4D089A` |

### 2.4 Qué decide la llave

Junta los votos `0xC302`, manda `0xC303`, elige turno y arma el clima (INFERIDO fuerte, §1.4), corre el vigilante de votos (§3) y pide el resultado `0x4412`.
**Si la llave se va**, el server tiene que mandar `0x3020` + `0x3400` (el server ya lo hace en `sala.py:221`) y los otros le re-mandan los votos a la nueva.

---

## 3 · La red vieja: todos los plazos y chequeos

Los tics de juego son de **50 ms** (`[0x5CDCF8]` = 50, `[0x5CDCFC]` = 20 por segundo): **si la PC se traba, los plazos en tics se estiran.**

| # | dónde | plazo | qué hace al vencer | ¿falso positivo / cuelgue? |
|---|---|---|---|---|
| 1 | P2P `0x44D8CF` | 5 s sin mandarle nada a un compañero | manda ping `0x4002` | no |
| 2 | P2P `0x44D8FD` | **20 s** sin recibir de un compañero | **pasa al túnel para siempre** (`0x44D5E0`), nunca corta | ya parcheado a 2 s (parches 6 y 7) |
| 3 | P2P `0x44D910` | reenvío = último RTT, recortado a **250–3000 ms**; RTT inicial 250 | reenvía todo lo pendiente (`0x44EAC0`), **sin límite de intentos** | puede inundar el túnel si el otro se fue |
| 4 | P2P `0x44E37F` | ventana de 128 secuencias | lo de afuera se tira (pero se acusa) | si un compañero reinicia su P2P a mitad, sus mensajes se tiran |
| 5 | P2P `0x44DAAA` | suma de 1 byte | se tira en silencio | no |
| 6 | prueba UDP con el server `0x44D25F` | **7 intentos × 500 ms** al puerto del mundo (empieza al `0x1012`, `0x4F1FA2`) | evento 3 (anda) u evento 4 (no anda) | el server ya hace eco (`mundo.py:146`) |
| 7 | **vigilante de votos de la llave** `0x4D8B88` | cada **10 s** de espera: aviso `0x0003`; cada **30 s**: da por votado al que falta y sigue (`0x4D8CFC`) | strike a esa casilla; **al 6.º (>5): `0x4000 [casilla]` al server + `0x0004` a todos** (`0x4D8C46`) | la partida se "congela" 30 s por cada sync con alguien mudo |
| 8 | mensajes retenidos `0x44D370` / `0x44D400` | **sin plazo** | `0xC300`, `0xC306`, `0xC40B` (y otros) esperan a que termine la animación local | **cuelgue posible** si la animación nunca termina (INFERIDO) |
| 9 | fin de partida `0x4D0F72` | **sin plazo** para el `0x4413` | después de llegar, 15 s y `0x3232` | cuelgue si el server no contesta (hoy contesta) |
| 10 | **vigilante de reloj** `0x416C60` | entre llamadas tiene que haber **350–650 ms** (`0x15E`–`0x28A`) | **11 seguidas fuera → código 9, cierra el juego** (`0x416CA9`) | ★ **candidato n.º 1 a falso positivo** (PC trabada, ventana arrastrada, suspensión). No encontré quién lo llama cada 500 ms (objeto global `0x872F44`) |
| 11 | variable cifrada tocada `0x4141B6` | — | código 9, cierra | sólo con trampa |
| 12 | anti-flood de chat `0x42A410` (desde `0x4FAF2A`) | más de **5 envíos en 10 s** (no a GM rango 0x19) | 1.ª vez aviso (texto 0x141), 2.ª **código 0x1A, cierra** (`0x41454C`) | puede saltar con chat legítimo rápido |
| 13 | versión de compañero `0x426A0A` | WORD de `0x8400` > 441 | **código 0x15, cierra** | sólo si se mezclan versiones |
| 14 | server dice "hack" `0x44688F` | mensaje `0xF001` | código 9, cierra | lo decide el server |
| 15 | TCP del juego | **ningún keepalive del cliente** (el "Sending Noop" `0x4AD10C` es del messenger, cada 600 s) | sólo se entera con FD_CLOSE ("Disconnected right now", `0x4132AD`) | un corte "mudo" (cable, NAT) **nunca** se detecta del lado del cliente |
| 16 | modo 2 (conectando) `0x4144C4` | 200 tics = 10 s | código 1 | sólo al entrar |

Otros códigos de cierre (`0x4138B0`, `cl=1` cierra el juego, `cl=0` vuelve): `0x12` mensaje 0 del server · `0x45` error de lectura · `0x19` falta un archivo de datos
(`0x4274AF`, `0x4D6129`, `0x4ECFD9`) · `0x1B/0x2C/0x26` tienda. El texto de cada código está en la tabla `0x872F5C` (no la extraje).

### 3.1 Candidatos — del lado del server (sin tocar el exe)

1. **No cortar por silencio a quien está `JUGANDO`**: el `timeout=600` de `mundo.py:79` echa a cualquiera en una partida de más de 10 min. Mejor: TCP keepalive del SO
   (`SO_KEEPALIVE` + tiempos cortos) y, si se quiere plazo, sólo en lobby.
2. **Atender `0x4000 [casilla]`** (la llave pide echar a un mudo): sacarlo de la sala y mandar `0x3020` (y `0x3400` si era la llave). Sin esto, la partida sigue con 30 s de
   espera por cada sync. ⚠ Qué espera el cliente como respuesta: sin medir.
3. Detectar al **jugador muerto de red** antes: si un cliente tunela y deja de mandar `0x4500` mucho tiempo, o el keepalive TCP falla → `0x3020` a la sala enseguida.
4. **Siempre contestar `0x4413`** al `0x4412` (ya está) y al `0x3232` con `0x3233`.
5. Seguir con el eco UDP (`mundo.py:146`): sin él, la prueba de 3,5 s da "no anda".

### 3.2 Candidatos — parche al exe

1. **Vigilante de reloj `0x416C60`**: subir el tope de 10 (`0x416C9D cmp eax, 0xA`) o ensanchar 350–650, o anularlo. Es el que más se parece al "se cerró solo".
2. **Vigilante de votos `0x4D8B88`**: bajar 600 tics (30 s) para que un mudo frene menos (`0x4D8BA4 lea ebx,[edi+edi*2]` y `0x4D8BB9`); el umbral de 5 strikes en `0x4D8C46`.
3. Reenvío sin tope (`0x44EAC0`): ponerle límite si el túnel se satura.
4. Anti-flood de chat (`0x42A41F`, tope 5 en `0x414537`), si molesta.

---

## 4 · Lo que quedó dudoso

- **Quién manda el `0xC300`**: casi seguro la llave, pero las dos comparaciones de `0x4E5490` usan variables cifradas que no resolví. Se confirma con una traza: ver de qué casilla llega el `0xC300` en el túnel.
- **Quién llama al vigilante de reloj** (`[0x571818]+4` → `0x416C60`): ni el exe ni DualSoft tienen la dirección a la vista. Puede ser un hilo con `SetEvent` cada 500 ms o la DLL.
- Qué espera el cliente después de mandar `0x4000`. Los textos 0x25F/0x260/0x261/0x282/0x141 (están en la tabla de textos `0x872F5C`).
- Los nombres de la mitad de los códigos P2P (`0x4001`…`0x4006`, `0x8xxx`, `0xC309`…`0xC801`, `0xF0xx`).
- `[0x7667C]` = 15 o −1 según `[0x240E9]` (`0x4D711D`): puede ser el tipo de sync del fin de turno ("15 sync") o la muerte súbita; sin resolver.

## El móvil «aleatorio» (19-nov)

Lo sortea el **server**, en cada partida (`partida._movil_al_azar`). Copiado del `GunBoundServ3.exe` de Perú (0x416227):

| paso | Serv3 | nuestro |
|---|---|---|
| ¿especial? | `rand() % 10000 < Tank.Hidden.Ratio × 100` (el ratio sale del `setting.txt`, 0x40372B: **2 si falta, 5 en Perú**) | `GB_ESPECIALES`, **5** por omisión (lo eligió Eñeños) |
| cuál especial | `(rand() & 1) + 0x11` → 17 Dragón / 18 Caballero, mitad y mitad | igual |
| si no | `rand() & 0xF` → uno de los **16** normales (0..15), parejos | igual |

Con 5 %: Dragón 2,5 % · Caballero 2,5 % · cada normal ≈ 5,9 %.
Antes de esto el nuestro sorteaba sólo 0..13 (el 14 y el 15 no salían nunca) y los especiales al 2 %.
Lo comprueba `pruebas/probar_azar.py`, con sus controles (la lista vieja y el 2 % dan rojo).
