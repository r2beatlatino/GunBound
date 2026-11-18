# GunBound en el launcher de Eñeños — la guía para el agente del launcher

> 16-nov-2026. Escrita para pasarle **a otra sesión** (la del launcher Tauri) todo lo que necesita para sumar
> GunBound, sin tener que leer el server. Cada dato de acá está **medido** contra el server y el cliente de verdad
> (o marcado *sin medir*). Si algo de este documento contradice al código del server, manda el código: avisá.

**Para arrancar la otra sesión**, alcanza con decirle:

> Leé `D:\Gunbound\gunbound-servidor\documentacion\PARA_EL_LAUNCHER.md` y sumá GunBound al launcher
> (rama `launcher-tauri`), siguiendo el mismo camino que EDA. Probalo contra el server local antes de nada.

---

## 0 · Las reglas (las mismas de siempre)

- ⛔ Nada a prod, nada publicado, ningún launcher subido sin que Benja lo pida.
- ⛔ El server de GunBound vive en **otro repo** (`D:\Gunbound\gunbound-servidor`, git local). Desde el launcher
  **no se cambia**: si falta algo del lado del server, se anota y lo hace la sesión de GunBound.
- ⛔ La clave de PRUEBA (`estado/clave_prueba.json` del repo de GunBound) firma pases que sólo valen contra el
  server de laboratorio. Nunca en un build que se publica (igual que `R2_EDA_CLAVES_PRUEBA`, sólo en debug).
- El cliente (`D:\Gunbound\Cliente-Enenos`) es de Softnyx: no va a ningún repo; se reparte por la CDN.

## ★ En el ENSAYO (18-nov, andando y medido de punta a punta)

| qué | dónde |
|---|---|
| canje y personajes (prod) | `https://ensayo.xn--eeos-gqab.link/gunbound/…` |
| canje y personajes (prueba) | `https://ensayo.xn--eeos-gqab.link/gunbound-prueba/…` |
| el juego (lo devuelve el canje) | prod `ensayo.xn--eeos-gqab.link:8372` · prueba `…:9372` (broker; el mundo 8370 / 9370, TCP+UDP) |
| la lista FIRMADA del cliente | `https://ensayo.xn--eeos-gqab.link/gunbound/lista.jws` (sin caché) |
| sus archivos | ★ desde el 18-nov por la CDN: `https://cdn.xn--eeos-gqab.link/gunbound/<versión>/<ruta>` (§5.1). La lista vigente es la 2026.11.18.2 |
| la firma | cabecera `{"alg":"EdDSA","typ":"gunbound-manifiesto","kid":"140674dc24472102"}` (la clave ACTUAL de publicación de la plataforma, la misma que ya conoce el launcher) · carga con `"aud":"gunbound-launcher"` + `iat` |
| el pase | `Portero::pase_para("gunbound")` / `("gunbound-prueba")`: Cuenta Eñeños los abre a toda cuenta activa |

Medido el 18-nov: cuenta de prueba nueva → pase → personajes (0, máximo 2) → crear (pollito, AR) → canje →
el juego de verdad entra al mundo del ensayo (log: `adentro`). Controles: pase reusado 409, nick repetido 409,
ficha inventada 401, pase `gunbound` contra prueba 401. La firma verificada también con OpenSSL (y un byte
cambiado no verifica). Herramientas: `lista_del_cliente.py` + `firmar_lista.py`.

## 1 · Dónde estamos

| pieza | estado |
|---|---|
| server (Python, Docker, prod + prueba) | ✅ anda de punta a punta en esta PC y en Docker; banco en verde (9 pruebas, 230 comprobaciones) |
| cliente parchado (`parchar_cliente.py`) | ✅ `D:\Gunbound\Cliente-Enenos`, 36 archivos, 761 MB |
| 2 personajes por cuenta, crear / elegir / cambiar país | ✅ en el server, por HTTP (§3) — **falta la pantalla** |
| lista de países y nombres de rango para la pantalla | ✅ `GET /paises` + `rango_nombre` (§6) |
| íconos de rango en PNG | ✅ `herramientas/exportar_para_launcher.py` (§6) |
| la lista de archivos del cliente | ✅ `herramientas/lista_del_cliente.py` arma la carga — **falta firmarla y subirla** (§5) |
| **Cuenta Eñeños da pases `gunbound` / `gunbound-prueba`** | ❌ el cambio está en `integracion/cuenta_enenos_gunbound.patch`, **sin aplicar** (§8) |
| **server de GunBound en el VPS de ensayo** (Caddy `/gunbound/*`) | ❌ sin armar (§8) |
| **la ficha de GunBound en el launcher** | ❌ **es este trabajo** |

