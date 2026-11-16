# GunBound Legacy v179: GM, mensajes raros y funciones escondidas

> 16-nov-2026. Análisis estático y de sólo lectura de `C:\GunBound-Legacy\GunBound.exe` y `DualSoft.dll`
> (desensamblado lineal + capstone/pefile). No se ejecutó nada ni se tocó el cliente ni el repo.
> **MEDIDO** = leído en el código, con dirección. **INFERIDO** = deducción razonable sin prueba en vivo.
> Scripts: `scratchpad\gb\gm\` (`sw.py` decodifica switches, `ann.py` desensambla anotando cadenas,
> `dlib.py` hace lo mismo con la DLL, `sends.py` lista los opcodes que manda el cliente).

---

## 0 · Corrección importante a lo que ya teníamos

| lo que decía la lista | lo que es de verdad | dónde |
|---|---|---|
| 0x5001/0x5013/0x500B/0x7000..0x7008/0x8004/0x8014/0x8016 son opcodes en 0x445D70 | Son **códigos de resultado (RTC)**: el `switch` va sobre el primer WORD del cuerpo, no sobre el opcode. Elige el cartel de error | MEDIDO 0x446323..0x4468C1 (lee `movzx eax, word [edx]` y loguea «2:RTC는 %d, 메시지는 %x») |
| 0x8001..0x8004 (switch 0x426829) | Mensajes **P2P** entre clientes (UDP o túnel 0x4500/0x4501), no del server | MEDIDO función 0x426410 (llamada desde 0x413DA1); el byte alto del tamaño es la casilla del que manda |
| 0x429570 / 0x502CA9 «muchos 0x8000» | Falsos positivos del script `cadenas.py` (sumas de saltos), no opcodes | MEDIDO 0x429608, 0x503203 son `je` |

---

## 1 · Comandos con «/» y GM

### 1.1 El cliente procesa algunos y manda el resto al server

Función **0x424E20** (la llama el chat del lobby en 0x4FAE4B antes de mandar 0x2010). Si el texto no empieza
con `/` (0x424E39), devuelve 0 y el chat sigue normal. Si empieza con `/`: junta espacios dobles, lo corta en
palabras (0x424D80) y compara la 1.ª palabra (sin distinguir mayúsculas, 0x548466). **MEDIDO:**

| comando | qué hace | condición | manda |
|---|---|---|---|
| `/h` `/help` `/guide` | muestra el texto de ayuda (cadena n.º 0x1F4) | sólo 1 palabra | nada |
| `/to` `/새` `/message` `/m` `<nick> <texto>` | **susurro**. Si el nick está en amigos va por el **server de amigos** (0xA110); si no, pregunta al server de juego **0x1020** `[01 00][nick 12]` y deja el texto en cola (0x404530, 0x404672). Pasa por el filtro de malas palabras (0x418B10) | ≥3 palabras; si el texto **contiene tu contraseña** (la descifra con la clave estática `FAEE85F2…`, 0x40B420 + strstr) no se manda: cartel 0x205 (INFERIDO «anti-robo») | 0xA110 o 0x1020 |
| `/kick <nick>` | echa a alguien **de la sala** | estar en sala (estado 9) y ser **la llave** (0x1A640 == 0x1A634) | **0x3150** `[casilla]` (0x425053) |
| `/key` | cartel 0x1F8 | — | nada |
| `/quit` `/exit` | se va del juego (0x4135C0(0xF)) | no en estados 0xB ni 9 | nada |
| `/go <n>` | en el lobby salta a la página de salas que contiene la sala n | estado 3 | **0x2100** `[01][WORD inicio][WORD 9]` (0x4251E7) |
| `/ipconfig` | muestra «Virtaul IP Mode IP[..] PORT[..]» | — | nada |
| `/clear` `/logging` | depuración: mandan a todos los compañeros P2P 0x9000 / 0xF00E (el 0xF00E prende un flag en 0x87069E) | — | P2P |
| `/iniciar` (¡en castellano!) | **empieza la partida** sin pasar por el botón | 1 palabra; no comprueba ser la llave | **0x3430** `[GetTickCount 4]` (+ 6×(WORD,BYTE) al azar si el modo es 3) (0x42540F) |
| `/Ehdzkffkvkdnj1`..`5` (= «똥칼라파워» tecleado en coreano) | prueba de **colores del chat**, sólo local (ver 1.4) | 1 palabra | nada |
| `/<nombre de evento>` | si la palabra está en `ChooseEvent.txt`, la llave cambia el **evento de la sala**: ajustes = (ajustes & 0xFFFFF) \| (índice << 24) | sala, llave, 1 palabra, flag 0x870592 = 0 | **0x3101** `[ajustes 4]` (0x42579C) — INFERIDO que es «evento» por el nombre del archivo |
| `/shrduarhkswjs` («…관전» = espectar) | se pasa al **equipo 0xFF** (espectador) | sala, llave | **0x3210** `[FF]` (0x425838) |
| `/shrduaakstpakstpaksakstp <n>` | elige **cualquier móvil por número** (alterna principal/secundario) | sala | **0x3200** `[móvil1][móvil2]` (0x425B77) |
| `/qz <n>` · `/qz s\|e\|o\|x` | **quiz**: tira preguntas (cadenas (n+13)×10000) a la sala por P2P; `qz e` además manda 0x2000 `FF FF` | sala y **rango guardado = 0x18** (rango 19 en el 0x1012) | P2P 0x0001 (+ 0x2000) |
| **cualquier otro** `/…` | se manda **tal cual** al server | — | **0x5100** con el texto crudo, `/` incluido, sin largo ni NUL (0x425C48 + 0x445B70) |

⇒ **Echar, silenciar, avisos, cerrar sala, ver IP: el cliente NO tiene nada de eso.** Todo es del server, por
0x5100. No hay menús ni diálogos de GM (las clases `XP…Dlg` del exe no tienen ninguno: hay Report, Gift,
MuteList, Buddy, Event, nada «Admin»).

### 1.2 «funciones» del 0x1012 — no hay bit de GM

Los 6 DWORD cifrados del final se guardan ofuscados (0x4F23DB..0x4F2510, en 0x1FEB4/0x1FEBC/0x1FEC4).
Los **7 lectores** de «funciones» (0x42334E, 0x423C3B, 0x423E2A, 0x42A37F, 0x4AABB4, 0x510698, 0x5107F1)
sólo prueban: bit 4 (0x10, avatares), bits 13..20 (0x2000 << i, una casilla de ítem/efecto cada uno) y
0x10000. **MEDIDO: ningún bit habilita nada de GM.**

### 1.3 Lo que sí hace el cliente con el rango (WORD +27 del 0x1012; el cliente le suma 5)

| rango que manda el server | guardado | efecto | dónde |
|---|---|---|---|
| **20** | 0x19 | **es el GM**: su chat de sala/partida sale en el color 5 («운영팀» = equipo de operación) | MEDIDO 0x422F39 (con el rango de la ficha de sala, 0x2434A) |
| 20 | 0x19 | **no puede** susurrar ni usar amigos (7 funciones de Buddy salen enseguida) | MEDIDO 0x403E60, 0x404040, 0x404539, 0x405998, 0x405C1D, 0x405F10, 0x4060D8 |
| 20 | 0x19 | **no tiene límite de flood** (al común: >5 mensajes en 10 s → aviso 0x141; la 2.ª vez cartel 0x1A + «Process Kick») | MEDIDO 0x42A415, 0x414537 |
| 20 | 0x19 | **el botón Empezar no le anda** (0x5167C0 da falso) ⇒ para eso está `/iniciar` | MEDIDO 0x5167D4, 0x511DBE, 0x511F59 |
| **19** | 0x18 | puede usar `/qz` (quiz) | MEDIDO 0x425889 |

⚠ Para el server: `/iniciar` manda el mismo 0x3430 que el botón, **sin comprobar ser la llave**. El server
tiene que validar quién lo manda (hoy `partida.py` ya exige la llave).

### 1.4 Colores del chat (para los avisos del server)

El texto de **0x5101** se dibuja con color 2 (sistema) y se parte en renglones por `\n` (0x411808).
Con color 2, **el primer carácter elige el color y se borra** (MEDIDO 0x42031C..0x4203B3):

| prefijo | `!` | `@` | `#` | `$` | `%` | `^` | `&` | `*` |
|---|---|---|---|---|---|---|---|---|
| color | sistema | rojo | naranja | verde | azul | violeta | negro | blanco |

