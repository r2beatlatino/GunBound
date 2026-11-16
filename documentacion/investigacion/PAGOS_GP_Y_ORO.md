# GP y oro al terminar una partida de GunBound Legacy v179

Revisión estática del 16/11/2026. **El cliente calcula los premios; `0x4412` ya lleva el oro y el GP de cada jugador.** Los servidores nativos revisados reciben esos deltas, controlan valores anormales y los pasan a persistencia. `0x4413` es el aviso de cierre: no hace falta inventarle una tabla de premios como respuesta.

**MEDIDO** significa leído en archivos o reconstruido directamente de instrucciones y constantes. No significa observado jugando. **INFERIDO** identifica interpretaciones, recomendaciones y límites de lo que se puede afirmar. No ejecuté el cliente ni los servidores, no instalé nada ni modifiqué archivos fuera de esta carpeta. No copié volcados de cuentas ni credenciales.

## 1. Fuentes y cómo ubicar la evidencia

En las tablas uso estos nombres cortos. Las direcciones son **VA hexadecimales**, no offsets dentro del archivo. Para el cliente también se pueden buscar en el listado indicado.

| Clave | Ruta exacta |
|---|---|
| **C** | `C:\GunBound-Legacy\GunBound.exe` |
| **A** | `D:\Gunbound\Legacy-Analisis\GunBound.exe.asm.txt` |
| **L** | `C:\GunBound-Legacy\graphics.xfs`, entrada `language.txt`; extracción local en `language_extraido.txt`, con los mismos renglones |
| **S2** | `D:\Gunbound\GB\GBWC\GB TorHammer\server\Server\Gunbound8360\GunBoundServ2.exe` |
| **CT2** | `D:\Gunbound\GB\GBWC\GB TorHammer\server\Server\Center\GunBoundCenter2.exe` |
| **S3** | `D:\Gunbound\GB\GBWC\Gunbound WEB\Server-Peru\GBWC-Files\GunBoundServ01\GunBoundServ3.exe` |
| **V585** | `D:\Gunbound\GB\GBWC\GunboundClasic\FILES-20220717T032803Z-001\FILES\WC season 1\files V 585\Gunbound\Server8360\GunBoundServ3.exe` |
| **FWC** | `D:\Gunbound\GB\GBWC\Gunbound WEB\Files_WC\Files_WC\Server8360\GunBoundServ3.exe` |
| **SQL2** | `D:\Gunbound\GB\GBWC\GB TorHammer\server\DB\gunbound.sql` |
| **PY** | `D:\Gunbound\GB\GBWC\Gunbound en gitb\gunbound-server-master\gunbound-server-master\GunBoundServer\gameserver.py` |
| **LAB** | `D:\Gunbound\Legacy-Laboratorio\Servidor\gameserver.py` |

**MEDIDO.** Se inventariaron 20 archivos llamados `GunBoundServ2.exe`/`GunBoundServ3.exe` en `GBWC`: cuatro SHA256 distintos. Las dos copias Serv2 coinciden; las doce de Perú también. FWC y Perú tienen la sección `.text` idéntica, aunque cambia el hash del archivo completo. V585 tiene algunas diferencias en `.text`, pero coincide en las constantes y lecturas de configuración de topes identificadas más abajo. No son veinte testimonios independientes.

Se buscaron declaraciones de procedimientos, funciones y triggers en los **159 `.sql` sueltos** de `GBWC`: no aparecieron. También se leyeron por streaming los SQL de los RAR distintos de `DATA-BASE\Completas` que los contienen: Batch season 2, db V585, SoftnyxDB y Thor's Hammer; tampoco aparecieron esas declaraciones. Los respaldos MyISAM se inventariaron por nombres; no se volcaron cuentas ni se levantó MySQL. Las búsquedas en webs no aportaron otra tabla numérica de premios.

## 2. Tabla de victoria: lo que suma el cierre

**MEDIDO — C/A, `0x004107BE–0x0041090A`; tabla de saltos de C en `0x00411C50`, ocho DWORD.** Esta es la tabla que **se suma a los acumuladores enviados**. Es un bono por jugador del equipo ganador, además de lo ganado durante la partida.

Valores base: factores de login en 100%, sin bonificaciones adicionales.

| Tamaño equilibrado | Jugadores usados para elegir fila | GP por victoria | Oro por victoria | Bono fijo por derrota |
|---|---:|---:|---:|---:|
| 1 vs 1 | 2 | 3 | 100 | 0 GP / 0 oro |
| 2 vs 2 | 4 | 6 | 150 | 0 GP / 0 oro |
| 3 vs 3 | 6 | 9 | 200 | 0 GP / 0 oro |
| 4 vs 4 | 8 | 12 | 300 | 0 GP / 0 oro |