⇒ Se puede construir y probar TODO contra el server local ya mismo (§7). Lo que depende de §8 es sólo el
último tramo: el pase de verdad y la descarga desde la CDN.

## 2 · Lo que tiene que hacer el launcher

En el orden en que lo ve el jugador. El modelo es EDA (`taller/launcher_tauri/src-tauri/src/eda.rs`).

1. **La carta de GunBound** en el mazo de juegos (hoy «próximamente»). La carpeta del instalador ya está prevista:
   `C:\game\N2launcher\Gunbound\` (`config.rs`, 16-nov).
2. **INSTALAR / actualizar**: bajar el cliente con la lista firmada, como EDA (§5). Si no está, JUGAR dice
   INSTALAR (pedido de Benja del 15-nov, anotado en la memoria del launcher).
3. **La pantalla de personajes** (nueva; EDA no la tiene). Benja (16-nov): **2 personajes por cuenta**, cada uno con
   nick, género (los dos iguales o distintos) y país; todos nacen **pollito**; el país se cambia después.
   - Lista: hasta `maximo` (= 2) tarjetas. Cada una: nick, ícono de rango (`rangos/<rango>.png`), `rango_nombre`,
     GP, país (nombre + bandera del launcher por `iso`).
   - «Crear personaje» si hay menos de `maximo`: nick, género (m/f), país (menú con `GET /paises`, viene marcado el
     `pais_sugerido`).
   - Cambiar el país de un personaje existente.
   - Elegir uno y JUGAR.
4. **JUGAR**: canje con `{ficha, personaje}` → registro de Windows → `GunBound.exe` (§4).
5. **Casilla / botón «Servidor de prueba»** del juego, como el de R2Beat: cambia el `aud` del pase
   (`gunbound-prueba`) y el prefijo de las rutas (`/gunbound-prueba/...`). Cada uno tiene sus personajes aparte.
6. **Configuración** (opcional, después): lo único medido es la ventana `1600x1200` en modo `Windowed` (§4.2).

## 3 · El contrato HTTP (servidor/web.py — exacto)

La base es `https://<host>/gunbound` (prod) o `https://<host>/gunbound-prueba` (prueba). En local:
`http://127.0.0.1:8371/gunbound`. Todo es JSON. Los errores siempre son `{"error": "<texto en castellano>"}`,
mostrable tal cual al jugador.

### 3.1 · El pase → la ficha

El pase lo da Cuenta Eñeños como a EDA: `Portero::pase_para("gunbound")` (o `"gunbound-prueba"`).
⚠ **El pase es de UN SOLO USO** (medido: el 2.º intento da `409 pase ya usado`). Por eso existe la **ficha**.

```
POST /gunbound/personajes          {"pase": "<JWT>"}
→ 200 {"ficha": "R56YJ8uJoGTA97xYZVcx3qUs",          24 letras y números, vale 10 MINUTOS (en memoria del server)
       "personajes": [{"id": 90000031, "nick": "Ana_1", "genero": "f", "pais": 9,
                       "rango": 19, "rango_nombre": "Pollito", "gp": 0}],
       "maximo": 2,
       "pais_sugerido": 9}                               de la cabecera CF-IPCountry (Cloudflare); 0 si no viene
→ 401 pase inválido · 409 pase ya usado · 403 cuenta suspendida · 503 el server no tiene la clave de Cuenta Eñeños
```