⇒ un aviso de GM puede ir como `0x5101 "@ATENCION: …"` y sale en rojo. **Sin tocar el exe.**

Los demás números de color (de la prueba `/Ehdzkffkvkdnj`): 1 susurro · 2 sistema · 3 penalización ·
4 bonificación · **5 GM** · 6 «-_-;» · 8 Red Dragon · 9 comsik · 0xA..0x10 rojo..blanco · 0x11 «power user».

---

## 2 · Mensajes raros

### 2.1 Los que manda el server y el cliente entiende (handler común 0x40E7D0, todos MEDIDOS)

| op | cuerpo | qué hace | dónde |
|---|---|---|---|
| **0x1FFF** | WORD motivo | **te desconecta**: cierra el socket y muestra un cartel según el motivo (0→0x12, 1→0x17 con tu nick, 2→0x18 con tu ID, 0x10→0x30, 0x1000→0x31, 0x1001→0x32, 0x1002→0x33, 0x100F→0x34, otro→0x35). **Es el «kick» del GM** | 0x4460F6, switch 0x44616B |
| **0x1FFA** | DWORD segundos | aviso «**: N Minute**» (segundos ÷ 60) en el cartel 0x5B ⇒ cuenta regresiva de **mantenimiento** | 0x40FC86 |
| 0x1FF8 | — | cartel 0x45 (el mismo que el RTC 0x20, que además corta la recepción) — INFERIDO «bloqueado/cerrado» | 0x40F9E1 |
| **0x5101** | texto | mensaje de sistema (ver 1.4) | 0x411808 |
| 0x5001 | WORD 0 | escribe la cadena 0x1004 en color 3 (penalización) y abre `XPReportDlg` — INFERIDO «te reportaron / advertencia» | 0x410F6E |
| 0x6005 | DWORD · DWORD id · BYTE · nick 12 · DWORD fecha (time_t) · largo + texto | **llegó un regalo** («Get Gift message in root»); lo agrega a la lista y prende el aviso | 0x411017 |
| 0x6105 / 0x6101 | rtc · DWORD | saldo de oro / de cash (el 0x6101 contesta con 0x6104) | 0x411935 / 0x41197F |
| 0x6032 | 12 + 4 + 1 + 1 | algo de la misma lista que los regalos (0x23FA0) — sin identificar | 0x4118A6 |
| 0x400F | — | el cliente contesta **0x2000 `FF FF`** | 0x4468C6 |