La tabla interna agrupa **1–2, 3–4, 5–6 y 7–8 jugadores**, respectivamente. No usa literalmente una cadena «2vs2». La selección viene del contador de participantes del estado de partida (`G+0x25EC0`, objeto cuyo handle está en `+0x25EC4`; `G = [0x008701CC]`). No reconstruí una política adicional de balance de equipos desparejos.

**MEDIDO.** Sólo suma el bono a slots participantes cuyo equipo coincide con `G+0x26D78`, el equipo ganador (`0x00410870–0x004108EB`). Perder no borra el GP y oro acumulados por acciones; tampoco hay una resta fija por derrota en este bloque. Un empate, representado por ganador `0xFF`, no encuentra un equipo ganador y no agrega este bono.

### Modos

| Modo | Bono de victoria | Premios durante la partida |
|---|---|---|
| Solo | Tabla anterior | Muertes, tiros y daño de las tablas siguientes |
| Score | Tabla anterior | Mismos importes por acción; las reapariciones permiten repetir acciones |
| Tag | Tabla anterior | Mismos importes por acción; no encontré un multiplicador especial por Tag |
| Jewel | Misma tabla **si el ganador llegó a 100 puntos** | Tabla especial por joyas; se saltean las rutas normales de muertes y bonos de tiros/daño identificadas |

**MEDIDO.** La excepción Jewel está en `0x00410774–0x004107B8`: modo 3 y puntaje ganador menor que la constante 100 → no suma bono de victoria. El chequeo paralelo del aviso está en `0x004D0982–0x004D09C6`. Se saltean premios normales de muerte en `0x004D2995–0x004D29A3`, de tiros/daño en `0x004D9FC6–0x004D9FF4`, y de doble muerte en `0x004D37D2–0x004D37E6`. Los modos se extraen de los bits 18–19 de la configuración en `0x004F0A0E–0x004F0A35`; PY, renglones 1114–1121, los nombra Solo/Score/Tag/Jewel.

### Una discrepancia real: aviso de victoria contra acreditación

**MEDIDO — C/A, `0x004D09CC–0x004D0B69`; tabla en `0x004D0FD0`.** El aviso de chat «Win Bonus received» tiene una tabla parecida, pero su primera fila dice **20 oro / 0 GP**. En el cierre que modifica los acumuladores la primera fila es **100 oro / 3 GP**. Las otras filas coinciden.

| Fuente dentro del mismo cliente | 1 vs 1 | 2 vs 2 | 3 vs 3 | 4 vs 4 |
|---|---|---|---|---|
| Aviso/efecto de victoria | 0 GP / 20 G | 6 GP / 150 G | 9 GP / 200 G | 12 GP / 300 G |
| Suma efectiva al cierre | **3 GP / 100 G** | 6 GP / 150 G | 9 GP / 200 G | 12 GP / 300 G |

**INFERIDO.** Para implementar este v179 corresponde seguir la suma efectiva y comprobar el paquete real cuando se habiliten pruebas de juego. No tomar el texto del aviso como fuente única. No se puede certificar si esta diferencia ya estaba en Softnyx o si apareció en una modificación posterior de Legacy.

## 3. Muertes, penalizaciones y doble muerte

**MEDIDO — C/A.** Importes base; «Ending Bonus» es el nombre que usa este cliente para rematar a un rival. No es el bono de ganar la partida.

| Acción | GP | Oro | Evidencia en C/A; texto en L |
|---|---:|---:|---|
| Rematar rival, `Ending Bonus` | +1 | +100 | `0x004D2EDD–0x004D2FD3`; ID 613, r. 163 |
| Tirar rival al vacío, `Bunge Shot Bonus` | +1 | +100 | `0x004D2C6C–0x004D2D42`; ID 610, r. 160 |
| Matar compañero, variante 611 | −2 | −50 | `0x004D2B4E–0x004D2C3F`; r. 161 |
| Matar compañero, variante 614 | −2 | −50 | `0x004D2DBF–0x004D2EB5`; r. 164 |
| Suicidio | −1 | −50 | `0x004D29FA–0x004D2AF5`; ID 612, r. 162 |
| Doble muerte, adicional a los remates | +4 | +500 | `0x004D3816–0x004D395F`; ID 628, r. 178 |

