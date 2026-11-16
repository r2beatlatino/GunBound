# GunBound Legacy: arte de carga y arranque

Trabajo terminado el 16/11/2026. **Se puede rearmar el XFS.** Dejé `graphics_nuevo.xfs` con arte histórico de GIS/WC 557 en cinco recursos: los dos logos, el título, el fondo de carga y el fondo del selector. Las demás entradas quedaron idénticas. Para reducir el arranque a una pantalla hace falta cambiar el flujo del EXE; dejé la propuesta con direcciones y bytes, **sin aplicarla**.

No ejecuté el juego, sus DLL ni los instaladores. No escribí en `C:\GunBound-Legacy\`, `D:\Gunbound\` ni en `..\comun\`. Los resultados y scripts están dentro de esta carpeta:

`C:\Users\benja\Desktop\Servidor R2Beat 2013\_trabajo\codex\gunbound\carga\`

## MEDIDO — qué mirar primero

- [COMPARACION_arranque.png](COMPARACION_arranque.png): Legacy a la izquierda, GIS/WC 557 a la derecha; logos, título, carga y selector.
- [LEGACY_pantallas.png](LEGACY_pantallas.png): pantallas completas, publicidades y recursos de carga antiguos.
- [LEGACY_mapas.png](LEGACY_mapas.png): los dos cuadros de cada `load_stage00..21.img`.
- [LEGACY_cuadros_auxiliares.png](LEGACY_cuadros_auxiliares.png): indicadores, botones y cuadros secundarios.
- [ORIGINALES_GIS557.png](ORIGINALES_GIS557.png): recursos históricos de referencia.
- [inventario_carga.csv](inventario_carga.csv): nombres exactos, bytes, **dimensiones de todos los cuadros**, fuente y comparación individual. [inventario_legacy.json](inventario_legacy.json) agrega flag y bytes de cada cuadro. Los cuadros individuales están en `png\`; los IMG extraídos, en `legacy\`.

Las hojas son de recursos: no son capturas del juego en ejecución. El magenta indica transparencia del recurso, no un fondo que necesariamente se vea jugando. `serverlist_back.img` tiene una segunda variante de píxeles en su primer cuadro; el lector de IMG salta esa variante para ubicar correctamente los diez cuadros. No se la contó como otra pantalla.

## MEDIDO — imágenes y tamaños

Origen de todos estos nombres: `C:\GunBound-Legacy\graphics.xfs`. Los bytes de IMG son descomprimidos; la columna XFS es el tamaño ocupado por sus bloques. La dimensión indicada es la del primer cuadro; el CSV detalla los demás.

| Nombre dentro del XFS | Bytes IMG | Bytes XFS | Cuadros | Primer cuadro | Comparación |
| --- | ---: | ---: | ---: | --- | --- |
| `load_back.img` | 1,039,206 | 150,638 | 14 | 800×600 | alternativa histórica del mismo slot; distinto |
| `load_back1.img` | 1,039,206 | 85,563 | 14 | 800×600 | idéntico byte a byte (nombre distinto) |
| `loading_ad.img` | 2,944,168 | 811,886 | 4 | 800×460 | idéntico a Lima; origen oficial no establecido |
| `loadmode.img` | 1,159,764 | 188,161 | 27 | 800×600 | idéntico byte a byte |
| `loadstage.img` | 7,262,144 | 1,685,612 | 22 | 748×228 | idéntico byte a byte |
| `logo.img` | 964,848 | 50,838 | 1 | 800×600 | alternativa histórica del mismo slot; distinto |
| `logomode.img` | 964,848 | 117,444 | 1 | 800×600 | alternativa histórica del mismo slot; distinto |
| `logomode2.img` | 960,048 | 7,692 | 1 | 800×600 | idéntico byte a byte |
| `server_back.img` | 389,540 | 136,171 | 1 | 800×600 | idéntico byte a byte |
| `server_list.img` | 715,130 | 45,237 | 12 | 546×530 | idéntico byte a byte |
| `serverlist_back.img` | 2,355,786 | 358,795 | 10 | 800×600 | alternativa histórica del mismo slot; distinto |
| `serverlist_rank_minus.img` | 24,916 | 6,988 | 26 | 27×17 | idéntico byte a byte |
| `serverlist_rank_plus.img` | 24,916 | 7,022 | 26 | 27×17 | idéntico byte a byte |
| `servermode.img` | 1,124,676 | 199,903 | 19 | 800×600 | idéntico byte a byte |
| `title.img` | 964,848 | 184,595 | 1 | 800×600 | alternativa histórica del mismo slot; distinto |
| `titlemode.img` | 960,048 | 244,697 | 1 | 800×600 | idéntico byte a byte |

Los logos y título con marca **Legacy** se ven en `logomode.img`, `logo.img` y `title.img`. El selector también lleva un logo Legacy en `serverlist_back.img`. `load_back.img` tiene otro fondo y el texto “OPCIONES DE SALA”; el `load_back1.img` conservado en el mismo XFS coincide exactamente con el `load_back.img` de GIS557.

**Las cuatro publicidades de `loading_ad.img` no fueron retocadas por Legacy respecto de la copia Lima 1.5: son idénticas byte a byte.** Se comparan en [loading_ad.png](comparaciones/loading_ad.png). Eso prueba que ya estaban en ese otro cliente, pero no certifica que sean originales oficiales de Softnyx: Lima es una distribución privada y tiene otras marcas cambiadas. No encontré `loading_ad.img` en los cuatro GIS/GLS antiguos extraídos. Como alternativa de carga con arte histórico, dejé [loading_ad_alternativa_oficial.png](comparaciones/loading_ad_alternativa_oficial.png), que muestra cada aviso frente al fondo de carga de GIS557 completo. Tiene otro tamaño y otra función de composición; **no es un original exacto ni un reemplazo binario directo**. No inventé una versión “limpia”.

Cada `load_stageNN.img` tiene **469.832 bytes**, dos cuadros RGB565 de **748×157**. La referencia es `originales\GIS557\` con el mismo nombre; el PNG de cada fila muestra **ambos** cuadros lado a lado:

| Archivo | Bytes XFS Legacy | Resultado | Comparación |
| --- | ---: | --- | --- |
| `load_stage00.img` | 118,152 | Igual al GIS557, ambos cuadros. | [PNG](comparaciones/load_stage00.png) |
| `load_stage01.img` | 109,261 | Igual al GIS557, ambos cuadros. | [PNG](comparaciones/load_stage01.png) |
| `load_stage02.img` | 112,176 | Igual al GIS557, ambos cuadros. | [PNG](comparaciones/load_stage02.png) |
| `load_stage03.img` | 125,323 | **Sin original exacto hallado**; alternativa GIS557, cambia el mapa. | [PNG](comparaciones/load_stage03.png) |
| `load_stage04.img` | 120,329 | Igual al GIS557, ambos cuadros. | [PNG](comparaciones/load_stage04.png) |
| `load_stage05.img` | 118,050 | Igual al GIS557, ambos cuadros. | [PNG](comparaciones/load_stage05.png) |
| `load_stage06.img` | 140,344 | Igual al GIS557, ambos cuadros. | [PNG](comparaciones/load_stage06.png) |
| `load_stage07.img` | 110,110 | Igual al GIS557, ambos cuadros. | [PNG](comparaciones/load_stage07.png) |
| `load_stage08.img` | 96,248 | Igual al GIS557, ambos cuadros. | [PNG](comparaciones/load_stage08.png) |
| `load_stage09.img` | 87,781 | Igual al GIS557, ambos cuadros. | [PNG](comparaciones/load_stage09.png) |
| `load_stage10.img` | 123,511 | Igual al GIS557, ambos cuadros. | [PNG](comparaciones/load_stage10.png) |
| `load_stage11.img` | 118,147 | Igual al GIS557, ambos cuadros. | [PNG](comparaciones/load_stage11.png) |
| `load_stage12.img` | 104,081 | **Sin original exacto hallado**; alternativa GIS557, cambia el mapa. | [PNG](comparaciones/load_stage12.png) |
| `load_stage13.img` | 158,361 | **Sin original exacto hallado**; alternativa GIS557, cambia el mapa. | [PNG](comparaciones/load_stage13.png) |
| `load_stage14.img` | 111,587 | Igual al GIS557, ambos cuadros. | [PNG](comparaciones/load_stage14.png) |
| `load_stage15.img` | 150,223 | Igual al GIS557, ambos cuadros. | [PNG](comparaciones/load_stage15.png) |
| `load_stage16.img` | 110,333 | **Sin original exacto hallado**; alternativa GIS557, cambia el mapa. | [PNG](comparaciones/load_stage16.png) |
| `load_stage17.img` | 133,256 | **Sin original exacto hallado**; alternativa GIS557, cambia el mapa. | [PNG](comparaciones/load_stage17.png) |
| `load_stage18.img` | 155,803 | **Sin original exacto hallado**; alternativa GIS557, cambia el mapa. | [PNG](comparaciones/load_stage18.png) |
| `load_stage19.img` | 115,141 | Igual al GIS557, ambos cuadros. | [PNG](comparaciones/load_stage19.png) |
| `load_stage20.img` | 104,896 | Igual al GIS557, ambos cuadros. | [PNG](comparaciones/load_stage20.png) |
| `load_stage21.img` | 149,866 | **Sin original exacto hallado**; alternativa GIS557, cambia el mapa. | [PNG](comparaciones/load_stage21.png) |

También busqué coincidencia visual de ambos cuadros de esos siete mapas distintos en GIS427, GIS545, GIS557, GLS458 y Lima: ninguna fue exacta. [MAPAS_alternativas.png](MAPAS_alternativas.png) muestra las variantes del mismo slot. Para `load_stage16.img`, Lima es visualmente más cercana al terreno de Legacy, aunque tampoco es idéntica; las demás referencias WC de la tabla son alternativas por posición en el cliente y, en varios casos, representan otro escenario. No corresponde venderlas como una reconstrucción del mismo mapa sin editar. No las incluí como reemplazos: cambiar una miniatura por otro mapa puede dejarla desfasada con el escenario real.

`loadstage.img` es otro recurso, sin guion bajo: contiene **22 cuadros de 748×228**, alternando ilustraciones y perfiles de terreno. Coincide completo con GIS557. No hay que confundirlo con los 22 archivos `load_stageNN.img`. `loadmode.img`, `titlemode.img` y `servermode.img` conservan interfaces de la familia anterior; que estén presentes no demuestra que formen parte del arranque actual.

No hay archivos `.jpg`, `.bmp`, `.tga`, `.avi` o `.mpg` con esas extensiones dentro del índice de `graphics.xfs`.

## INFERIDO — alternativas visuales cuando falta el mismo mapa

Además de la comparación por slot, elegí estas aproximaciones por tema y aspecto entre las referencias extraídas. Es una selección visual, no una prueba de parentesco ni de geometría. Ninguna se instaló en el XFS nuevo. Para las fuentes GIS557, el arte sale del instalador 557 identificado más abajo; Lima se mantiene claramente rotulada como copia privada.

| Recurso Legacy | Referencia más parecida elegida | Motivo y límite | Comparación |
| --- | --- | --- | --- |
| `load_stage03.img` | `originales\GIS557\load_stage00.img` | ambiente oscuro con criaturas; no aparece la serpiente de Legacy | [PNG](comparaciones_parecidas\load_stage03.png) |
| `load_stage12.img` | `originales\GIS557\load_stage09.img` | ambiente espacial/nocturno y estructuras mecánicas | [PNG](comparaciones_parecidas\load_stage12.png) |
| `load_stage13.img` | `originales\GIS557\load_stage15.img` | piedra, vegetación y relieve exterior; otra geometría | [PNG](comparaciones_parecidas\load_stage13.png) |
| `load_stage16.img` | `originales\setup_LimaWC_1.5\load_stage16.img` | mismo tema y terreno muy parecido; distribución privada, sin origen oficial certificado | [PNG](comparaciones_parecidas\load_stage16.png) |
| `load_stage17.img` | `originales\GIS557\load_stage17.img` | ruinas y piezas doradas; otra variante del terreno | [PNG](comparaciones_parecidas\load_stage17.png) |
| `load_stage18.img` | `originales\GIS557\load_stage18.img` | arquitectura de templo; no conserva las columnas sobre lava | [PNG](comparaciones_parecidas\load_stage18.png) |
| `load_stage21.img` | `originales\GIS557\load_stage04.img` | paisaje exterior rocoso con vegetación; otro escenario | [PNG](comparaciones_parecidas\load_stage21.png) |

Se pueden revisar todas las miniaturas de la referencia principal en [GIS557_miniaturas.png](GIS557_miniaturas.png).

## MEDIDO — de dónde salen las referencias

Instaladores usados, todos leídos como datos:

- `D:\Gunbound\GB\GBWC\Gunbound GIS_WC\Gunbound_GIS_WC_557.exe`
- `D:\Gunbound\GB\GBWC\Gunbound GIS_WC\Gunbound_GIS_WC_545.exe`
- `D:\Gunbound\GB\GBWC\Gunbound GIS_WC\Gunbound_GIS_WC_427.exe`
- `D:\Gunbound\GB\GBWC\Gunbound GIS_WC\Gunbound_GLS_WC_458.exe`
- `D:\Gunbound\GB\GBWC\Gunbound WEB\setup_LimaWC_1.5.exe`

El 557 declara Inno Setup 5.1.7. El stream LZMA que empieza en **offset 1.005.817** contiene el XFS gráfico; el índice incluye 4.146 entradas. Lima usa un stream sólido: empieza en **58.880** y el XFS gráfico empieza en **3.040.837 dentro de lo descomprimido**. Son offsets de archivo/stream, no direcciones del EXE cargado.

| Cliente | Copia exacta del contenedor extraído dentro de esta carpeta | Entradas | Marca |
| --- | --- | ---: | --- |
| Gunbound_GIS_WC_427 | `C:\Users\benja\Desktop\Servidor R2Beat 2013\_trabajo\codex\gunbound\carga\clientes\Gunbound_GIS_WC_427\stream_421454.xfs` | 2,907 | XFS2 |
| Gunbound_GIS_WC_545 | `C:\Users\benja\Desktop\Servidor R2Beat 2013\_trabajo\codex\gunbound\carga\clientes\Gunbound_GIS_WC_545\stream_720520.xfs` | 3,913 | XFS2 |
| Gunbound_GIS_WC_557 | `C:\Users\benja\Desktop\Servidor R2Beat 2013\_trabajo\codex\gunbound\carga\clientes\Gunbound_GIS_WC_557\stream_1005817.xfs` | 4,146 | XFS2 |
| Gunbound_GLS_WC_458 | `C:\Users\benja\Desktop\Servidor R2Beat 2013\_trabajo\codex\gunbound\carga\clientes\Gunbound_GLS_WC_458\stream_354114.xfs` | 3,382 | XFS2 |
| setup_LimaWC_1.5 | `C:\Users\benja\Desktop\Servidor R2Beat 2013\_trabajo\codex\gunbound\carga\clientes\setup_LimaWC_1.5\solid_58880_3040837_graphics.xfs` | 16,915 | XFS2 |

`originales\GIS557\NOMBRE.img` es la referencia principal, extraída de `clientes\Gunbound_GIS_WC_557\stream_1005817.xfs`. Las carpetas `originales\Gunbound_GIS_WC_427\`, `originales\Gunbound_GIS_WC_545\`, `originales\Gunbound_GIS_WC_557\`, `originales\Gunbound_GLS_WC_458\` y `originales\setup_LimaWC_1.5\` conservan las otras variantes con sus nombres internos. La tabla del CSV identifica la fuente elegida para **cada** recurso. `load_back1.img` se compara con el nombre histórico `load_back.img`; `loading_ad.img`, con Lima.

Los cuatro clientes GIS/GLS coinciden byte a byte entre sí en `logo.img` y `title.img`. GIS427/545/557 también coinciden en `logomode.img`; GLS458 tiene una variante. Eso respalda usar ese arte histórico sin la marca Legacy. No se verificó una firma del editor del instalador ni una cadena de autenticidad oficial.

Evidencia: [fuentes.json](fuentes.json) trae tamaños y SHA256 de los contenedores; [contraste_clientes.json](contraste_clientes.json), 179 comparaciones por nombre; [comparacion.json](comparacion.json), hashes y tamaños frente a GIS557. Los scripts de extracción son `extraer_inno.py` y `extraer_solid.py`; no lanzan los instaladores. También se inspeccionaron los paquetes Thor/Perú/Classic y recursos sueltos del respaldo; no se obtuvo de ellos un original exacto adicional utilizable. No se afirma haber abierto todos los RAR internos del catálogo.

## MEDIDO — recorrido del arranque en el EXE

Muestra: `C:\GunBound-Legacy\GunBound.exe`, SHA256 `d03e0afed3890595c1ae16a5c64b2481f01ab9caef79c7d37faccbf5cd62b8ca`, base preferida **0x00400000**. Las direcciones VA siguientes usan esa base. Los recortes están en [arranque_evidencia.asm.txt](arranque_evidencia.asm.txt), sacados por rangos y búsquedas de `D:\Gunbound\Legacy-Analisis\GunBound.exe.asm.txt`.

| Orden normal | Estado | Recurso / audio | Evidencia estática |
| --- | --- | --- | --- |
| 1 | 5, GLogoMode | `graphics.xfs:logomode.img`, cuadro 0; `sound.xfs:logo.mp3` | Entrada inicial `0x0040C7EA: mov eax,5`; carga en `0x004AB4D1`; audio en `0x004AB4E9`; actualización `0x004AB5E0`, al contador 40 solicita estado 6. |
| 2 | 6, GXPLogo2Mode | `graphics.xfs:logo.img`, cuadro 0; el código pide `logo2.mp3`, ausente del índice de sonido | Carga en `0x004CF561`; actualización `0x004CF590`, al contador 60 solicita estado 1. |
| 3 | 1, GXPTitleMode | `graphics.xfs:title.img`, cuadro 0; `sound.xfs:title.mp3` | Carga en `0x004F65A2`; actualización `0x004F6600`, al contador 60 solicita estado 2. |
| Llegada | 2, selector | `graphics.xfs:serverlist_back.img`, controles `b_serverlist_*.img`, `illust.img` | Inicializador `0x004F31A0`; fondo cargado en `0x004F3295`. |

Se revisó el índice de `C:\GunBound-Legacy\sound.xfs` sin extraer ni reproducir audio: `logo.mp3` y `title.mp3` están; `logo2.mp3` no. La llamada al nombre ausente no prueba que se escuche sonido en ese paso. Los estados 5/6/1 dibujan mediante la misma función `0x004AB600`: recurso 0x2710, cuadro 0. Sus tablas virtuales están en `0x0057793C`, `0x00579C7C` y `0x0057A394`. Las altas de los estados están en `0x0040D26C..0x0040D33C`.

Hay una rama alternativa de reinicialización que entra directamente al **estado 6**, en `0x0040C914`, si la inicialización previa devuelve 0x17 y el reintento funciona. En esa rama se omite el estado 5.

`0x004135C0` solicita un cambio; `0x004133E0` hace la salida del estado viejo y la entrada del nuevo. Hay un contador global de transición, comprobado alrededor de `0x00414B13..0x00414B56`, que cambia de estado al alcanzar 11. Por eso el arte y la transición son decisiones separadas del programa.

**`load_back.img` y `load_stage%02d.img` se cargan para la carga de partida**, no son un cuarto paso demostrado antes del selector. La referencia al fondo está en `0x004EE2E1`; los estados/funciones de carga y el título son distintos. Tampoco encontré una referencia literal directa a `logomode2.img`, `titlemode.img` o `loading_ad.img` en `GunBound.exe`. Su presencia no prueba que se muestren ahí; no se descartan nombres construidos dinámicamente o uso por otro componente.

Antes del EXE puede estar el launcher: `C:\GunBound-Legacy\img\login.dat` referencia `frame.bmp` y los BMP de botones/progreso; `NyxLauncher.ini` configura `Url_Notice`. Es una ventana con avisos y descarga, separada de los tres estados del juego. [LAUNCHER_recursos.png](LAUNCHER_recursos.png) e [inventario_launcher.json](inventario_launcher.json) muestran sus recursos sueltos. `img\fondo.jpg` existe, pero su participación en esta secuencia no quedó demostrada. No hay archivos de video en el árbol del cliente inspeccionado.

El directorio de recursos PE de `GunBound.exe` no contiene bitmaps ni películas: tiene cursor, iconos y versión. `DualSoft.dll` sólo expone un manifiesto en su directorio de recursos. No apareció una pantalla de aviso/intro embebida en esos directorios; eso no descarta gráficos construidos por código. Evidencia completa: [recursos_pe.json](recursos_pe.json). No hay una pantalla local GameGuard identificada en este cliente.

## INFERIDO — cómo dejar una sola pantalla

La secuencia reconstruida es **logo Legacy oscuro → logo Legacy blanco → título Legacy → selector**, con posibles fundidos entre estados. Es la explicación estática de las tres o cuatro transiciones reportadas. No es una observación de ejecución y no permite asignar cualquier negro o pausa que hayas visto a un cuarto recurso concreto.

**Sólo datos:** reemplazar los IMG restaura el arte, pero mantiene los estados y sus contadores. Vaciar un IMG no elimina la espera ni el cambio de estado, y puede romper la carga. Poner la misma ilustración en los tres slots unifica la imagen, pero siguen existiendo los cambios y posibles fundidos. No encontré una opción de INI que controle esta cadena; los destinos 6/1/2 están codificados en el EXE.

**Propuesta de parche, no aplicada:** conservar un estado de logo y saltar desde él al selector. Así se conserva la salida normal del estado 5: `0x004AB500` libera el recurso y prepara/envía un paquete 0xA000 cuando hay conexión. Saltar el estado 5 desde la entrada dejaría de ejecutar esa salida; por eso no es la propuesta elegida.

| VA de instrucción | RVA / offset de archivo de esta muestra | Bytes actuales | Bytes propuestos | Efecto |
| --- | --- | --- | --- | --- |
| `0x004AB5EE` | `0x000AB5EE` | `6A 06` (`push 6`) | `6A 02` (`push 2`) | Ruta normal: 5 → 2, omite segundo logo y título. Sólo cambia el byte de `0x004AB5EF`. |
| `0x004CF59E` | `0x000CF59E` | `6A 01` (`push 1`) | `6A 02` (`push 2`) | Ruta alternativa que entra en 6: 6 → 2. Sólo cambia el byte de `0x004CF59F`. |

Los dos pares de bytes se cotejaron contra el binario original y la conversión VA→offset contra sus secciones PE. [parche_propuesto_NO_APLICADO.json](parche_propuesto_NO_APLICADO.json) deja el manifiesto. **No hay un EXE parcheado en la entrega.**

Para que la única pantalla muestre GunBound y no Nexon, `reemplazos_una_pantalla\logomode.img` y `reemplazos_una_pantalla\logo.img` contienen el `title.img` original de GIS557: 800×600, un cuadro. Son una propuesta de reasignación de arte; no se mezclaron en el XFS de restauración histórica. Se puede armar otro XFS combinando esos dos archivos con los otros reemplazos elegidos, siempre dentro de esta carpeta.

El resultado esperado con esas dos modificaciones de flujo y el arte propuesto es **una pantalla WC → selector** para las dos entradas conocidas. Sigue estando la transición hacia el selector. No se propone tocar el gestor global de fundidos porque afectaría más pantallas del juego. La compatibilidad del arranque completo, los hooks de DualSoft y la aceptación del servidor quedan **sin prueba dinámica**, por la prohibición de ejecutar el cliente. No se promete eliminar el launcher, su aviso remoto, una pausa de inicialización o cualquier ventana ajena a estos estados.

## MEDIDO — rearmado y comprobación exhaustiva

Entregables: [rearmar_xfs.py](rearmar_xfs.py), [xfs.py](xfs.py), [extraer_xfs.py](extraer_xfs.py), [verificar_xfs.py](verificar_xfs.py), `reemplazos\` y **[graphics_nuevo.xfs](graphics_nuevo.xfs)**. El escritor usa sólo la biblioteca estándar de Python; las hojas usan Pillow. El script se importa con `xfs.py` al lado.

Ejemplo desde esta carpeta, con un Python 3.9 o posterior:

```powershell
python -B .\rearmar_xfs.py 'C:\GunBound-Legacy\graphics.xfs' .\reemplazos
python -B .\extraer_xfs.py .\graphics_nuevo.xfs logo.img title.img --destino .\comprobacion_manual
python -B .\verificar_xfs.py
```

Python usado acá: `C:\Users\benja\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`, con `-B` para no escribir cachés en carpetas de origen. `--salida` permite otro nombre **dentro de esta carpeta**. El escritor rechaza nombres que no están en el índice, enlaces y destinos externos; nunca permite sobrescribir el original. Recibe IMG/EPA/etc. binarios, no convierte PNG a IMG. Un archivo de cero bytes no es una imagen transparente válida.

El XFS tiene un puntero de 32 bits al índice, cabecera descomprimida FOX7 de 64 bytes y 18.948 entradas de 128 bytes: nombre en 112 bytes y cuatro DWORD (offset, flag, tamaño original, tamaño almacenado). Los bloques admiten zlib y datos crudos, tamaños explícitos menores a 64 KiB y dos bytes auxiliares. El escritor conserva los datos antiguos hasta el índice, agrega los reemplazos y reconstruye cabecera/índice; las entradas intactas conservan offsets y bytes almacenados. No compacta los restos, así que el nuevo archivo puede crecer. El formato de escritura se validó para este FOX7, no para todos los XFS de cualquier versión.

Resultado final de [verificacion_xfs.json](verificacion_xfs.json):

- **18.948 entradas** leídas en los dos contenedores con el extractor corregido.
- **18.943 entradas no tocadas idénticas byte a byte**, tanto descomprimidas como en sus bloques almacenados; además, mismos metadatos y offsets de esas entradas.
- **5 reemplazos** leídos y comparados exactamente con `reemplazos\`: `load_back.img`, `logo.img`, `logomode.img`, `serverlist_back.img`, `title.img`.
- Se ejecutó también el código original de `..\comun\sacar_xfs.py`, sin modificarlo, redirigiendo sus rutas y el índice en memoria: **17.803 entradas coinciden** en ambas copias. **1.145 fallan de la misma forma en el original y el nuevo**; no hay fallos exclusivos del nuevo. Son limitaciones del extractor viejo con bloques crudos o coincidencias falsas de cabecera zlib, no pérdida de entradas. El lector corregido comprobó las 18.948. No sería cierto afirmar que el extractor viejo ya podía leerlas todas.
- También pasaron 16 comprobaciones del codec de bloques: datos compresibles y aleatorios de 0, 1, 9, 32.768, 65.535, 65.536, 65.537 y 131.081 bytes.

`graphics_nuevo.xfs`: **665.864.230 bytes**. SHA256:

```text
Original: 6bbc098e47aa485b4192d01fec11ae2e1eca1382597c8c8fc54bd8f164e881d1
Nuevo:    7b5cd17da919623bb2751b941055a4d23c3f483d7cfe2a75d4fa7cfc5f5c73ea
```

El archivo nuevo queda acá como copia de trabajo. No fue instalado ni se aplicó el parche al EXE. La validación demuestra la lectura y la conservación de datos; no sustituye una prueba del motor gráfico o del arranque en ejecución.