### 2.2 Los códigos de error (RTC) — tabla del preprocesador 0x445D70

Se miran cuando el RTC ≠ 0 en las respuestas a **0x1012, 0x1017, 0x1031, 0x1079, 0x1102, 0x1312, 0x2001,
0x2103, 0x2111, 0x2121, 0x2131, 0x2132, 0x2133, 0x6021, 0x6031** (MEDIDO 0x446026..0x44631D). El número es el
cartel (`ErrorCodeDialog`, texto = cadena cartel+0xC7 de `language.txt`):

| RTC | cartel | RTC | cartel | RTC | cartel |
|---|---|---|---|---|---|
| 1 | 4 | 0x30 | 0x14 | 0x5001 | 0x1D |
| 2,3,4,7,8 | 3 | 0x60 | 0x15 | 0x5011 | 0x1E |
| **0x10** | **5** (= nuestro «no existe») | 0x1001 / 0x1002 / 0x1003 | 0xA / 0xB / 0xC | 0x5012 / 0x5013 | 0x1F / 0x20 |
| **0x11** | **6** (= nuestra «clave mala») | 0x2001..0x2004 | 0xD..0x10 | 0x6001 | 0x21 |
| 0x12 | 7 | 0x2008 | 0x2B | 0x7000..0x7008 | 0x37..0x3F |
| 0x19 | 0x16 | 0x3001 | 0x11 | 0x8000..0x8003 | 0x40..0x43 |
| 0x20 | 0x45 **y corta** | 0x24 | 0x5C | **0xF000** | «Double Logined» |
| 0x13,0x18,0x1A..0x1E, **0xF001** | «Server returns error likes hacking» (cartel 9) | | | | |