**MEDIDO.** Las ramas Bunge y Ending son alternativas del evento de muerte; no encontré que una misma muerte pague ambos bonos de 100. El bono doble se cobra al detectar contador de remates ≥2 en el turno y después lo reinicia. También hay implementaciones equivalentes de +4 GP/+500 G en `0x004E5773–0x004E59CA` y `0x004E7525–0x004E7781`.

El código distingue la causa con el nibble bajo y el bit `0x10` del evento (`0x004D29A9–0x004D29F4`). Los identificadores de jugador permiten atribuir el premio o penalización al responsable. **No hay una deducción automática por morir a manos de un rival en estas ramas**: las deducciones encontradas son por suicidio, daño aliado y muerte aliada.

Ejemplo **INFERIDO por suma de constantes**: ganar un Solo 1vs1 con un remate normal, sin ningún otro bono, da **4 GP y 200 G**: 3/100 de victoria más 1/100 del remate. El daño o el tiro pueden agregar otros premios, así que no es un total garantizado de cualquier 1vs1.

## 4. Tiros y daño

**MEDIDO — C/A.** Estos importes se agregan al oro del jugador. Sólo las filas que indican GP modifican también su acumulador de GP.

| Concepto | GP | Oro base | Condición leída / dirección |
|---|---:|---:|---|
| Ultra High Angle | 0 | +30 | Vuelo > `4×20 = 80` ticks y daño ≥50; `0x004DA1DF–0x004DA381` |
| High Angle | 0 | +15 | Vuelo > `2×20+10 = 50` ticks y daño ≥50; `0x004DA3AA–0x004DA572` |
| Hurricane | 0 | +20 | Flag `G+0x26D40` activo y daño ≥50; `0x004DA5A7–0x004DA73C` |
| Boomer Shot | 0 | +20 | Flags de trayectoria: `+0x26D48` falso, `+0x26D50` verdadero; daño ≥50; `0x004DA771–0x004DA957` |
| Back Shot | 0 | +25 | Flag `+0x26D48` activo y daño ≥50; `0x004DA98C–0x004DAB22` |
| Team Damage | **−1** | **−25** | Daño aliado registrado en el turno **>50**; `0x004DAB5C–0x004DAD40` |
| Excellent Shot | 0 | +50 | Daño del turno ≥500; `0x004DADE2–0x004DAF4F` |
| Good Shot | 0 | +20 | Daño del turno ≥250 y <500; `0x004DAF78–0x004DB0DD` |
| Shot Bonus | 0 | +10 | Daño del turno ≥150 y <250; `0x004DB117–0x004DB27B` |
| Hito de daño 1000 | **+1** | +100 | Acumulado **>1000**, contador de siguiente hito=1; `0x004DB76A–0x004DB929` |
| Hito de daño 2000 | **+2** | +100 | Acumulado **>2000**, contador=2; `0x004DB565–0x004DB730` |
| Hito de daño 3000 | **+4** | +100 | Acumulado **>3000**, contador=3; `0x004DB356–0x004DB519` |

Textos que vinculan nombres y ramas: L, renglones 166–177, IDs 616–627. La constante de ticks vale **20** en C, VA `0x005CDCFC`. La constante de daño mínimo 50 se inicializa en `0x0040C24F–0x0040C26C`. La interpretación de esos ticks como duración del vuelo se apoya en el contador usado por las ramas; no traduje eso a un ángulo ni a distancia horizontal.

**MEDIDO.** Ultra y High tienen chequeos separados: la ruta Ultra continúa por el chequeo High. Un tiro que cumple ambos puede sumar **30+15 G** antes de otros bonos. Excellent/Good/Shot forman una selección por umbrales, por lo que no suman 50+20+10 en un solo turno. El chequeo de hitos usa `jle`: exactamente 1000 no pasa el primer hito. Avanza un hito por evaluación (`0x004DB2B5–0x004DB350`, `0x004DB95E–0x004DB971`); los tres hitos cobrados suman **7 GP / 300 G**. No es «1 GP por cada 100 de daño» ni una conversión lineal general.

**MEDIDO.** Los tiros y el daño también se guardan como estadísticas. En la ruta identificada, el contador enviado como tiros se incrementa cuando hay daño positivo y está desactivado el flag `G+0x4EE38` (`0x004DA120–0x004DA1B5`; incremento `0x00416E80`). Por eso no conviene llamarlo «cantidad de veces que apretó disparar» sin una captura que lo contraste. El propio cliente separa acumuladores de daño y daño computable.

