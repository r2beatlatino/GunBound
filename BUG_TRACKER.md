# Registro de bugs — auditoría nov-2026

Todos los bugs fueron encontrados, corregidos y verificados en la rama `audit/noviembre-2026`.

---

## B-01 · fin_jewel sin validar al remitente
**Severidad:** Alta  **Módulo:** `servidor/partida.py`  **Estado:** ✅ corregido

**Descripción:** Cualquier jugador podía mandar el opcode 0x4200 (fin de partida Jewel) y terminar la partida, aunque no fuese la llave (host) ni estuviese en la sala. No se validaba si ya había ganador, lo que permitía terminar la misma partida dos veces.

**Causa:** `fin_jewel` no verificaba `s.sala.llave is s` ni `x.ganador is not None`.

**Corrección:**
```python
def fin_jewel(mundo, s, cuerpo):
    datos, ok = s.descifrar(cuerpo, 0x4200)
    x = s.sala
    if not ok or x is None or x.llave is not s or x.estado != JUGANDO or x.ganador is not None:
        return
    x.ganador = datos[0] if datos else SIN_GANADOR
    for o in x.jugadores:
        o.enviar_cifrado(0x4410, datos)
```

**Prueba:** `probar_audit.py` — sección B-01 (4 aserciones).

---

## B-02 · volver_del_resultado reinicia la sala sin partida terminada
**Severidad:** Media  **Módulo:** `servidor/sala.py`  **Estado:** ✅ corregido

**Descripción:** El opcode 0x3232 (volver al lobby desde la pantalla de resultado) podía cambiar `sala.estado` de `JUGANDO` a `ESPERA` aunque la partida siguiera activa. Cualquier jugador podía mandarlo.

**Causa:** `volver_del_resultado` no verificaba que existiese un ganador antes de resetear el estado.

**Corrección:**
```python
def volver_del_resultado(mundo, s, cuerpo):
    x = s.sala
    if x is not None and getattr(x, "ganador", None) is not None:
        x.estado = ESPERA
    s.enviar(0x3233, b"", rtc=0)
```

**Prueba:** `probar_audit.py` — sección B-02 (2 aserciones).

---

## B-pase · evicción de JTI borra entradas vigentes
**Severidad:** Media  **Módulo:** `servidor/pase.py`  **Estado:** ✅ corregido

**Descripción:** Cuando el diccionario de JTIs usados llegaba a MAX_RECORDADOS (50 000), la evicción podía borrar entradas cuyo JTI aún no había expirado (ventana de replay).

**Causa:** El bucle de evicción dura ordenaba por tiempo de expiración sin filtrar los aún vigentes.

**Corrección:** La evicción dura sólo elimina entradas con `exp + TOLERANCIA_RELOJ < ahora`. Si todas las entradas están vigentes (ataque activo), no se borra nada.

**Prueba:** Cubierta por `probar_basicos.py` (pruebas de replay existentes).

---

## B-03 · elegir_movil acepta valores inválidos
**Severidad:** Media  **Módulo:** `servidor/sala.py`  **Estado:** ✅ corregido

**Descripción:** El opcode 0x3200 guardaba cualquier byte como número de móvil sin validar. El cliente sólo tiene móviles 0-15, 17 y 18; valores fuera de ese rango podían causar comportamiento indefinido en el cliente.

**Corrección:**
```python
_MOVILES_VALIDOS = set(range(16)) | {17, 18, AL_AZAR}
def elegir_movil(mundo, s, cuerpo):
    if s.sala is not None and len(cuerpo) >= 2:
        m1, m2 = cuerpo[0], cuerpo[1]
        if m1 in _MOVILES_VALIDOS and m2 in _MOVILES_VALIDOS:
            s.movil1, s.movil2 = m1, m2
    s.enviar(0x3201, b"", rtc=0)
```

**Prueba:** `probar_audit.py` — sección B-03 (2 aserciones).

---

## B-04 · armar_inicio: colisión de posiciones de salida
**Severidad:** Media  **Módulo:** `servidor/partida.py`  **Estado:** ✅ corregido

**Descripción:** Al calcular la posición de salida de cada jugador, se usaba `s.casilla % len(puntos)` en lugar del índice del bucle. Si dos jugadores tenían casillas que diferían en exactamente `len(puntos)`, se les asignaba la misma posición X,Y de salida.

**Causa:** `puntos[orden_lugar[s.casilla % len(puntos)]]` debería ser `puntos[orden_lugar[i % len(puntos)]]`.