Comprobación cruzada: nuestro server ya manda 0x10 y 0x11 en el login y anda ⇒ la tabla lee bien.

### 2.3 Mensajes P2P (entre jugadores, función 0x426410)

0x0001 (**chat de sala**: va P2P o por el túnel, **el server no lo ve** salvo por el túnel), 0x0307,
0x4201..0x4203, 0x8000..0x8004, 0x8100..0x8103, 0x82FF, 0x8400, 0x8600, 0xC302, 0xF00E. MEDIDO el switch.
⇒ Un «mute» del server sólo puede cortar el chat del **lobby** (0x2010 → 0x201F), no el de la sala directa.

### 2.4 Servidor de amigos (Buddy) — aparte del de juego

Opcodes 0xA000 (entrar), 0xA110/0xA112 (mensajes), 0xA200, 0xA210, 0xA251, 0xA500, 0xA502, 0xA510
(MEDIDO 0x404578..0x4AB531). Va a `BuddyIP`/`BuddyPort` del registro. Sin ese server no hay susurros entre
amigos ni lista de amigos.

### 2.5 Lo que agregaba DualSoft (y perdimos al sacarla)

La DLL engancha 0x401DD0 (leer archivos del xfs), **0x40E7D0 (recepción)**, 0x468DC0, 0x526C80, 0x525BB0
(dibujo), **0x414B80 (imprimir mensaje de sistema)** y **0x5417CC (sprintf)** (MEDIDO 0x10126950..0x10126B03).

| función | cómo viaja | qué hacía |
|---|---|---|
| **0x7A31** bono GM por sala | 81 u 85 bytes, magia `GBRT`, título de sala (65), serie, activo, multiplicador 1000..10000 | cartel «BONUS GP» sobre la sala (colores de `GMBonusVisual.ini`). **Sólo visual** |
| **0x7A32** bono GM global | 20 bytes: `GBGS` · versión 1 · activo · serie · multiplicador · **FNV-1a** de los 16 primeros | cartel «BONUS GP» en el lobby. Sólo visual (MEDIDO 0x10128870, 0x101204E0) |
| 0x7A33 mascotas | 0x13 bytes, magia/versión/checksum | mascotas en sala y partida (`pet%d.img`, «PetRestore V2.5.0») |
| **etiquetas en el texto** de cualquier mensaje entrante (10..0x800 bytes) | `[PET_SYNC]:a:b:…`, `[SYNC_CLAN]:` (color de gremio), `[MSG_CORN]:c1:c2\|texto` (mensaje de sistema **con colores**), `[EMOTE]:…`, `[EMOTE_MUTE]:` | MEDIDO 0x10122E49..0x101243CD. **Sin la DLL esas etiquetas saldrían como texto crudo** |
| hacia el server, **por 0x5100** sin `/` | `[DS_TEAMCHAT]:`, `[DS_BONUS]:`, `[DS_HWLOG]:` (HWID), `[DS_BLACKLIST]:`, `[DS_MEMLOG]:`, `[DS_PROCLIST]:` (lista de procesos) | MEDIDO: arma el paquete a mano en el búfer de 0x870558 (bytes `00 51` + texto) y llama 0x445CD0 (0x10104770) |
| auth aparte | TCP a 15.204.128.129:8899..8901, `LOGIN\|0\|HWID…` | respuestas OK / login rechazado / **HWID bloqueado** |
| antitrampa | lista de nombres (cheat engine, speedhack, injector, vehdebug…), `Img.Info`/`ImgV2.Info` | protección de imágenes y reporte |
| extras | emotes con **Alt+1..0** (`emoti_%d.img`, `emote_sounds.txt`), **TurnAlert** (`turn.wav` cuando es tu turno), colores de gremio | — |