- Si la ficha vence (10 min sin jugar), se pide **otro pase** y se repite este paso. No guardarla en disco.
- `id` es el «usuario» del juego: personaje 1 = el Eñeños ID de la cuenta; personaje 2 = 1 000 000 000 + cuenta.
- `rango`: −4…20 (y 21+ si un GM le pone un ícono especial). 19 = pollito, 20 = GM. Se calcula por GP.

### 3.2 · Crear, cambiar país

```
POST /gunbound/personajes/crear    {"ficha", "nick": "Ana_1", "genero": "m"|"f", "pais": 0..241}
→ 200 {"personajes": [...]}       la lista entera, ya con el nuevo
→ 400 datos inválidos (nick, género o país) · 401 ficha vencida · 403 ya tiene el máximo · 409 nick ocupado

POST /gunbound/personajes/pais     {"ficha", "personaje": <id>, "pais": 0..241}
→ 200 {"personajes": [...]}
→ 400 · 401 · 403 ese personaje no es de tu cuenta
```

- **Nick**: `^[A-Za-z0-9_]{3,12}$`, único **sin mirar mayúsculas**. Validarlo en la pantalla con la misma regla.
- **País**: el número del juego (no el ISO). 0 = sin país (el juego muestra «?»).
- Lo creado o cambiado se ve en el juego **al entrar** (el cliente lo lee sólo en el login).

### 3.3 · El canje (para jugar)

```
POST /gunbound/canje               {"ficha", "personaje": <id>}
→ 200 {"usuario": "90000031", "ticket": "Ab3dEf7hJk2m", "servidor": "juego.eñeños.link:8372",
       "nick": "Ana_1", "nuevo": false}
→ 400 · 401 ficha vencida · 403 ese personaje no es de tu cuenta / suspendida
```

- El boleto vale 12 h y sirve para re-entrar al mundo mientras el juego está abierto.
- **Una persona, un personaje adentro**: entrar con el otro personaje de la misma cuenta saca al primero.
- Sigue existiendo `POST /canje {"pase"}` (sin pantalla de personajes = personaje 1). Para la ficha nueva no hace
  falta.

### 3.4 · Lo público (sin pase)

```
GET /gunbound/salud    → {"ok": true, "entorno": "prod"|"prueba", "juego": "gunbound", "en_linea": 3}
GET /gunbound/paises   → {"paises": [{"n": 0, "nombre": "Sin país", "iso": null},
                                     {"n": 9, "nombre": "Argentina", "iso": "AR"}, ...]}   242 entradas
```

## 4 · Abrir el juego (la parte delicada)

La referencia que anda es `herramientas/jugar.py` (Python): canje → `escribir_registro` → `abrir`.

### 4.1 · Validar lo que llega

`usuario` `^[0-9]{1,16}$` · `ticket` `^[A-Za-z0-9]{12}$` (⚠ EDA usa 20: **son 12**) ·
`servidor` `^[A-Za-z0-9.\-]+:[0-9]{1,5}$`. Si algo no cumple, no se abre nada.

### 4.2 · El registro: `HKCU\Software\softnyx\Enenos`

El cliente parchado lee **sólo** de ahí (no de HKLM, no de `softnyx\Legacy`). Escribir **todos** estos valores, con
**estos tipos** — ⛔ los `REG_BINARY` son **de UN byte**. Escritos como texto (`"{1}"`), el juego lee el `{` y dibuja
el HUD mezclado (medido 16-nov: el panel WEAPON vacío con el selector redondo encima).