| Pedido del encargo | Resultado de la revisión |
|---|---|
| Primer golpe | **No determinado**: no encontré una etiqueta ni un importe propio en las rutas de pago revisadas. No le asignaría un premio inventado. |
| Tiro de lejos | **No determinado como distancia**. Sí están los bonos por tiempo de vuelo indicados arriba. |
| Ataque doble / ítem Dual | No encontré un bono fijo por usar Dual. Puede producir más daño o una doble muerte y cobrar esos conceptos. L, r. 834, describe Dual como doble disparo, sin un premio de GP/oro. |
| Diferencia de rango rival | No encontré una fórmula de intercambio de GP por diferencia de rango en las rutas identificadas de victoria, muerte, daño o Jewel. **No queda demostrada una regla histórica universal de «cero ajuste por rango»** para todas las versiones. |
| Pagar por tiro sin impacto | No encontré un importe fijo. La estadística de tiros y los bonos por calidad de tiro son conceptos distintos. |

## 5. Jewel: puntos de partida separados de GP

**MEDIDO — C/A, `0x0047E25F–0x0047E477`, tabla de saltos en C `0x0047E8F8`.** Se elige por tipo de joya; los mensajes 600–603 de L (r. 150–153) dicen cuántos puntos cambian en el marcador. Esos puntos **no son GP**.

| Tipo interno | Puntos del marcador | GP personal | Oro base |
|---:|---:|---:|---:|
| 0 | +25 | +2 | +100 |
| 1 | +10 | +1 | +10 |
| 2 | +5 | 0 | +5 |
| 3 | −5 | 0 | 0 |

El GP personal se incrementa sólo para tipos 0 y 1 (`0x0047E3E5–0x0047E477`). El puntaje por equipo se actualiza aparte (`0x0047E47C–0x0047E527`). Además está el bono de victoria de la sección 2, condicionado a llegar a 100 puntos. No encontré una tabla distinta por tamaño para cada joya.

## 6. Abandono, desconexión y empate

**MEDIDO.** L, mensaje 245, r. 46: la rendición advierte **100 oro por compañero**. El cliente contiene estas dos rutas:

| Ruta | Cambio de oro del que sale | Compañeros |
|---|---|---|
| Participante con entrada válida en el estado de salida | `−100 × (trunc(N/2)−1)` | +100 a cada compañero participante distinto del que salió |
| Otra salida en Score, antes del cierre | `−100 × trunc(N/2)` | +100 a cada compañero participante distinto del que salió |

Direcciones C/A: `0x004CFFBF–0x004D011A` y `0x004D011F–0x004D0240`. El bono del compañero imprime ID 641, «Team Penalty Bonus» (L, r. 191). `N` es el contador usado para el tamaño de la partida. **INFERIDO:** la primera coincide con la compensación normal por rendirse en equipos equilibrados: 0/100/200/300 G de penalización en 1/2/3/4 jugadores por lado. La segunda depende del estado previo y del modo Score; no la generalizaría a toda desconexión ni la sumaría a la primera.

**No quedó determinada una penalización única de GP por salir antes**, ni se auditó todo el tratamiento de cortes de red del servidor. Estas cifras son cambios de acumulador del cliente; la conservación del resultado del ausente depende del estado que conserve el servidor. El Serv2 nativo guarda también muerte/causa y puede completar el log de slots que ya no están conectados (`S2 0x004114DA–0x0041152A`).

**MEDIDO.** En empate el byte de resultado de cada registro es 2 (`0x004150CC–0x004150DE`). En victoria/derrota usa 1/0. No aparece un bono fijo de empate en el bloque de cierre: siguen existiendo los acumulados por acciones y penalizaciones.

## 7. Porcentajes: avatar, bonificaciones y factores del login

**MEDIDO.** El oro de muchas acciones se calcula primero así, con división entera con signo:

```text
oro_de_la_accion = trunc(base × (100 + extra_oro_del_jugador) / 100)
```

`extra_oro_del_jugador` está en el objeto `G+0x262A0+0x40×slot`; 100 es la constante en `0x005CF1B4`. Ejemplos: `0x004D2CA4–0x004D2CD2`, `0x004DA2B9–0x004DA2D3`. **INFERIDO:** es la bonificación personal de oro usada por avatar/estado del jugador; no reconstruí todos sus productores ni cada ítem. Puede afectar también penalizaciones, porque esas ramas usan el mismo cálculo con base negativa.

Después del bono de victoria, el cierre hace estas etapas (`0x00410946–0x00410D9F`):