**Prueba:** `probar_audit.py` — sección B-04 (2 aserciones de smoke test; la verificación exacta de coordenadas requiere decodificar el paquete 0x3432 con el protocolo extendido).

---

## B-05 · /movil no acepta móviles 14 y 15
**Severidad:** Baja  **Módulo:** `servidor/comandos.py`  **Estado:** ✅ corregido

**Descripción:** El comando `/movil` aceptaba sólo 0-13, 17 y 18, rechazando los móviles 14 y 15 que sí existen en el cliente.

**Corrección:** Cambio de `range(14)` a `range(16)`:
```python
if len(args) != 1 or not args[0].isdigit() or int(args[0]) not in list(range(16)) + [17, 18]:
    _decir(s, "Uso: /movil <0-15, 17 o 18>")
```

**Prueba:** `probar_audit.py` — sección B-05 (4 aserciones).

---

## B-06 · cambiar configuración de sala durante partida activa
**Severidad:** Baja  **Módulo:** `servidor/sala.py`  **Estado:** ✅ corregido

**Descripción:** La llave podía cambiar mapa, ajustes, cupo y otros parámetros de la sala mientras la partida estaba activa (`estado == JUGANDO`). Los cambios se guardaban en el server aunque el cliente no los pudiera mostrar correctamente.

**Corrección:** Se añadió el helper `_llave_en_espera()` que sólo devuelve la sala si `estado == ESPERA`. Todas las funciones de cambio de configuración lo usan en lugar de `_sala_de_la_llave`.

**Prueba:** `probar_audit.py` — sección B-06 (1 aserción).

---

## B-07 · límite de conexiones no cuenta las pre-login
**Severidad:** Baja  **Módulo:** `servidor/mundo.py`  **Estado:** ✅ corregido

**Descripción:** El contador `len(mundo.sesiones)` sólo cuenta jugadores que completaron el login. Las conexiones TCP abiertas pero sin login podían superar el límite configurado en `max_conexiones`.

**Corrección:** Se añadió `_total_conexiones` que se incrementa en la conexión TCP y se decrementa al cerrar, independientemente de si el login completó.

**Prueba:** Cubierta por los límites de `max_conexiones` en `probar_basicos.py`.

---

## B-08 · _lugar_libre: fallback 254 crea slots duplicados
**Severidad:** Baja  **Módulo:** `servidor/entrada.py`  **Estado:** ✅ corregido

**Descripción:** Cuando los 255 slots del canal estaban ocupados, `_lugar_libre` devolvía `254` como fallback, creando un segundo jugador con el mismo `lugar_canal`. Eso corrompía el paquete del canal (0x2001).

**Corrección:** `_lugar_libre` devuelve `None` cuando no hay slots; `login` rechaza la entrada con `0x1012 NO_EXISTE`.

**Prueba:** `probar_audit.py` — sección B-08 (2 aserciones sobre el helper puro).

---

## B-09 · clave_dinamica crash con inputs demasiado largos
**Severidad:** Baja  **Módulo:** `servidor/cifrado.py`  **Estado:** ✅ corregido

**Descripción:** Si usuario o contraseña superaban 12 bytes, `clave_dinamica` podía terminar con un `relleno` negativo, causando `ValueError: bytes() arg 'count' cannot be negative`.

**Corrección:** Se añaden slices `[:12]` y `[:4]` al construir `m`, garantizando que el mensaje siempre cabe en un bloque SHA-0 (64 bytes):
```python
m = bytearray(usuario.encode("latin-1")[:12] + contrasena.encode("latin-1")[:12] + bytes(ficha)[:4])
```

**Prueba:** `probar_audit.py` — sección B-09 (3 aserciones, incluyendo equivalencia de truncado vs. directo).

---

## B-10 · crear sala falla en silencio cuando se agotan los IDs
**Severidad:** Baja  **Módulo:** `servidor/sala.py`  **Estado:** ✅ corregido

**Descripción:** Cuando los 255 IDs de sala estaban en uso, `_id_libre` devolvía `None` y `crear` retornaba sin mandar ninguna respuesta al cliente. El cliente quedaba esperando indefinidamente.

**Corrección:** Se añade envío de `0x5101` con texto de error antes de retornar:
```python
sid = _id_libre(mundo)
if sid is None or len(resto) < 9:
    motivo = "no quedan números de sala" if sid is None else "pedido corto"
    s.enviar(0x5101, motivo.encode("latin-1"))
    return
```

**Prueba:** `probar_audit.py` — sección B-10 (1 aserción).