| valor | tipo | qué poner |
|---|---|---|
| `IP` | SZ | el host de `servidor` — ⚠ *sin medir* si el exe acepta un NOMBRE (usa gethostbyname): **resolverlo a IP en el launcher** y escribir la IP |
| `port` | DWORD | el puerto de `servidor` |
| `BuddyIP` | SZ | igual que `IP` |
| `BuddyPort` | DWORD | `port − 20` |
| `Location`, `Path` | SZ | la carpeta del cliente **con `\` al final** |
| `ScreenMode` | SZ | `Windowed` (lo medido; el juego va en ventana por DxWnd) |
| `ScreenDetail` | SZ | `1600x1200` (lo medido) |
| `MusicVolume` 7 · `EffectVolume` 100 · `MouseSpeed` 50 · `Language` 1 · `AppID1` 701 · `AppID2` 702 · `AppID3` 703 · `LastServer` 0 · `AutoRefresh` 1 · `Version` 179 | DWORD | tal cual |
| `PlayBackStyle` | DWORD | el **medidor de tiro** que eligió el jugador: 0 Normal · 1 Milimétrico · 2 Métrico (lo lee el parche 9 del exe en esta MISMA clave, al empezar cada partida; `jugar.py` pone 1). ⚠ NO en `…\Enenos\Config` ni en HKLM: eso era de lua15.dll, que nuestro cliente no carga |
| `Background` 01 · `ChannelName` 00 · `Effect3D` 03 · `EffectUse` 01 · `GameName` 00 · `InterfaceMode` 01 · `MusicUse` 00 · `MidiMode` 01 · `ShootingMode` 00 · `ShowMoon` 00 · `ShowOnlineUser` 00 · `ShowTurn` 01 · `LastID` 00 | **BINARY (1 byte)** | el byte en hex |

La tabla sale de `REGISTRO_BASE` en `jugar.py`: si cambia allá, manda allá.

### 4.2b · Ventana o pantalla completa: en el `dxwnd.dxw`, NO en el registro (medido 18-nov)

`ScreenMode` no cambia nada (el DxWnd mete el juego en ventana igual): dejarlo en `Windowed`. Lo que cambia es el
`dxwnd.dxw` de la carpeta del cliente, ANTES de abrir (el juego lo lee al arrancar). Partiendo del que viene en la
lista firmada:

| | `coord0` | `flagg0` | `flagi0` | `sizx0` `sizy0` `initresw0` `initresh0` |
|---|---|---|---|---|
| **ventana** (lo de hoy) | `1` | `1275346944` | `4194308` | el tamaño elegido |
| **pantalla completa** | `3` | `1275346960` (+`0x10` KEEPASPECTRATIO) | `4227076` (+`0x8000` HIDEDESKTOP) | dejarlos como estén (no se usan) |

Pantalla completa = el juego 4:3 sin estirar a la altura del monitor y centrado (en 1920×1080: 1440×1080 en x=240),
sin marco, con bandas negras a los costados (una ventana `dxwnd:hider` de DxWnd); el mouse bien escalado (clic
medido). No hace falta saber la resolución del monitor: DxWnd la toma solo. Volver a ventana = volver a escribir la
fila de arriba (medido). ⚠ Calcularlo con OR / AND sobre el valor que haya (`flagg0 | 0x10`, `flagi0 | 0x8000`; para
volver, `& ~`), no clavarlo: si un día cambia el dxw de la lista, los demás bits se respetan.

⚠ **En ventana, el tamaño tiene que entrar en el área de trabajo** (altura + ~36 de la barra de título): en un monitor
1920×1080 (área 1920×1032), `1600x1200` sale 1600×1032 ESTIRADA y con la barra de título fuera de la pantalla (así
está hoy); `1280x960` sale 4:3 y con su barra (medido). Ofrecer sólo los que entren (`SystemParametersInfo
SPI_GETWORKAREA`), o elegir por defecto el más grande que entre.

#### Resolución CON pantalla completa — medido 18-nov (las dos vías que se pidieron)

**(1) Cambiar la resolución del MONITOR mientras se juega: NO.** DxWnd no tiene un campo para eso (sus `initres`,
`maxres`, `SUPPORTSVGA`… son las resoluciones que le FINGE al juego, no las del monitor): tendría que hacerlo el
launcher con `ChangeDisplaySettingsEx`. Medido con 1280×960 y la receta ★: el juego llena el monitor justo (1280×960
en 0,0, sin bandas), pero:
- **el mouse quedó MAL escalado**: el clic no entró al lobby y el cursor se dibujó a escala del tamaño anterior;
- **Windows NO devuelve el modo si el proceso que lo cambió muere** (lo cambié con `CDS_FULLSCREEN` desde un proceso
  y lo maté: el monitor siguió en 1280×960). O sea: si el launcher se cierra o se cuelga, el jugador queda con el
  monitor cambiado;
- devolverlo costó: un cambio hecho por un proceso que se cierra enseguida a veces se pierde (volvía a 60 Hz en un
  monitor de 165), y con dos monitores hay que nombrar el dispositivo (`\\.\DISPLAY1`). Encima, al bajar la
  resolución Windows reacomoda las ventanas del escritorio.

**(2) El monitor como está y la resolución elegida = el TAMAÑO del juego, centrado sobre negro: anda, con un
pero.** Valores (sobre la receta ★ de pantalla completa):

| | `coord0` | `posx0` `posy0` | `sizx0` `sizy0` `initresw0` `initresh0` | `flagn0` |
|---|---|---|---|---|
| tamaño W×H centrado | `0` | `(monitorW−W)/2`, `(monitorH−H)/2` | `W`, `H`, `W`, `H` | `& ~1` (sin FIXTHINFRAME = sin marco) |

(+ `flagg0 | 0x10` y `flagi0 | 0x8000` como en ★). Medido 1024×768 en 1920×1080: ventana sin marco 1024×768 en
(448,156), el mouse bien (clic → lobby), negro alrededor. **El pero:** como la ventana del juego no cubre el monitor,
Windows NO la toma como pantalla completa (estado `ACCEPTS_NOTIFICATIONS`): **la barra de tareas queda visible
abajo** y el negro de DxWnd tapa sólo el área de trabajo. Con la ★ (el juego a la altura del monitor) Windows sí la
toma como pantalla completa (estado `BUSY`) y la barra de tareas se esconde (medido: abajo está el juego).
(`coord0=1` también centra, pero en el área de trabajo, no en el monitor.)

⇒ **Recomendación:** con «pantalla completa» marcada, ofrecer **«Pantalla entera (recomendado)»** = la ★, y si se
quiere elegir tamaño, los 4:3 que entren en el MONITOR (`800×600, 1024×768, 1152×864, 1280×960, 1440×1080`, los de
altura ≤ la del monitor), avisando que la barra de tareas se ve. No cambiar la resolución del monitor.

Descartado: sin `WINDOWIZE` es pantalla completa EXCLUSIVA (cambia el monitor a 800×600; el 4:3 lo decide la placa
de video), y lo del GBSet (`ddraw2` + DdrawCompat) cambia las dll. Detalle y la tabla entera: CLIENTE.md «La ventana».

### 4.3 · El argumento

`AES-128-ECB`, clave `FAEE85F24073D9161390197F6E562A67` (hex), sobre 48 bytes:
`usuario` (16, relleno con ceros) + `ticket` (16, relleno con ceros) + 16 ceros → **hex en MAYÚSCULA** (96
caracteres). Es `servidor/cifrado.py:argumento_cliente`. Una prueba de unidad en Rust contra un valor sacado de
ahí (`python -c "from servidor import cifrado; print(cifrado.argumento_cliente('90000031','Ab3dEf7hJk2m'))"`
desde el repo del server).

### 4.4 · El proceso

- `CreateProcess` con el programa = `<cliente>\GunBound.exe` y la **línea de comandos = SÓLO el hex**, sin la
  ruta del exe adelante (en Rust: `Command::new(exe).raw_arg(hex)` no alcanza, porque Rust antepone el nombre del
  programa: usar `CreateProcessW` con `lpApplicationName` = exe y `lpCommandLine` = hex). ⛔ Con la ruta adelante
  **el juego se cierra en silencio** (medido).
  ⚠ Es al revés que EDA (ahí va la ruta entre comillas): no copiar `eda::linea_de_comandos`.
- Directorio de trabajo = la carpeta del cliente.
- Se pueden abrir varias instancias (parches 4 y 5 del cliente).

## 5 · Repartir el cliente (la lista firmada)

`herramientas/lista_del_cliente.py` arma la carga en el formato de `eda::validar_manifiesto`:

```
{"juego": "gunbound", "version": "1.0.0", "base": "https://cdn…/gunbound/1.0.0/",
 "servidor": "juego.eñeños.link:8372", "canje": "https://…/gunbound/canje",
 "exe": "GunBound.exe", "del_usuario": ["MuteList.txt"],
 "files": [{"path": "graphics.xfs", "size": 665137759, "md5": "…"}, …]}       36 archivos, 761 MB