1. Arma extras de GP y oro desde `G+0x7746C` y `G+0x77474`; una selección adicional puede aportar extras desde `0x008F3F94` (`0x00410980–0x004109C4`). Su catálogo completo de condiciones no quedó reconstruido.
2. **Sólo si el acumulado es positivo**, agrega `trunc(acumulado × extra / 100)`: oro en `0x00410A48–0x00410A81`, GP en `0x00410ADC–0x00410B13`.
3. **Sólo si sigue siendo positivo**, aplica el factor de login: oro × `G+0x1FEC4` /100 y GP × `G+0x1FEBC` /100 (`0x00410B6E–0x00410BC1`, `0x00410C1B–0x00410C6C`).
4. Hay otra rama, bajo un flag por slot, que suma 10% de oro y 20% de GP y limita el resultado a no negativo (`0x00410C71–0x00410D88`). **No quedó identificado con certeza el nombre comercial de ese flag.** No lo confundí con el factor general de login.

**MEDIDO.** El `% GP / % oro` del login es un **factor total**: 100 significa ×1, 200 ×2 y 300 ×3. No es «100 puntos extra de GP». El cliente lee los tres primeros DWORD del tramo descifrado de `0x1012` así:

| Offset dentro del tramo descifrado | Campo | Destino y lectura C/A |
|---:|---|---|
| +0 | Máscara de funciones | `G+0x1FEB4`, `0x004F2418–0x004F2461` |
| +4 | Factor GP | `G+0x1FEBC`, `0x004F2466–0x004F24B9` |
| +8 | Factor oro | `G+0x1FEC4`, `0x004F24BE–0x004F2510` |

LAB, renglones **1048–1064**, ya construye el login Legacy con ambos factores en **100**, en el tramo cifrado que agrega después del prefijo de 89 bytes. El cierre omite multiplicar acumulados negativos por estos factores. El redondeo importa: se trunca en etapas, no se conserva un decimal hasta el final.

**Consecuencia INFERIDA para el server Python:** si acreditás los deltas recibidos en `0x4412`, **no vuelvas a multiplicarlos por ScoreFactor/GoldFactor**. El cliente ya aplicó los factores del login. Aplicarlos otra vez duplica el aumento.

## 8. Comparación de fuentes y relación con Softnyx

| Fuente | Qué número aporta realmente | Evaluación |
|---|---|---|
| C v179, acumuladores | Victoria 3/6/9/12 GP y 100/150/200/300 G; acciones de las tablas anteriores | Evidencia directa para este cliente |
| C v179, aviso de victoria | Primera fila 0 GP / 20 G | Discrepa con su propio cierre; no sirve como tabla única |
| PY, r. 1264–1269 | `0x4413` vacío para todos; **no calcula ni acredita GP/oro** | No aporta una tabla alternativa |
| LAB, r. 1438–1443 | Mismo comportamiento sin premio | Confirma el faltante actual |
| Configuración V585, Server8360 | GoldFactor=100, ScoreFactor=100, r. 90–91 | Factor normal ×1; no es una tabla de acciones |
| Configuración Perú, Serv01/02 | 200/200, r. 70–71 de cada `setting.txt` | ×2, configuración privada |
| Configuración Perú, Serv03/04 | 300/300, r. 70–71 de cada `setting.txt` | ×3, configuración privada |
| Configuración FWC, Server8360/61 | 200/200, r. 82–83 de cada `Setting.txt` | ×2, configuración privada |
| SQL y respaldos | Saldos, estadísticas, snapshots y deltas; sin tabla de tarifas identificada | No respaldan afirmar otro premio por ganar/perder |

Rutas exactas de configuraciones: son los archivos `setting.txt`/`Setting.txt` **al lado del ejecutable de cada instancia**, según las rutas S3, V585 y FWC de la sección 1; para las otras instancias se reemplaza únicamente `GunBoundServ01` por `GunBoundServ02/03/04`, o `Server8360` por `Server8361/62/63`. V585 Server8361/62/63 también usa 100/100, r. 88–89. S3 carga las opciones con valor por defecto **100** en `0x00403B44–0x00403B69`.

**INFERIDO — cuál se parece al original.** La familia de reglas del cliente y la configuración ×1 conservada en V585 son una referencia más cercana a una economía clásica que las configuraciones privadas ×2/×3. Pero **no hay aquí una muestra certificada, sin modificaciones, del cliente y servicio original de Softnyx de la misma versión**. El nombre `SoftnyxDB.rar` no certifica el origen de una fórmula; su SQL no la trae. No sería honesto declarar que la tabla de Legacy es exactamente la de todas las épocas de Softnyx. Lo que sí queda sustentado es la tabla que ejecuta este v179 en disco y cómo la recibe Serv2.

## 9. `0x4412`: formato y origen de cada número