---

## 3 · Otras funciones escondidas

| cosa | qué es | evidencia |
|---|---|---|
| **Filtro de malas palabras** | `FourWord.txt` adentro de `graphics.xfs`; si el texto contiene una, **no se manda** y sale la cadena 0x202. Del lado del cliente | MEDIDO 0x418A13 (carga), 0x418B10 (prueba), 0x4FAE66 |
| **Lista de silenciados** | `MuteList.txt` (`[Mute List]` n=nick): ignorar **local**; el chat del lobby (0x201F) y el P2P pasan por 0x42A5F0 antes de dibujarse | MEDIDO 0x4136C9, 0x4CB125, 0x4266E0 |
| `eventword.dat` | el **abecedario** (≤64 letras) de la fuente `event_font.img`; la palabra del evento es la cadena 1.000.000 de `language.txt` ⇒ un evento de «juntar letras» | MEDIDO 0x449260/0x449330; el evento en sí, INFERIDO |
| `ChooseEvent.txt` | tabla de eventos de sala (nombre, número, banderas Y/N); la usa `/<evento>` | MEDIDO 0x408EC9, 0x409070 |
| `Event14.txt` | info del «Event14» | sólo la cadena (0x42ACEC) |
| Regalos | 0x6005 + diálogos `XPGiftItemDlg`, `XPRecvGiftItemDlg`, `XPRecvGiftResultDlg` | MEDIDO 0x411017 |
| Historial del chat | guarda los últimos 10 renglones para recuperarlos | MEDIDO 0x426330 |
| **Chat de voz, Lua, Game.Info** | `voice_chat.ini`, `opus.dll`, `libopus-0.dll`, `lua15.dll`, `lua5.1.dll`, `Game.Info`: **nadie los nombra** — ni el exe, ni DualSoft, ni NyxLauncher, GBSet, Updater, ddraw o dxwnd (búsqueda ASCII y UTF-16) y ninguno los importa | MEDIDO por búsqueda; INFERIDO que son restos o de otra versión de la DLL |
| Megáfono / cupones | **no hay** nada en el cliente (ni cadenas ni diálogos) | búsqueda negativa |

---

## 4 · Lo dudoso / lo que falta

- **Los textos de los carteles** (0x1F4, 0x202, 0x141, carteles+0xC7…) están en `language.txt`, adentro de
  `graphics.xfs`, y el índice del xfs no está a la vista (bloques zlib desde +9, sin nombres). No se extrajo.
- **0x5010** (lo manda el cliente en la pantalla de resultado: `FF` + largo + texto armado con la cadena 0x1388
  y la sala): no se sabe qué hace el server con eso (¿anuncio del ganador?).
- **0x5001** y `XPReportDlg`: el nombre dice «report», el color dice «penalización». Sin probar.
- El rango **19** (`/qz`) ¿es «presentador de eventos»? Sólo se sabe que habilita el quiz.
- El **cuerpo de 0x1020** (buscar usuario para susurrar) y su respuesta no se siguieron.