```

- Todas las rutas pasan `RX_RUTA` de `eda.rs` (la herramienta corta si alguna no).
- Falta decidir (lado launcher + plataforma): el `aud` y el `typ` de la firma para GunBound (¿`gunbound-launcher`?)
  y quién la firma. Benja (15-nov): una sola autoridad para todos los juegos — la clave de publicación de la
  plataforma, que el launcher ya conoce. La de EDA hoy la firma `firmar_manifiesto.py` del repo de EDA.
- Con eso, lo natural es generalizar `eda.rs` (verificar firma, `pendientes`, `bajar`) a «un juego con lista
  firmada», y que EDA y GunBound sean dos usos.
- Los archivos del jugador (`del_usuario`) no se pisan al actualizar. `graphics.xfs` es el grande (681 MB).

### 5.1 · La CDN y las PARTES (18-nov)

- **La base es la CDN**: `https://cdn.xn--eeos-gqab.link/gunbound/<versión>/` (Cloudflare delante del VPS, caché de
  1 año; el VPS le contesta 403 a lo que no venga de Cloudflare). ⛔ La carpeta de una versión NO se reusa con otros
  contenidos: versión nueva = carpeta nueva.
- **Partes**: el plan gratis de Cloudflare no guarda archivos de más de 512 MB. `lista_del_cliente.py --partes
  CARPETA` corta cada archivo de más de 500 MiB en pedazos de 256 MiB (el último, lo que sobre) y los declara EN
  ORDEN dentro de la entrada del archivo:
  ```
  {"path": "graphics.xfs", "size": 681151882, "md5": "<del archivo ENTERO>",
   "partes": [{"path": "graphics.xfs.p1", "size": 268435456, "md5": "…"},
              {"path": "graphics.xfs.p2", "size": 268435456, "md5": "…"},
              {"path": "graphics.xfs.p3", "size": 144280970, "md5": "…"}]}
  ```
  Los pedazos se suben a la misma carpeta de la versión (`<base><path de la parte>`). El launcher: valida cada parte
  con las mismas reglas que un archivo (`RX_RUTA`, `size` entero, `RX_MD5`, y la suma de los `size` = el `size` del
  archivo), baja cada una y comprueba su md5 (si una falla, se reintenta esa sola), las junta en orden y comprueba
  el `md5` y el `size` del archivo ENTERO antes de dejarlo en su lugar. En la carpeta del jugador queda el archivo
  entero, nunca las partes. Un launcher viejo no conoce `partes`: las ignora y baja el archivo entero (anda igual,
  sólo que ese archivo sale del VPS y no de la caché).