### Construcción del cliente

**MEDIDO — C/A, función `0x00414C80–0x00415158` (A, r. 26281–26567).** Usa el header clásico de 6 bytes y después cifra el cuerpo. El cuerpo **antes de cifrar** es:

```text
u16_le cantidad
repetir cantidad veces:
    u8     slot
    i32_le oro_delta
    i16_le evento_delta
    i16_le gp_delta
    u32_le tiros
    u32_le dano
    u8     resultado       # 0 pierde, 1 gana, 2 empate
```

Cada registro ocupa **18 bytes**, sin padding entre campos. `evento_delta` es un campo aparte; no hay que sumarlo como si fuera otro GP.

| Offset en registro | Campo | Origen leído en C/A |
|---:|---|---|
| +0 | Slot 0..7 | Índice del bucle; sólo incluye slots con flag `G+0x26135+slot` activo; `0x00414D51–0x00414D6D` |
| +1 | Oro delta con signo | Objeto `G+0x26BC0+8×slot`, handle en +4; `0x00414D73–0x00414DB2` |
| +5 | Delta de evento con signo | Selección por WORD `G+0x77454`: desactivado/otro → 0; casos 1/2 comparan acumulados por equipos; caso 0 usa dato del ganador, perdedor `0xFFFF`; `0x00414DB8–0x00414FF3` |
| +7 | GP delta con signo | Objeto `G+0x26C00+8×slot`; `0x00414FFA–0x00415032` |
| +9 | Tiros | Objeto `G+0x26D00+8×slot`; `0x00415039–0x00415078` |
| +13 | Daño | Objeto `G+0x26C40+8×slot`; `0x0041507E–0x004150BE` |
| +17 | Resultado | Compara equipo del slot con `G+0x26D78`; si ganador=FF escribe 2; `0x004150CC–0x004150F5` |

**MEDIDO.** Los acumuladores son objetos protegidos en memoria, no enteros directamente legibles en el campo del handle. El cliente los extrae mediante `0x004C66D0` y `0x00403240` antes de escribir enteros ordinarios en el paquete. La función `0x00416A30` decodifica constantes con XOR `0xEEAEAEC0`. Por ejemplo, `0xEEAEAEA4` es 100 y `0x1151510E` es −50. Leer esos hexadecimales como premios sin hacer el XOR daría números absurdos.

El WORD de selección `G+0x77454` viene del tramo posterior a los jugadores en el inicio de partida (`0x004ED4B4–0x004ED4D2`), con `FFFF` como desactivado. **INFERIDO:** es selección de evento; no es el modo Solo/Score/Tag/Jewel. No quedó reconstruida toda la semántica de sus casos. El servidor registra estos valores en `EventScore`, separados de `TotalScore`/GP.

### Cifrado y tamaños

**MEDIDO.** `0x00415113` llama `0x00445C20` con desplazamiento 0: cifra todo el payload. Esa rutina redondea a bloques de **12 bytes útiles → 16 cifrados** (`0x00445C4A–0x00445CBC`, auxiliares `0x004B7800`, `0x004B7960`). Se conserva sin cifrar el header de 6 bytes.

| Registros | Cuerpo útil | Cuerpo cifrado esperado | Paquete con header |
|---:|---:|---:|---:|
| 2 | 38 | 64 | 70 |
| 4 | 74 | 112 | 118 |
| 6 | 110 | 160 | 166 |
| 8 | 146 | 208 | 214 |

Los tamaños son **derivación MEDIDA del layout y del redondeo**, no capturas. El descifrado puede devolver padding: no interpretarlo como jugadores extra. Usar la rutina de sesión ya existente con opcode `0x4412` y el buffer después del header, por ejemplo `Session.decrypt(packet[6:], 0x4412)` según la interfaz de los emuladores.

**MEDIDO, cotejo independiente en Serv2:** S2 `0x004146C6–0x004147AB` descifra el cuerpo y lee exactamente slot/DWORD/WORD/WORD/DWORD/DWORD/BYTE. Lo convierte a una estructura interna de 24 bytes por alineación; **24 no es el tamaño de registro en la red**. Pasa a `SaveResult`, `0x00411140`. S3 también reconoce ese prefijo de registros en `0x00429FAD–0x0042A091`, pero su almacenamiento y procesamiento por jugador/sala son distintos; compartir opcode no certifica compatibilidad completa con WC.

### Quién lo manda y qué recibe

