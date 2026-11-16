# GunBound Legacy v179 — rangos, bandera, nick/género y la tabla de mensajes

> Análisis estático, 16-nov-2026. Nada se ejecutó ni se tocó en `C:\GunBound-Legacy` ni en el repo.
> **MEDIDO** = leído en el código del exe o en los gráficos sacados de `graphics.xfs`.
> **INFERIDO** = sale de servers/webs viejos o de la forma del código, sin prueba directa.
> Scripts y salidas en `scratchpad\gb\cuenta\` (lista al final).

## 0 · Lo más importante en tres renglones

1. Al lado del nombre (canal y sala) **NO se dibuja el 1.er rango**: se dibuja el **3.er WORD** y la «bandera»
   es el **4.º WORD**. Hoy el server manda ahí `0, 0` ⇒ se ve la **varita de rubí** (cuadro 5) y la etiqueta **«?»**.
2. Rango → cuadro = **valor + 5**. Pollito = **19**, GM = **20** (el único valor que el cliente trata distinto),
   dragón plateado = −4 (el mejor). La «bandera» es un **código de país 0..245** (0 = «?», 9 = AR, 157 = PE…).
3. El cliente **no tiene** pantalla de «crear nick/género»: hay que seguir haciéndolo del lado nuestro.

---

## 1 · Rangos

### 1.1 Los 4 WORD de rango (MEDIDO)

Van iguales en tres mensajes: login `0x1012` (+27), ficha del canal `0x200E` (+22) y ficha de la sala
`0x2111`/`0x3010`. Los tres primeros el cliente los guarda **+5**; el 4.º tal cual.

| WORD | qué es | dónde se guarda (0x1012 / canal / sala) | quién lo usa |
|---|---|---|---|
| W1 | **rango total** (TotalGrade) | `+0x19ED6` / `+0x22DD8` / `+0x2434A` | panel «Mi info» (0x509A62), promedio del equipo (0x4F1AF0), **chequeos de GM** |
| W2 | **rango de temporada** (SeasonGrade) | `+0x19ED8` / `+0x22FD8` / `+0x2435A` | **nadie lo dibuja** (sólo se copia) |
| W3 | **el ícono al lado del nombre** | `+0x19EDA` / `+0x235D8` / `+0x2437A` | lista del canal (0x4FA7E6), sala (0x510F0E, 0x5193F8), «Mi info» |
| W4 | **país** (sin +5) | `+0x19EE4` / `+0x237D8` / `+0x2436A` | `nationcode.img`, dibujado ENCIMA del ícono de W3 |

⇒ En la base de Softnyx W3 sería el `CountryGrade` (rango dentro del país; por eso lleva la bandera encima)
— **INFERIDO**. Para nosotros alcanza con **W3 = W1**.

### 1.2 Número → ícono (MEDIDO: `rank2.img`, 183 cuadros de 25×15, sacado de `graphics.xfs`)

El cliente dibuja `rank2.img` (id 0x65) con cuadro = valor+5. Hoja: `cuenta\rank2_zoom.png`, `rank2_0_60.png`.

| valor | cuadro | ícono | nombre en `language.txt` (7000+) |
|---|---|---|---|
| −5 | 0 | martillo de GM (borde azul) | — |
| −4 | 1 | dragón plateado | Silver Dragon |
| −3 | 2 | dragón rojo | Red Dragon |
| −2 | 3 | dragón azul | Blue Dragon |
| −1 | 4 | varita de diamante | Diamond Hole |
| 0 | 5 | varita de rubí ← **lo que se ve hoy** | Red Ruby Hole |
| 1 / 2 | 6 / 7 | zafiro / violeta | Sapphire / Violet Hole |
| 3…8 | 8…13 | hachas de batalla (oro+, oro, plata+, plata, metal+, metal) | Gold/Silver/Metal Double Sided Axe(+) |
| 9 / 10 | 14 / 15 | hacha de oro doble / de oro | Double gold Axe / Gold Axe |
| 11 / 12 | 16 / 17 | hacha de plata doble / de plata | |
| 13 / 14 | 18 / 19 | hacha doble / hacha | Double Metal Axe / Metal Axe |
| 15 / 16 | 20 / 21 | piedra doble / piedra | |
| 17 / 18 | 22 / 23 | madera doble / madera | |
| **19** | **24** | **pollito** (el primero) | A Little Chick |
| **20** | **25** | **martillo de GM con «+»** | — |
| 21 | 26 | «VIP» | — |
| 22…29 | 27…34 | dragones/bichos especiales | — |
| 30…34 | 35…39 | estrellas (1 roja, plata, oro, 2, 3) | — |
| 35…46 | 40…51 | cascos, medallas, coronas | — |
| 47…91 | 52…96 | los mismos de arriba con una «+» | — |
| 92…96 | 97…101 | TikTok, otros logos, banderitas | — |
| 97…177 | 102…182 | franjas de colores (no parecen rangos) | — |

Lo que el **código** hace con el número (MEDIDO, todos comparan W1+5):

| dirección | compara | efecto |
|---|---|---|
| 0x403E60, 0x404040, 0x404539, 0x405998, 0x405C1D, 0x405F10, 0x4060D8 | `== 0x19` (GM, 20) | se salta chequeos en lo de amigos/silenciados |
| 0x42A415 | `== 0x19` | GM sin anti-flood del chat |
| 0x5167D4, 0x422F39 | `== 0x19` | otros permisos de GM (sala) |
| 0x425889 | `== 0x18` (pollito, 19) | caso especial del pollito en la sala |
| 0x522DE2 | `> 0x13` (valor ≥ 15: piedra doble para abajo, y GM) | no abre `XPShopListDlg`: mensaje 0x4F |

⇒ **GM = 20** (MEDIDO). El −5 se ve como GM pero no da permisos.

### 1.3 Cuánto GP pide cada rango (INFERIDO, servers viejos)

`GB TorHammer\www\modules\maintenance.php` (numeración Softnyx, coincide con la imagen):

| valor | GP | valor | GP |
|---|---|---|---|
| 19 pollito | 0–1099 | 9 hacha de oro doble | 6000–6899 |
| 18 madera | 1100–1199 | 8 batalla | 6900–8172 |
| 17 madera doble | 1200–1499 | 7 batalla+ | 8173–9939 |
| 16 piedra | 1500–1799 | 6 batalla plata | 9940–13076 |
| 15 piedra doble | 1800–2299 | 5 batalla plata+ | 13077–16024 |
| 14 hacha | 2300–2799 | 4 batalla oro | 16025–21984 |
| 13 hacha doble | 2800–3499 | 3 batalla oro+ | 21985–27280 |
| 12 hacha de plata | 3500–4199 | 2 violeta | 27281–35334 |
| 11 plata doble | 4200–5099 | 1 zafiro | 35335–51221 |
| 10 hacha de oro | 5100–5999 | 0 rubí | 51222–107915 |
| | | −1 diamante · −2 · −3 · −4 | 107916 · 199629 · 227295 · 238204+ |

GM: `TotalGrade = 20` a los de `Authority 99/100`. Hasta 6899 el corte es por GP fijo en todos los servers.
Desde **6900 GP** el original iba **por puesto** (lo dice el propio juego: `language.txt` 150023 «Double metal axe
and above rank are dependant on accumulated GP on others», 400028/400029). La versión por puesto está en
`gb-peru.net\bloque3\actualizar_total.php` (numeración propia de Perú; acá ya traducida a Softnyx):

| valor | quién |
|---|---|
| −4 dragón plateado | el puesto 1 |
| −3 dragón rojo | puestos 2–5 |
| −2 dragón azul | puestos 6–25 |
| −1, 0, 1, 2 | siguiente 1 %, 3 %, 4 %, 6 % |
| 3, 4, 5, 6, 7 | siguiente 8 %, 10 %, 11 %, 12 %, 20 % |
| 8 batalla | el resto con ≥ 6900 GP |

(los % son sobre los que tienen ≥ 6900 GP; `language.txt` 150021: «se actualiza una vez por día»).

### 1.4 ¿Se ve el GP? (MEDIDO)

Sí: en el panel **«Mi info»** (`XPMyInfoDlg`, dibujo en 0x509A30), con las etiquetas de `language.txt`.
Todo sale del **0x1012**; el GP no se refresca con ningún otro mensaje (sólo lo escribe 0x4F2307).

| campo del 0x1012 | se guarda en | etiqueta en pantalla |
|---|---|---|
| +35 WORD | `[0x19F04]` | (junto al gremio: ¿cantidad de miembros?) INFERIDO |
| +37 DWORD | `[0x19EEC]` | **TRank** (puesto total) |
| +41 DWORD | `[0x19EF4]` | ¿puesto de temporada? INFERIDO |
| +45 DWORD | `[0x19EFC]` | (junto al gremio: ¿puesto del gremio?) INFERIDO |
| +49 DWORD | `[0x19EE0]` | **CRank** (puesto en el país) |
| +53, +57 DWORD | `[0x1A550]`, `[0x1A558]` | ? |
| **+61 DWORD** | `[0x1A580]` | **GP** |
| +65 DWORD | `[0x1A588]` | ? |
| **+69 DWORD** | `[0x1A570]` | **Gold** (la tienda lee ésta) |
| +73…+88 | 4 × (WORD + 2 de relleno) → `[0x7744C]` | ¿EventScore0..3? INFERIDO |
| (Cash) | `[0x1A578]` | **Cash** — no viene en el 0x1012 (lo trae 0x1032) |

Hoy el server manda ceros desde +31 ⇒ «Mi info» muestra **GP 0, Gold 0, TRank 0, CRank 0**.

### 1.5 «Rango de temporada»

En Softnyx había `SeasonScore` (GP de la temporada) y `SeasonGrade`; al cerrar la temporada se sumaba al total
(comentario en `actualizar_total.php`). **En este cliente W2 no se dibuja en ningún lado** (MEDIDO: sólo se copia
de un lado a otro). Mandar W2 = W1 o el de temporada da lo mismo a la vista.

---

## 2 · La «bandera» con «?»

- **No es la 4.ª casilla del avatar** (MEDIDO): es el **4.º WORD de rango** (W4), y se dibuja con `nationcode.img`
  (id 0x66), **encima** del ícono de W3 (lista del canal 0x4FA803, sala 0x510F28, «Mi info» 0x509AAE).
- `nationcode.img` (MEDIDO, 246 cuadros, hoja en `cuenta\nation_0_130.png` y `nation_130_246.png`) **no son
  banderas**: son **etiquetas de 2 letras** (código ISO del país). **Cuadro 0 = «?»**.
- El orden de los cuadros es **exactamente** la tabla `country_reference` de la base de Softnyx
  (`DATA-BASE\Completas\SoftnyxDB\gunboundwc\gunboundwc.sql`): 1 AF, 2 AL, 3 DZ, 4 AD, 5 AO… (comprobado en la
  imagen con AR, BR, CL, CO, MX, PE, US, UY, VE).

| país | valor | país | valor |
|---|---|---|---|
| Argentina | 9 | Colombia | 42 |
| Bolivia | 25 | Ecuador | 57 |
| Brasil | 28 | México | 131 |
| Chile | 39 | Paraguay | 156 |
| España | 184 | Perú | 157 |
| Estados Unidos | 207 | Uruguay | 208 |
| Venezuela | 212 | (sin país) | **0 → «?»** |

Del 230 al 245 hay agregados (242 EU, 243 GB, 245 CS…). Más de 245 se sale de la imagen.

---

## 3 · Género y nick: ¿el cliente tiene su propio flujo? — **No** (MEDIDO, por barrido)

Lo que se miró para afirmar el «no»:

1. **Las 231 clases con RTTI** del exe (`cuenta\rtti.txt`): no hay ninguna de «crear personaje/nick/género».
   La única con nombre parecido, **`NameChangeDlg`**, es **cambiar el título de la SALA**: arma `0x3104` + el texto
   (0x4CA290; se abre desde 0x50FFDA en la sala).
2. **El 0x1012 con error** (rama 0x4F2549): sólo muestra un aviso para `0x5001`, `0x5011`, `0x5012`, `0x5013` y
   vuelve a la lista de servidores. No hay rama que abra un diálogo.
3. **Los 47 mensajes que manda el cliente** (sección 4): ninguno lleva nick propio ni género.
4. El género (0x1012 +18; fichas del canal y la sala) sólo se **lee**: `0` = varón (0x4F2080 → bandera en
   `+0x1A62C`). `language.txt` 60008/500029 lo usa sólo para avisar «el ítem es del otro género».

⇒ Como en el GunBound original (eso se hacía en la web), **nick y género se eligen afuera**: el launcher/Cuenta
Eñeños, o los `/nombre` y `/genero` de hoy. Nota: el cliente recién ve el cambio con un 0x1012 nuevo (relogin).

---

## 4 · Tabla de mensajes

### 4.1 Lo que el cliente RECIBE, por escena (MEDIDO: árbol de comparaciones de cada despachador)

Cada escena es una clase `GXP…Mode`; su método #1 es el despachador. Además hay uno **común** (0x40E7D0) que
corre siempre. «Server» = si `servidor/*.py` ya lo manda.

**Común (0x40E7D0)**

| cmd | qué hace (INFERIDO salvo que diga) | server |
|---|---|---|
| 0x1013 | dos listas (WORD cantidad + DWORDs) → `+0x1A548` | no |
| 0x1018 | desafío anti-trampa: el cliente responde **0x1019** (0x40EB73) | no |
| 0x101B | ídem, responde **0x101C** | no |
| 0x1022 | lista de 16+12 bytes (¿silenciados/vetados?) | no |
| 0x1030 | aviso de tiempo de cuenta (texto 6000) | no |
| 0x1032 | **cash** (MEDIDO) | sí |
| 0x1040 | DWORD → `+0x7748C` (¿multiplicador de evento?) | no |
| 0x1060 | estado: 1 → aviso 0x46, 3 → aviso 0x52 | no |
| 0x1079 | rtc 0 → aviso 0x47 | no |
| 0x1091 | respuesta a 0x1090 (en sala manda 0x3200) | sí |
| 0x1FF8 | aviso 0x45 (¿te sacaron?) | no |
| 0x1FFA | DWORD segundos ÷ 60 → aviso 0x5B (¿cierre en N min?) | no |
| 0x2001 | entrar al canal | sí |
| 0x200E / 0x200F | alguien llegó / se fue del canal (MEDIDO) | sí |
| 0x3010 / 0x3020 | alguien entró / salió de la sala | sí |
| 0x3400 | estado de una casilla | sí |
| 0x4410 | fin de Jewel/partida | sí |
| 0x4501 | túnel P2P (MEDIDO) | sí |
| 0x5001 | resultado de un mensaje (texto 0x1004) | no |
| 0x5101 | texto del server al chat (MEDIDO) | sí |
| 0x6001 / 0x6005 / 0x6032 | inventario / ítem nuevo (¿regalo?) / info de ítem | 6001 sí |
| 0x6101 / 0x6105 | cash / oro | sí |

**Servidores/login (`GXPServerMode`, 0x4F1E10)**: 0x1001 (ficha → manda 0x1010), **0x1012**, 0x1017 y 0x101A
(rtc 0 → arma el P2P con la IP/puerto), 0x101F, 0x1102, 0x2001.

**Canal (`GXPGameListMode`, 0x4CAD50)**: 0x1101, 0x2001, 0x201F (chat), 0x2103 (lista), 0x2105, 0x2111 (entrar),
0x2121 (crear), 0x2131/0x2132/0x2133 (¿entrada rápida?), 0x21F0…0x21F7, 0x3010, 0x3432.

**Sala (`GXPReadyMode`, 0x4EC500)**: 0x2001, 0x3010, 0x3020, 0x3105, 0x315F, 0x3201, 0x3211, 0x3231, 0x3233,
0x3400, 0x3431, **0x3432**, 0x3FFF.

**Carga (`GLoadMode`, 0x4A6CB0)**: 0x2001, 0x3233, 0x3FFF, 0x4410.

**Partida (`GXPPlayMode`, 0x4CFD60)**: 0x2001, 0x3020, 0x3233, 0x3400, 0x3FFF, **0x4102**, 0x4410, 0x4413.

**Tienda (`GXPShopMode`, 0x4F3B50)**: 0x2001, 0x6009, 0x600F, 0x6021, 0x6025, 0x6031, 0x6101, 0x6105.

**Otros**: broker 0x1100–0x1102 (0x4BFE30); `CBuddy2` 0x1001, 0x1011, 0x101F, 0x1FFE, 0x1FFF, 0x2010, 0x2021,
0x2031, 0x3001–0x3007, 0x3FFF, 0x4001, 0x5000 (0x4B1300, conexión de amigos aparte); UDP/P2P 0x4201–0x4203 y
0x8000–0x8004 (0x426410).

Mensajes que el receptor descifra **enteros** antes de despacharlos (0x445EF9, MEDIDO): 0x1032, 0x1033, 0x201F,
0x3432, 0x4102, 0x4106, 0x4410.

⚠ **Cosas que el server manda y el cliente NO atiende** (MEDIDO: no están en ningún despachador):
- **0x4101** (respuesta al 0x4100 «me morí»). El que sí existe es **0x4102** (partida, 0x4D0C92: casilla + DWORD,
  cifrado entero) — INFERIDO que ése es el aviso de muerte.
- **0x1021** (respuesta a «buscar»): ver 0x1020 abajo.

### 4.2 Lo que el cliente MANDA (MEDIDO: `push CMD; call 0x445B40` o `mov word [conexión+0x9C], CMD`)

| cmd | desde (clase) | qué es (INFERIDO salvo MEDIDO) | server |
|---|---|---|---|
| 0x1000 | GXPServerMode | pedir ficha | sí |
| 0x1010 | GXPServerMode | login (MEDIDO) | sí |
| 0x1019 / 0x101C | común | respuesta a los desafíos 0x1018 / 0x101B | **no** |
| 0x1020 | `gDialogConfirmAdd` | **agregar amigo** (WORD 1 + nombre) — no «buscar» | sí (como «buscar») ⚠ |
| 0x1021 | `CBuddyManager` | sincronizar la lista de amigos (WORD n + 16 B c/u) | **no** |
| 0x1078 | `ErrorCodeDialog` | «entendido» tras ciertos avisos (cuerpo vacío) | no |
| 0x1090 | ServerMode/ReadyMode | ajustes del mundo | sí |
| 0x1100 | broker | lista de servidores | (broker) |
| 0x2000 | varias | ir al canal (`FFFF` = el que toque) | sí |
| 0x2010 | canal | chat | sí |
| 0x2100 / 0x2101 | GameListMode | lista de salas / **página** (WORD) | 2100 sí, 2101 **no** |
| 0x2104 / 0x2110 / 0x2120 | XPGameListDlg | detalle / entrar / crear sala | sí |
| 0x2130 | canal | ¿entrada rápida? (vacío) | **no** |
| 0x2140 / 0x2141 | canal | ? (vacíos) | **no** |
| 0x3001 | sala | salir | sí |
| 0x3100…0x3104 | sala | mapa, ajustes, cupo, título (`NameChangeDlg`) | sí |
| 0x3150 | sala | un byte (?) | **no** |
| 0x3200 / 0x3210 / 0x3230 / 0x3232 | sala | móvil, equipo, listo, volver | sí |
| 0x3430 | sala | empezar | sí |
| 0x4000 | GXPPlayMode | ? | **no** |
| 0x4100 | partida | me morí | sí (responde 0x4101 ⚠) |
| 0x4104 | partida | byte de casilla, cifrado (¿rendirse/pasar?) | **no** |
| 0x4200 / 0x4412 | partida | fin de Jewel / pedir resultado | sí |
| 0x4500 | partida | túnel (MEDIDO) | sí |
| 0x5000 | amigos | 16 bytes (¿susurro/info?) | **no** |
| 0x5010 | partida | `FF` + largo + texto | **no** |
| 0x5100 | canal | /comandos | sí |
| 0x6000 / 0x6004 / 0x6008 / 0x600E / 0x6020 / 0x6100 / 0x6104 | tienda | inventario, regalos, ponerse, comprar, saldos | sí |
| 0x600A | tienda | WORD n (≤300) + piezas (¿vender/borrar varias?) | **no** |
| 0x6024 / 0x6030 | tienda | DWORD serie (+ bytes): ¿regalar? (responde 0x6025/0x6031) | **no** |

---

## 5 · Qué cambiaría en el server (para decidir; no se tocó nada)

1. En 0x1012 (+27…+33), 0x200E y fichas de sala: **W1 = W3 = rango(GP)**, W2 = temporada, **W4 = país**.
   Pollito 19, GM 20.
2. En 0x1012: **+61 = GP**, **+69 = oro**, +37/+49 = puestos (si se quieren ver en «Mi info»).
3. Guardar `pais` en la base (0 = «?») y `gp`; el rango desde la tabla 1.3.
4. Responder **0x4102** en vez de 0x4101 (medir con dos clientes qué espera adentro).

## Archivos de este trabajo (`scratchpad\gb\cuenta\`)

| archivo | qué |
|---|---|
| `arbol.py` | recorre el árbol de comparaciones de un despachador (cmp/sub/je/tablas) |
| `entrantes.txt`, `salientes.txt`, `despachadores.txt` | las listas crudas |
| `clases.py` → `clases.pkl`, `rtti.txt` | vtables ↔ nombres de clase (RTTI) |
| `xfs_index.bin`, `sacar_xfs.py` | índice de `graphics.xfs` (FOX7, zlib; 18 948 entradas de 128 B) y extractor |
| `img.py`, `rle.py`, `hoja_img.py` | lector del formato `.img` (cuadros crudos RGB565 y RLE) |
| `xfs\` | `rank*.img`, `nationcode.img`, `language.txt` sacados |
| `rank2_zoom.png`, `rank2_0_60.png`, `rank2_60_183.png`, `nation_*.png`, `rangos_torhammer.png` | las hojas |
