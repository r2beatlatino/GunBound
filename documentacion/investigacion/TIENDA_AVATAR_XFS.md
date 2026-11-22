# Tienda de avatares en oro — GunBound Legacy v179

**Actualización:** la salida vigente incluye precios y permisos **oro=1/cash=0 en
las 861 piezas**. Los resultados y hashes vigentes están en
[Segunda pasada: permisos](#segunda-pasada-permisos), al final. Las secciones
anteriores a esa actualización conservan el registro de la primera pasada,
incluidos sus tamaños, hashes y la limitación de permisos que ahora se corrigió.

Quedaron generados `avatar_oro.xfs`, `precios_avatar_oro.json` y el conversor
`oro_solo.py`. Los **861 precios permanentes** coinciden con lo pedido:
858 conservan su oro, las otras tres pasan a 180.000 de oro y las 861 tienen cash 0.
La copia `avatar_original.xfs` y `precios_avatar.json` quedaron intactos.
No ejecuté el juego ni modifiqué archivos fuera de esta carpeta.

**Ojo con el resultado funcional:** el cliente también usa permisos separados para
las monedas. Cambiar sólo precios **no alcanza para que toda la tienda funcione
exclusivamente con oro**. Esos permisos se conservaron para cumplir la condición
de que todo campo ajeno a precios quede idéntico. Más abajo está la cadena de
lecturas del ensamblado y el efecto concreto.

## MEDIDO

### Entregables y ejecución

- `oro_solo.py`: lector XFS, conversor y verificación antes y después de escribir.
  Usa solamente la biblioteca estándar de Python 3.10 o posterior.
- `avatar_oro.xfs`: archivo convertido, 232.704 bytes.
- `precios_avatar_oro.json`: mismo contenedor JSON (`source` y `prices`), mismos
  861 IDs, valores `[oro, 0]`. El texto de `source` identifica la salida nueva.
- `verificacion.json`: resultados y SHA-256 generados por el conversor.
- `verificacion_independiente.json`: control adicional con JavaScript y `node:zlib`,
  sin importar ni ejecutar el lector Python.
- `test_oro_solo.py`: nueve controles automatizados.
- `evidencia_asm.txt`: extractos del ASM solicitado, con números de línea originales.

Desde esta carpeta:

```powershell
python oro_solo.py
python oro_solo.py --verificar
python -B -m unittest -v test_oro_solo
```

El primer comando genera y vuelve a leer los archivos. El segundo sólo verifica,
sin escribir. Las rutas se resuelven respecto del script, aunque lo ejecutes desde
otra carpeta. En esta máquina usé el Python 3.12.14 disponible en
`%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.

### Contenedor XFS

Es **Xenesis2, versión textual 2.0.0**, con firma interna `FOX7`. No se interpretó
como el otro formato de `graphics.xfs`. Los enteros de varios bytes son little-endian.

El archivo empieza con un `uint32` que apunta al **índice activo**, no con el tamaño
del archivo: `0x0003974C` = 235.340 en el original. La longitud original es 235.602.
Después vienen los archivos internos en bloques. Al final hay dos copias de índice;
el puntero inicial elige la última.

Cada copia de índice contiene:

| Campo almacenado | Interpretación comprobada |
| --- | --- |
| 1 byte | Longitud comprimida de la cabecera |
| Esa cantidad de bytes | Stream zlib que produce una cabecera de 64 bytes |
| 3 bytes | Longitud comprimida del directorio |
| Esa cantidad de bytes | Stream zlib del directorio: 11 × 128 = 1.408 bytes |

Dentro de la cabecera descomprimida:

| Offset | Campo |
| --- | --- |
| `+0x00` | Firma `FOX7` |
| `+0x04` | Valor 142 en la primera copia y 179 en la activa; significado no determinado, conservado |
| `+0x08` | Cantidad de entradas: 11 |
| `+0x0C` | Valor 0, conservado |
| `+0x10` | Offset de la propia copia de índice |
| `+0x14` | Tamaño de bloque: 65.536 |
| `+0x18` | Texto `The Xenesis2 file system version 2.0.0`, con terminación/relleno NUL |

El lector del cliente sigue esta estructura en `00408816–00408994`: lee el puntero,
la longitud de un byte, descomprime 64 bytes, comprueba firma y bloque de `0x10000`,
y luego lee la longitud de tres bytes y descomprime las entradas de 128 bytes.

Cada entrada del directorio tiene:

| Offset relativo | Campo |
| --- | --- |
| `+0x00..+0x6F` | Nombre del archivo, área de 112 bytes con NUL/relleno |
| `+0x70` | `uint32`: offset físico de sus bloques |
| `+0x74` | `uint32`: modo; vale 1 en las once entradas de esta copia |
| `+0x78` | `uint32`: tamaño descomprimido |
| `+0x7C` | `uint32`: tamaño almacenado, incluidas las cabeceras de bloques |

Archivos originales, en el orden del directorio:

| Archivo | Offset físico | Descomprimido | Almacenado | Registros | Piezas convertidas |
| --- | ---: | ---: | ---: | ---: | ---: |
| `ex1.dat` | 60 | 7.528 | 644 | 11 × 684 bytes | 0 |
| `ex2.dat` | 196.202 | 1.491.124 | 38.876 | 2.180 × 684 bytes | 0 |
| `ex3.dat` | 4 | 25 | 30 | No es tabla de piezas | 0 |
| `ex4.dat` | 34 | 21 | 26 | No es tabla de piezas | 0 |
| `fb.dat` | 65.834 | 964.072 | 30.115 | 1.497 × 644 bytes | 143 |
| `fg.dat` | 704 | 422.468 | 13.009 | 656 × 644 bytes | 53 |
| `fh.dat` | 95.949 | 976.952 | 32.827 | 1.517 × 644 bytes | 145 |
| `mb.dat` | 128.776 | 1.012.372 | 33.375 | 1.572 × 644 bytes | 143 |
| `mf.dat` | 28.869 | 1.172.728 | 36.965 | 1.821 × 644 bytes | 180 |
| `mg.dat` | 13.713 | 488.156 | 15.156 | 758 × 644 bytes | 53 |
| `mh.dat` | 162.151 | 1.024.608 | 34.051 | 1.591 × 644 bytes | 144 |

Las tablas de registros empiezan con `uint32 cantidad`; después están los registros
sin separadores. `ex3.dat` y `ex4.dat` son respectivamente 25 y 21 caracteres ASCII
`1`. Las tablas `ex1/ex2` tienen otra estructura de registro y se preservaron completas;
no se les aplicaron los offsets de las piezas individuales.

### Bloques y compresión

Cada archivo con modo 1 se divide en bloques de hasta 65.536 bytes descomprimidos.
Se lee primero un token de tres bytes:

- Bit `0x800000`: el bloque es corto; su tamaño lógico está en `token & 0xFFFFF`.
  Sin ese bit, su tamaño lógico es 65.536.
- Bit `0x400000`: contenido sin comprimir.
- Si es corto y comprimido, siguen otros tres bytes con el tamaño comprimido.
  Si es completo y comprimido, ese tamaño viene en `token & 0xFFFFF`.
- Siguen dos bytes de checksum opcional: **cero en todos los bloques de esta copia**.
- Sigue el contenido crudo o un stream **zlib con envoltura y Adler-32**.

Esto explica los primeros bytes:

```text
0x000004: 19 00 C0 00 00 [25 veces 31]   ex3.dat crudo
0x000022: 15 00 C0 00 00 [21 veces 31]   ex4.dat crudo
0x00003C: 68 1D 80 7C 02 00 00 00 78 9C ...
           7.528       636       0       zlib de ex1.dat
```

Las ramas del lector en `004015C8–004016FC` comprueban esos bits, usan el tamaño
`0x10000` por defecto y llaman al descompresor `004C6270`. No se adivinaron límites
buscando `78 9C`: el lector entregado usa las longitudes del contenedor y exige
consumir cada stream por completo.

### Registro individual y ubicación de precios

Las siete tablas `fb/fg/fh/mb/mf/mg/mh` suman **9.412 registros de 644 bytes**,
todos con ID distinto. Los offsets siguientes son relativos al comienzo de un
registro; para el registro `i`, el offset lógico dentro del `.dat` es
`4 + i × 644 + offset_campo`.

| Offset | Campo observado |
| --- | --- |
| `+0x00` | ID de pieza, `uint32`; la clave JSON es la representación hexadecimal de sus cuatro bytes en disco |
| `+0x04` | Otro identificador, `uint32`; se usa en la búsqueda del registro en `00427504` |
| `+0x08` | Otro `uint32`, conservado; semántica no determinada |
| `+0x0C` | Nombre: cadena de bytes terminada en NUL, antes de `+0x23`; no se recodifica |
| `+0x23`, `+0x24` | Estados separados, copiados a `+0x3E/+0x3F` del objeto del cliente; no se reinterpretaron |
| `+0x25` | Estado de la primera opción de plazo |
| `+0x54` | Estado de la opción permanente, un byte |
| **`+0x58`** | **Precio permanente en oro, `uint32`** |
| **`+0x5C`** | **Precio permanente en cash, `uint32`** |
| **`+0x60`** | **Permiso de moneda oro, un byte** |
| **`+0x61`** | **Permiso de moneda cash, un byte** |
| `+0x64..+0x83` | Ocho campos de cuatro bytes; el cliente los carga por separado; significado individual no confirmado |
| `+0x84..+0x283` | Área de descripción/texto de 512 bytes, conservada literalmente |

Opciones de precio dentro del registro:

| Opción almacenada | Byte de estado | Oro `uint32` | Cash `uint32` |
| --- | --- | --- | --- |
| Plazo, opción 0 | `+0x25` | `+0x28` | `+0x2C` |
| Plazo, opción 1 | `+0x30` | `+0x34` | `+0x38` |
| Plazo, opción 2 | `+0x3C` | `+0x40` | `+0x44` |
| Plazo, opción 3 | `+0x48` | `+0x4C` | `+0x50` |
| Permanente, opción 4 | `+0x54` | `+0x58` | `+0x5C` |

Las opciones 1 y 3 están enteramente en cero en esta copia. La relación de la última
opción con los precios permanentes está comprobada contra las 861 claves del JSON.
No confirmé la cantidad exacta de días de las otras opciones: no la inventé.

El ID codifica datos adicionales. El cliente en `0051847C–005184BF` separa el bit
`0x8000` para elegir género, los bits 16–19 para la casilla, y `ID & 0x7FFF` para el
número de pieza. Su selector arma el prefijo `f` o `m` en `004273D1–004273DE`.
La relación con los archivos de esta copia es:

| Dato | Valores |
| --- | --- |
| Género | Bit 15 en 0: tablas `f`; en 1: tablas `m` |
| Casilla 0 | `b`: cuerpo/ropa |
| Casilla 1 | `h`: cabeza |
| Casilla 2 | `g`: cara/lentes |
| Casilla 3 | `f`: bandera; en esta copia sólo está `mf.dat` |

Por ejemplo `01000000` es el entero `0x00000001` y `01800000` es
`0x00008001`: ambas piezas se llaman `Space Marine`, de `fb.dat` y `mb.dat`.
Sus precios originales permanentes son `[20000, 2000]`.

### Contraste de precios y alcance exacto

El lector selecciona las piezas con estado permanente `+0x54 != 0` y al menos un
precio permanente distinto de cero. Esa regla, **sin usar el JSON para elegir IDs**,
produce exactamente los mismos **861 IDs y 861 pares** de `precios_avatar.json`:
sin faltantes, extras ni diferencias de importe.

La conversión afecta únicamente los ocho bytes `+0x58..+0x5F` de esos 861 registros.
Los otros 8.551 registros individuales, las opciones por plazo de las 861 piezas,
las tablas adicionales y los permisos de moneda se conservan. Hay importes de cash
en esas otras opciones/tablas: el JSON entregado es de piezas permanentes y no es
un inventario de todos los campos de precio del XFS.

| ID tal como figura en JSON | Nombre | Antes | Después |
| --- | --- | --- | --- |
| `7e800100` | Super Fly | `[0, 18000]` | `[180000, 0]` |
| `7f800100` | Bikini | `[0, 18000]` | `[180000, 0]` |
| `80800100` | Skeleton Halloween | `[0, 18000]` | `[180000, 0]` |

Para las otras 858 se conserva el oro exacto, incluso cuando no era diez veces el
cash. Por ejemplo, `01000100` conserva 10.000 de oro aunque antes tuviera 1.200 cash.

### Verificación de preservación

Se volvió a leer `avatar_oro.xfs` desde disco. Resultado:

- Control inverso del original: **861/861 pares coinciden con el JSON viejo**.
- Salida: **861/861 pares cumplen la conversión**, y coinciden con el JSON nuevo.
- Comparación de los **7.560.054 bytes descomprimidos** de los once archivos:
  exactamente **1.729 bytes distintos**, todos dentro de los campos de precios
  permanentes permitidos. Para cada archivo se construye la copia esperada del
  original aplicando esos pares y se exige igualdad completa con la salida.
- Nombres, IDs, géneros, casillas, estados, permisos de moneda, descripciones,
  campos auxiliares y precios de las demás opciones: **idénticos**.
- De los **121 bloques**, **105 se conservan literalmente**, incluso comprimidos;
  sólo se recomprimen los 16 que contienen cambios.
- Los dos índices se vuelven a leer y sus directorios coinciden. Se ajustan los
  offsets físicos, tamaños almacenados y autopunteros que cambian al recomprimir.
  Los demás bytes de las cabeceras/directorios descomprimidos se comparan y conservan.
- Índices originales: `[235078,235340)` y `[235340,235602)`.
  Índices nuevos: `[232182,232443)` y `[232443,232704)`.
  El puntero inicial nuevo es 232.443 = `0x00038BFB`.

La identidad pedida es del **contenido lógico no modificado**. El archivo comprimido
completo no puede conservar su hash cuando cambian sus precios: los streams zlib,
sus Adler-32 y la información física correspondiente cambian.

Los **nueve controles pasaron**: original contra referencia sin selección por JSON;
conversión y preservación; archivos escritos y regeneración determinista; rechazo de
referencia incorrecta; rechazo de nombre alterado; rechazo de permiso de moneda
alterado; rechazo de precio incorrecto; rechazo de truncamiento; rechazo de puntero
activo fuera del archivo. El segundo lector independiente confirmó los 861 precios
y la comparación completa de los once contenidos lógicos.

| Archivo | SHA-256 |
| --- | --- |
| `avatar_original.xfs` | `97b9b6b997437b72af52b3eb256b3bbe7e1054c7e10571e9305a238baf44ee91` |
| `avatar_oro.xfs` | `a95e45336fee8cf69dd008a88022dad0f18f8d90d513775f152143221451973b` |

### Quién lee los precios y decide los botones

Se buscó por patrones y rangos de direcciones en
`D:\Gunbound\Legacy-Analisis\GunBound.exe.asm.txt`. No se volcó el ASM completo.
`evidencia_asm.txt` conserva los extractos con las líneas originales.

1. **Carga de la pieza: `004273B0`**, llamada por el diálogo de tienda en
   **`004FE2A1`**. Lee registros de **`0x284` = 644 bytes** en `004274F0`; también
   hay una ruta de acceso por índice en `004279A5–004279C2`.
2. **Carga del oro y cash permanentes: `00427697–004276D9`**. El registro temporal
   empieza en `[esp+0x98]`: `[esp+0xF0]` es `registro+0x58` (oro) y
   `[esp+0xF4]` es `registro+0x5C` (cash). Se guardan en los campos protegidos del
   objeto de pieza: oro en `objeto+0x74` y cash en `objeto+0x7C`.
   La ruta equivalente está en `00427AE0–00427B28`.
3. **Carga de permisos: `00427806–00427821`**. Los bytes del registro `+0x60/+0x61`
   se copian a `objeto+0x84/+0x85`. También aparece en `00427C55–00427C7A`.
4. El diálogo coloca el objeto en `diálogo+0x94`. En
   **`004FE316–004FE348`** lee `diálogo+0x119` (permiso cash) y `+0x118` (permiso oro),
   y los transforma en los estados `diálogo+0xA10/+0xA11`.
5. **`004FE409–004FE4FA`** consulta esos estados para elegir entre las funciones
   **`004C7870`** y **`004C7880`**. Esas funciones ponen el estado del control
   `+0x50` en 1/0 y llaman a su método virtual con argumento 1/0. Esta rama depende
   de los permisos, **no de comparar el precio con cero**.
6. **Lectura para mostrar el importe permanente: `004FF3B0–004FF3CC`**.
   Lee cash desde `diálogo+0x110` y oro desde `diálogo+0x108`, con el getter
   `0042BFD0`, y los guarda en `+0xA08/+0xA0C`. En
   `004FF49D` y `004FF573` también consulta los permisos al preparar el texto.

Distribución de permisos **antes y después**, para las 861 piezas:

| Permiso oro | Permiso cash | Piezas |
| ---: | ---: | ---: |
| 1 | 1 | 539 |
| 1 | 0 | 167 |
| 0 | 1 | 155 |

Por lo tanto hay **155 piezas con oro deshabilitado**, aunque ahora su importe de
oro sea positivo, y **694 con cash habilitado**, aunque su importe sea cero.
Las tres convertidas desde sólo cash pertenecen al grupo `[permiso oro=0, cash=1]`.
No es una particularidad exclusiva de esas tres.

## INFERIDO Y LÍMITES

- Por la cadena de carga y control, para que la interfaz ofrezca exclusivamente oro
  haría falta además habilitar el byte `+0x60` y deshabilitar `+0x61` en las piezas
  correspondientes. **No se hizo en esta salida**, porque esos bytes no son precios
  y el encargo exige que permanezcan idénticos. El comportamiento visual y la compra
  efectiva no se probaron: no se ejecutó el juego.
- El significado de esos estados como permisos de oro/cash queda respaldado por la
  correspondencia de importes y las ramas del diálogo; la apariencia exacta de cada
  control y cualquier validación posterior del servidor requerirían comprobación
  adicional. El cambio local de precios no demuestra por sí solo cómo cobra el servidor.
- Para extender «todo en oro» a alquileres o paquetes habría que acordar su conversión
  además de los 861 pares permanentes definidos en el encargo. Esta salida conserva
  sus bytes completos y no da por cambiados esos otros productos.
- `f/m` se interpretan como femenino/masculino y `b/h/g/f` como cuerpo, cabeza,
  lentes y bandera por los selectores del cliente y los nombres de las piezas.
  No se asignaron cantidades de días a opciones de plazo sin evidencia suficiente.
- El lector es estricto para **esta variante y esta copia**: entradas modo 1,
  checksums opcionales cero e índices duplicados con directorios iguales. No se
  presenta como un lector universal de cualquier XFS, ni como una prueba de que un
  cliente o servidor ya aceptó el archivo generado.

## Segunda pasada: permisos

**MEDIDO.** Por decisión del dueño, `oro_solo.py` ahora modifica también los bytes
`+0x60 = 1` y `+0x61 = 0` de **esas mismas 861 piezas permanentes**, siempre partiendo
de `avatar_original.xfs` y comprobando sus precios contra `precios_avatar.json`.
Los archivos `avatar_oro.xfs` y `precios_avatar_oro.json` se regeneraron. El XFS vigente
mide **232.321 bytes** y reemplaza la salida de la primera pasada.

Distribución de permisos de las 861 piezas, leída desde la salida regenerada:

| Permiso oro (`+0x60`) | Permiso cash (`+0x61`) | Piezas |
| ---: | ---: | ---: |
| 1 | 0 | **861** |
| 1 | 1 | 0 |
| 0 | 1 | 0 |
| 0 | 0 | 0 |

Los precios siguen cumpliendo exactamente la conversión original: **858 precios de
oro conservados**, las tres piezas que eran sólo cash a **180.000 de oro**, y **861
precios cash en cero**. El JSON sólo contiene precios; por eso, aunque se regeneró,
sus bytes y su hash coinciden con la primera pasada.

Se compararon otra vez los **7.560.054 bytes lógicos** de los once archivos internos
con una copia esperada del original que permite únicamente los nuevos precios y
esos dos permisos en los 861 IDs. Contra el original hay:

- **1.729 bytes distintos de precios** y **849 bytes distintos de permisos**:
  155 permisos de oro pasan de 0 a 1 y 694 permisos de cash pasan de 1 a 0.
- **2.578 bytes lógicos distintos en total**, todos dentro de los diez bytes
  autorizados `+0x58..+0x61` de esas piezas.
- **8.551 registros individuales ajenos al JSON idénticos completos**, incluidos
  sus permisos originales.
- Plazos, nombres, IDs, descripciones y demás campos de las 861 piezas idénticos;
  `ex1.dat`, `ex2.dat`, `ex3.dat` y `ex4.dat` idénticos completos.
- **105 de 121 bloques almacenados idénticos**. Se recomprimen los otros 16 y se
  ajustan únicamente los datos físicos correspondientes del contenedor.
- Ambos índices verificados: `[231799,232060)` y `[232060,232321)`; el puntero
  activo inicial ahora vale **232.060**.

`verificacion.json` y `verificacion_independiente.json` se actualizaron y coinciden
en la distribución de permisos, hashes y contenido autorizado. El segundo control
se puede repetir con el lector separado **`verificar_independiente.cjs`**, que usa
`node:zlib` y no importa el código Python:

```powershell
python -B oro_solo.py --verificar
python -B -m unittest -v test_oro_solo
node verificar_independiente.cjs
```

**Pasaron las 11 pruebas**, además de la relectura con `--verificar` y el lector
independiente. El control de permisos ahora exige los nuevos valores en las 861
piezas y los anteriores en el resto. Incluye rechazar por separado oro=0 o cash=1
en una pieza seleccionada, rechazar cualquier permiso alterado fuera de ellas y
recorrer los 9.412 registros para comprobar los campos preservados. Siguen pasando
los controles de precios, regeneración determinista y rechazo de corrupciones.

SHA-256 de los archivos vigentes, comprobados por ambos lectores:

| Archivo | SHA-256 |
| --- | --- |
| `avatar_oro.xfs` | `9d9f32995a94ce8c5dcf46036cb939b46c862145dc6bb5c0c8b528fbdcd3236c` |
| `precios_avatar_oro.json` | `10791d15ae3450e752481864db11e32ca445b0b6d8ae69f6edc878f0d032b620` |
| `avatar_original.xfs` (intacto) | `97b9b6b997437b72af52b3eb256b3bbe7e1054c7e10571e9305a238baf44ee91` |
| `precios_avatar.json` (intacto) | `cab5c86a81f8b7afc87bccde51ea1bd4ef4c3a9d5fd178cab56ab38de896f6d6` |

**INFERIDO / límite de la comprobación.** Según la cadena de lecturas del ensamblado
documentada en la primera pasada, estos permisos hacen que la interfaz ofrezca
únicamente oro para esas piezas. Se corrigió la causa identificada de los botones
de cash y de oro deshabilitado. No se ejecutó el juego ni se probó una compra contra
el servidor. No se modificó ningún archivo fuera de esta carpeta.