**MEDIDO.** Los emuladores documentan que lo solicita el host/llave (PY r. 1266; LAB r. 1440). En C/A hay chequeos del identificador local contra el identificador de llave antes de llamar a `0x00414C80` (`0x00410DB0–0x00410F0A`, `0x004D3AB2–0x004D3B0A`). No es una solicitud independiente de premio de cada jugador.

**MEDIDO.** Serv2, después de guardar el resultado, recorre ocho slots conectados y manda **`0x4413` sin un cuerpo de GP/oro** (`S2 0x0041167A–0x0041169A`). Los dos emuladores hacen lo mismo. El handler de recepción del cliente, `0x004D0F72–0x004D0FB0`, marca que llegó el cierre y llama a la ventana de resultado; no lee una tabla de premios del payload. La ventana dibuja sus acumuladores locales: oro `0x00519A00–0x00519ADF`, GP `0x00519B32–0x00519C03` y el bloque equivalente del otro equipo en `0x005192F3–0x00519810`.

**INFERIDO para implementación:** la pantalla puede mostrar ganancias aunque el servidor no haya acreditado nada. Mandar `0x4413` sólo arregla la transición visual; no la persistencia. El retorno a sala ya tiene otro intercambio, `0x3232 → 0x3233` (PY r. 1232–1237). La corrección del saldo debe comprobarse también al volver a entrar o consultar datos de usuario.

## 10. Topes: distinguir premio, umbral de log y rechazo

**MEDIDO.** Los límites encontrados son controles de deltas anormales **por resultado/partida**, no una fórmula que recorta todo premio hasta un máximo.

| Fuente | Umbral de registro de anomalía | Umbral alto de rechazo | Umbral negativo |
|---|---|---|---|
| Serv2 | GP >30 **o** oro >5000 | GP >50 **o** oro >20000 | No encontré un límite negativo en este control |
| Serv3 Perú / FWC / V585 | GP >30 **o** oro >3000 | GP >50 **o** oro >6000 | GP <−100 **o** oro <−2500 provoca salida por la rama negativa |

Serv2: `0x00411225–0x004112C9`. Usa comparaciones con signo; **30/5000** no supera el umbral de log, **50/20000** no supera el de rechazo. Al superar el umbral alto toma la salida anticipada `0x004113B2`; no vi un `min(premio, tope)`.

Serv3: valores por defecto leídos de configuración en `0x00403CA5–0x00403D33`:

| Opción | Defecto |
|---|---:|
| `ANU_WRITELOG_GP` | 30 |
| `ANU_WRITELOG_GOLD` | 3000 |
| `ANU_DROP_GP` | 50 |
| `ANU_DROP_GOLD` | 6000 |
| `ANU_DROP_GP_NEG` | −100 |
| `ANU_DROP_GOLD_NEG` | −2500 |

El uso está en `0x00418CA4–0x00418CDC` y `0x00418FCC–0x004190E2`. La rama negativa registra y corta el procesamiento; la positiva de rechazo conduce al tratamiento de descarte/desconexión. Estos valores se cotejaron en las tres variantes Serv3. En las configuraciones revisadas no aparecieron overrides `ANU_*`; son los defaults del binario. Las opciones `GradeLimitFirst/Last` limitan rangos de acceso, no el GP ganable.

**No quedó demostrado un tope diario de GP ni de oro.** No encontré un contador diario ni una fórmula de recorte diario en las rutas revisadas, en las configuraciones de juego ni en las tablas de juego examinadas. Eso **no prueba que jamás haya existido** una política diaria en otro servicio o versión. L, r. 537, habla de actualizar el *ranking* una vez por día: no equivale a limitar las ganancias diarias.

## 11. Dónde se acredita y qué falta en Python

**MEDIDO.** SQL2, r. **213–246**, define `game.Money`, `TotalScore`, `SeasonScore`, `AccumShot` y `AccumDamage`. Su `playlog`, r. **493–548**, guarda por slot `ScoreDelta` y `MoneyDelta`, además de equipo y causa de muerte. Son destinos de persistencia; no una tabla de tarifas.

Serv2 prepara el registro de actualización y lo manda al Center con comando interno **`0xD012`** (`S2 0x0041140B–0x004114A7`). CT2 contiene en VA **`0x0043E038`** el SQL que incrementa Money, TotalScore, SeasonScore, AccumShot y AccumDamage. Serv3 contiene los fragmentos equivalentes en `0x0046B3D0–0x0046B438`. No hace falta un procedimiento almacenado oculto para explicar el premio observado en estos archivos.

