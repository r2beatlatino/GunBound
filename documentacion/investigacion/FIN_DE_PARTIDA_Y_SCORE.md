# El fin de la partida (Solo, Score, Tag) y el número de sala

> 19-nov-2026. Disparador: en el ensayo (VPS de USA) una partida **Score 1vs1** no terminó cuando murió Bryan; los
> turnos del otro siguieron, y terminó recién cuando el otro se suicidó. Además, después de abandonar una partida
> ninguno de los dos pudo entrar a la sala nueva del otro.
> Fuentes: el cliente Legacy v179 (`D:\Gunbound\Legacy-Analisis\GunBound.exe.asm.txt`) y **el server original**
> `GunBoundServ3.exe` (Perú, `D:\Gunbound\GB\GBWC\Gunbound WEB\Server-Peru\GBWC-Files\GunBoundServ01\`), con sus
> propios textos de log (`CGameRoomManager::DeadUser`, `CheckPlayEnd`, `Resurrect`).

## 0 · En cinco renglones

1. **El fin de Solo, Score y Tag lo decide el SERVER**, no el cliente: con cada muerte (`0x4100`) el Serv3 se fija si
   terminó y manda **`0x4410 [ganador]`** a todos. Nuestro server sólo anotaba la muerte ⇒ la partida no terminaba.
2. **El bono de victoria** (3/6/9/12 GP, 100/150/200/300 de oro) lo suma el cliente **al leer ese `0x4410`**. Sin él,
   el que ganó cobró sólo lo de sus acciones (y por eso salió con GP negativo).
3. El cliente avisa cuando **reaparece** (`0x4104`); el server tiene que anotarlo, o el «equipo entero muerto» salta mal.
4. El Jewel es la excepción: ahí el fin lo manda el cliente (`0x4200` → el server lo reparte como `0x4410`). Ya andaba.
5. **Abandonar veda por 5 minutos el NÚMERO de esa sala** en el cliente; nuestro server le daba a la sala nueva el
   mismo número (0) ⇒ nadie podía entrar, sin ningún aviso.

## 1 · Lo que hace el Serv3 (MEDIDO en el binario)

| función (Serv3) | qué hace |
|---|---|
| handler `0x4100` (`0x429C54`, «SVC_PLAY_USER_DEAD») | lee `[DWORD][byte]` **sin cifrar** del paquete, llama a DeadUser con la casilla de la sesión y contesta `0x4101 [WORD 0]` |
| **DeadUser** `0x4180F0` | si la casilla no está viva (estado `0x81`) → log «already dead» y nada. Si no: la marca muerta (`0x82`), manda **`0x4102` cifrado a TODOS** (`[casilla][DWORD][byte]`, 12 bytes), en **Score** suma la baja del equipo (`+0x70C` si murió uno del A, `+0x708` si del B) y llama a CheckPlayEnd |
| **CheckPlayEnd** `0x4183E0` | **Score** (`ajustes & 0xC0000 == 0x40000`): `vidas = (ajustes >> 20) & 0xF`; si las bajas del B ≥ vidas gana el A (0), si las del A ≥ vidas gana el B (1). Si no se decidió (o no es Score): con el **bit `0x80` de `ajustes[0]`** (el Legacy lo manda siempre: `b2…`) recorre los vivos y, si son todos de **un solo equipo**, gana ése; sin el bit, gana **el último vivo** (su casilla). Nadie vivo → `0xFF`. Decidido → **`0x4410 [ganador]` cifrado a todos** y lo guarda en `+0x714` |
| handler `0x4104` (`0x429BEA`, «SVC_PLAY_RESURRECT») | **descifra** `[casilla]` y llama a Resurrect; contesta `0x4105 [WORD 0]` |
| **Resurrect** `0x418210` | sólo en **Score o Jewel** (si no: log «not in score nor jewel mode»); sólo si estaba muerta (`0x82`) → vuelve a viva (`0x81`) y manda **`0x4106 [casilla]` cifrado a todos** |
| al empezar `0x415F55` | en Score: `vidas = jugadores ÷ 2 + 1` → al nibble alto del byte [2] de los ajustes (1vs1 → 2 · 2vs2 → 3 · 4vs4 → 5) |
| al irse uno de la sala `0x4145BF` | si estaba jugando y vivo: **DeadUser con causa `0xF000` y quién `0xFF`** (y por eso puede cerrar la partida) |

O sea, las dos condiciones que contó Eñeños: **(a)** un equipo agotó sus vidas → pierde; **(b)** quedan vidas pero
todos los de un equipo están muertos a la vez → pierde. En 1vs1 la (b) salta **con la primera muerte**.

## 2 · Lo que hace el cliente (MEDIDO en el Legacy v179)

| dónde | qué |
|---|---|
| `0x4E91E3` | al morir: `0x4100 [DWORD +0x414][byte +0x410]` al server y `0xC304` por P2P a todos. Una vez por muerte (bandera `+0x2DC`, que se apaga al reaparecer) |
| `0x463EC5` | **al reaparecer** (modo 1 = Score o 3 = Jewel, y sólo el propio): `0x4104` cifrado `[casilla]` |
| `0x004D0C92` (lector de `0x4102`) | Score: resta una vida al equipo del muerto (texto 0x25C/0x25D) — con un control para no restarla dos veces si ya llegó por P2P. Si la causa trae `0xF000` y soy la llave → `0x8500` (rehace al que se fue). Si la casilla soy yo y la bandera `+0x11C4` está prendida → me voy al canal y veda la sala |
| `0x004106F4` (lector de `0x4410`) | lee **el byte del ganador** → `+0x26D78`, y **suma el bono de victoria** a los del equipo ganador (`0x004107BE–0x0041090A`, ver `PAGOS_GP_Y_ORO.md` §2) |
| `0x004D0927` (otro lector de `0x4410`) | el cartel de fin; la llave pide el resultado (`0x4412`) |
| `0x004D61A8` | las vidas que DIBUJA: jugadores de cada equipo + 1 (no las lee de los ajustes) |
| — | **`0x4101`, `0x4105` y `0x4106` no tienen lector** (sólo `0x4106` está en la lista de los que se descifran, `0x445EF9`): se mandan como el Serv3, el cliente no hace nada con ellos |

### La causa del `0x4100` (INFERIDO de los logs del ensayo)

`01000000 01` = lo mató la casilla 1 · `03000000 01` = suicidio (Eñeños se mató a propósito; el cliente tiene una rama
aparte `cmp [+0x414], 3` en `0x4E92C8`). `0xF000` = se fue (lo pone el server).

## 3 · Lo que pasó en el ensayo, leído con esto

```
13:43:46  sala 0 empieza (2 jug, mapa 10, Score)
13:44:58  Bryan murió · 01000000 01      ← Serv3: todo el equipo A muerto → 0x4410 [1] y FIN. El nuestro: nada.
13:46:23  Bryan: «sin atender 0x4104»    ← reapareció (el server no lo anotó)
13:47:19  test murió · 01000000 00
13:49:07  test: «sin atender 0x4104»
13:49:52  Bryan murió · 01000000 01
13:49:59  test murió · 03000000 01      ← suicidio
13:49:59  Bryan manda el resultado (0x4412): ganó con −1 GP, test perdió con −2
```

- **Por qué terminó al final**: no fue por las reglas del Score. La llave pidió el resultado sola después del suicidio
  (hay un camino en el cliente que llama a `0x414C80` tras una muerte, `0x4D3AAD`; no lo seguí más). INFERIDO.
- **Por qué el ganador salió con GP negativo**: el bono de victoria se suma al leer el `0x4410`, que nunca llegó
  (MEDIDO el lugar del bono; el resto de los −1/−2 son penalizaciones por acciones que calcula el cliente: el
  suicidio es −1 GP/−50 de oro según `PAGOS_GP_Y_ORO.md`). El modo NO se leyó mal: `04` en el byte [2] = bits 18–19 = 1
  = Score, y la excepción del Jewel (bono sólo con 100 puntos) no aplica.
- **La segunda partida (Solo 0x00)**: test murió 13:53:35 y la partida tampoco terminó (en Solo el cliente no se
  cierra solo); test abandonó a los 14 s.

## 4 · El número de sala vedado (MEDIDO en el cliente)

- `0x00425DA0`: agrega a una lista (hasta 64) `servidor + número de sala + (ahora + 300 s)`.
- La llaman: **el botón de abandonar** en partida (`0x004FA2D1`: `0x2000 FFFF` y veda la sala), el echado por la
  llave (`0x004EC9E8`) y el `0x4102` sobre uno mismo con `+0x11C4` (`0x004D0D33`).
- `0x00425F90`: ¿este número está vedado? Lo consultan **los dos caminos que mandan `0x2110` (entrar)**: la lista
  (`0x004CF338`) y «Go to» (`0x00500476`). Si está vedado **no manda nada y no avisa**.
- Nuestro `_id_libre` daba siempre el primer número libre: la sala abandonada era la 0 y la siguiente también ⇒ los
  dos (los dos habían salido por el botón de abandonar) quedaron 5 minutos sin poder entrar a ninguna «sala 0». Eso
  explica que en el log no haya ni un «no entra a la sala»: el `0x2110` nunca salió del cliente.

## 5 · Lo que cambió en el server (19-nov)

- `servidor/partida.py`: `murio` (0x4100) → `caer` (DeadUser) → `ver_fin` (CheckPlayEnd), `reaparecer` (0x4104),
  `ajustes_de_partida` (las vidas en el `0x3432`), `0x4101`/`0x4105` con su `WORD 0`. La `/practica` no se cierra sola.
- `servidor/sala.py`: el que se va a mitad de partida cuenta como muerto (`0xF000`, `0xFF`) — **diferencia con el
  Serv3**: a ése no se le manda su propia baja ni el `0x4410` (ya se fue). `_id_libre` no reusa por **330 s** el
  número de una sala cerrada. Los `return` callados de `crear` y `entrar` ahora dejan una línea en el log.
- Pruebas: `pruebas/probar_fin.py` (31 comprobaciones, cada regla con su control al revés; contra el server viejo dan
  17 rojas) y `probar_premio.py` corregida (leía el número de sala del `0x2121` corrido un byte: con la sala 0 daba
  igual).

## 6 · Lo que falta medir con el juego

- **Que el cliente acepte el `0x4410` de una muerte y muestre el cartel con el bono** (la mesa de esta PC no pudo
  arrancar la partida el 19-nov: la ventana ahora es 1920×1080 y el botón Start no respondió a los clics; las
  coordenadas de `PROBAR_CON_EL_JUEGO.md` son de 1600×1032).
- La bandera `+0x11C4` del cliente: si estuviera prendida durante el juego normal, el `0x4102` sobre uno mismo (que
  el Serv3 manda a todos, el muerto incluido) lo mandaría al canal. Con el Serv3 eso no pasaba, pero no lo medí.
- Tag (`0x08`): usa el mismo CheckPlayEnd que Solo; no hay nada propio de Tag en DeadUser.