- Probado: `pruebas/probar_lista.py` (11, con controles: sin `--partes` no parte; un archivo chico va entero;
  juntadas en otro orden el md5 NO da) y sobre el `graphics.xfs` real: 3 pedazos que juntos dan el md5 entero.

## 6 · Recursos para la pantalla de personajes

- **Países**: `GET /gunbound/paises` (§3.4). El juego no dibuja banderas: dibuja una **etiqueta de 2 letras**. El
  launcher puede mostrar su propia bandera por `iso` (los que tienen `iso: null` → sólo el nombre).
- **Íconos de rango**: `python herramientas/exportar_para_launcher.py [carpeta]` escribe (fuera del repo, por
  omisión `D:\Gunbound\para_el_launcher\`):
  - `rangos/<valor>.png` — 183 íconos de 25×15 con fondo transparente, `-5.png` … `177.png`. Para la tarjeta:
    `19.png` pollito … `-4.png` dragón plateado, `20.png` GM, del 21 en adelante especiales (VIP, coronas…).
    Se ven chicos: escalarlos ×2 o ×3 con «vecino más cercano» (son pixel art).
  - `rangos.json` — nombres + cortes de GP (`{"gp": 1100, "rango": 18}`…) para mostrar «te faltan N GP».
  - `paises.json` — lo mismo que `/paises`, por si se quiere empaquetar.
  Son arte de Softnyx: van en el paquete del launcher (como el arte del muñeco de R2Beat) o se sacan del
  `graphics.xfs` del cliente instalado. Decisión del lado launcher.

## 7 · Probar en esta PC, sin Cuenta Eñeños

Desde `D:\Gunbound\gunbound-servidor` (Git Bash):

```bash
bash estado/reiniciar.sh                                         # el server de laboratorio: mundo 8370, canje 8371, broker 8372
python herramientas/jugar.py --solo-pase --id 90000055          # imprime un PASE de prueba (uno por pedido: es de un solo uso)
python herramientas/jugar.py --id 90000055                      # la referencia: canje + registro + abre el juego
```

```bash
P=$(python herramientas/jugar.py --solo-pase --id 90000055)
curl -s -X POST http://127.0.0.1:8371/gunbound/personajes -H "Content-Type: application/json" -d "{\"pase\":\"$P\"}"
```

- El log del server: `estado/lab.log` (cada login dice `adentro`).
- Para que el launcher pida el pase al server local en debug, lo más simple es una variable sólo de debug (como
  `R2_EDA_CLAVES_PRUEBA`) que tome el pase de `jugar.py --solo-pase` en vez de Cuenta Eñeños.
- `90000001` es GM en el laboratorio (rango 20 en todos sus personajes).
- Fotos del juego sin tocar el mouse: `python herramientas/ventanas.py foto <carpeta>`.

**Lista de comprobación** (cada una con su control al revés):

| comprobar | control (tiene que fallar) |
|---|---|
| cuenta nueva: 0 personajes, `maximo` 2 | — |
| crear 2 → aparecen, pollito, GP 0 | un 3.º → 403 · nick `a` → 400 · nick repetido en mayúsculas → 409 |
| cambiar país → se ve al entrar | país de un personaje ajeno → 403 |
| JUGAR con el personaje 2 → entra con su nick | la línea con la ruta del exe adelante → el juego se cierra |
| registro: el HUD se ve normal | `InterfaceMode` como texto → HUD mezclado |
| 10 min sin jugar → pide pase nuevo solo | reusar el mismo pase → 409 |
| «Servidor de prueba» → pasa por `/gunbound-prueba` | un pase `gunbound` contra prueba → 401 |

## 8 · Lo que falta de NUESTRO lado (no lo hace el launcher)

1. **Cuenta Eñeños**: aplicar `integracion/cuenta_enenos_gunbound.patch` en la rama de topología (los `aud`
   `gunbound` y `gunbound-prueba`). Sin eso no hay pase de verdad.
2. **VPS de ensayo**: sumar el contenedor de GunBound (prod + prueba) y Caddy `/gunbound/*` y `/gunbound-prueba/*`
   → 127.0.0.1:8371 / 9371, más el broker y el mundo abiertos (TCP 8372/8370 y UDP).
3. **La CDN**: subir el cliente y firmar su lista (§5).
4. *Sin medir*: si `IP` acepta un nombre; otras resoluciones de ventana; pantalla completa.

## 9 · Dónde está cada cosa

| qué | dónde |
|---|---|
| el server de las rutas | `servidor/web.py` (+ `base.py`: personajes, `boletos.py`: fichas) |
| la referencia del launcher | `herramientas/jugar.py` |
| el argumento AES | `servidor/cifrado.py` (`argumento_cliente`) |
| la lista del cliente | `herramientas/lista_del_cliente.py` |
| íconos y datos para la pantalla | `herramientas/exportar_para_launcher.py` |
| decisiones de los personajes | `documentacion/CREAR_PERSONAJE.md` |
| el camino entero de un jugador | `documentacion/COMO_ENTRA_UN_JUGADOR.md` |
| qué hace el cliente (rangos, banderas, GM…) | `documentacion/MAPA_DEL_CLIENTE.md` |
| el cliente y sus parches | `documentacion/CLIENTE.md`, `herramientas/parchar_cliente.py` |
| EDA, el modelo a copiar | `taller/launcher_tauri/src-tauri/src/eda.rs` (repo de R2Beat, rama `launcher-tauri`) |