**MEDIDO.** PY r. **1264–1269** y LAB r. **1438–1443** no descifran ni guardan el resultado: sólo responden. Además, la construcción **genérica** del login de LAB usa GP de ejemplo **888888** en r. **1034–1035**; la rama Legacy **reemplaza ese buffer** por otro de 89 bytes en r. **1048–1064**. Por eso esos 888888 no demuestran qué GP recibe v179 ni constituyen una regla de economía. Los saldos reales y el layout particular del login deben mantenerse coherentes al implementar persistencia.

**INFERIDO — cambio concreto para implementar después, sin tocar fuentes en este encargo:**

1. Descifrar `0x4412`, validar cantidad, longitud y slots, y asociar cada slot a los participantes de esa partida y su llave vigente.
2. Leer `oro_delta` como **i32** y `gp_delta` como **i16**; mantener `evento_delta` aparte. Son deltas, no saldos finales.
3. Acreditar una sola vez por partida, de forma atómica, a Money/GP total/GP de temporada y estadísticas; conservar el resultado incluso si después se repite el paquete. Los factores de login ya están aplicados.
4. Aplicar conscientemente los controles elegidos para el server propio. Los umbrales de las copias antiguas sirven como referencia de validación; no son una razón para transformar cualquier premio alto en 50 GP.
5. Mandar `0x4413` a los participantes y verificar que las consultas siguientes devuelvan el saldo acreditado. El GP dibujado por el cliente no demuestra que se haya guardado.

Se dejó **`parser_4412_referencia.py`**: interpreta únicamente el cuerpo ya descifrado, sin red ni acreditación. Se verificó con **21 comprobaciones sintéticas**: tamaños de 1 a 8 registros, padding, valores negativos y rechazo de cuerpos inválidos. No reemplaza una captura real del cliente ni simula toda la partida.

## 12. Alcance, trazabilidad y archivos entregados

**MEDIDO.** El SHA256 del ejecutable analizado es `d03e0afed3890595c1ae16a5c64b2481f01ab9caef79c7d37faccbf5cd62b8ca`, coincidente con la muestra identificada en el análisis previo. El de S2 es `cc672b48db972f79870473b229c3667a75137e69cca4ecff2ea394a4f03e2c7c`; S3 Perú `6bd1fefec55e41bd17c1ae1f815e598c66ccec89be7bdf3450b38722e485bc20`; V585 `e86bdd1741f638ed21e57e4cc4294bcbd78b96179c8bf5d46071fa014b4763bc`; FWC `c93b4adf3c4692277b0458313e4ab053ab6c8f01864aeee6239b5293da622ee6`.

El cliente original carga `C:\GunBound-Legacy\DualSoft.dll`, que es una extensión posterior. Se encontraron controles de bonos GM/overlays y un observador de textos de bonos: cadenas en VA `0x102CC0C0`, `0x102CC0D8`, `0x102CC4F8`, `0x102CC820`; listado `D:\Gunbound\Legacy-Analisis\DualSoft.dll.asm.txt`, referencias `0x10122952`, `0x101229B4`, `0x10128AE1`, `0x10129121`. **No se auditó exhaustivamente cada hook de esa DLL ni se midió su efecto en ejecución.** Las tablas de este informe describen las instrucciones del ejecutable en disco; un bono GM o un hook activo exige comprobación aparte. No atribuí esos overlays a Softnyx.

En esta carpeta quedaron:

- `INFORME.md`: este informe.
- `parser_4412_referencia.py`: parser de cuerpo descifrado y verificaciones sintéticas.
- `investigar.py`: extractor de fragmentos por VA, cadenas de juego, constantes y `language.txt`; sólo usa la biblioteca estándar. La lectura del XFS se adaptó del extractor indicado en el encargo para escribir acá.
- `inventario.py` / `inventario_fuentes.json`: rutas, hashes de binarios y opciones de juego; no contiene filas de usuarios.
- `muestras_sha256.json`: tamaños y hashes de las muestras principales.
- `language_extraido.txt`: textos de interfaz del cliente, sin cuentas.
- `serv2_disasm.txt`, `serv3_disasm.txt`, `serv3_v585_disasm.txt`, `serv3_fileswc_disasm.txt`: desensamblados estáticos hechos con el `dumpbin.exe` ya instalado. No se ejecutaron esos binarios del juego.

**Pendientes de certeza histórica, no datos inventados:** premio específico por primer golpe/distancia/rango; catálogo de todos los extras de ítems y flags; política universal de desconexión y límites diarios; efecto de todos los hooks de Legacy; certificación de la misma tabla en el Softnyx original. Para acreditar en el Python de este v179, en cambio, el layout y los deltas recibidos permiten avanzar sin esperar a reconstruir todas esas reglas desde cero.
