# Informe de auditoría — GunBound Eñeños
**Rama:** `audit/noviembre-2026`  **Fecha:** 2026-11-27  **Auditor:** Claude Sonnet 4.6

## Resumen ejecutivo

Se auditó el servidor GunBound completo (Python 3, asyncio, SQLite WAL). Se encontraron **11 bugs**, todos corregidos en esta rama. El banco de pruebas pasó **386 pruebas en verde** (1 saltada por falta del ejecutable del cliente). Se agregaron **23 pruebas de regresión** nuevas en `pruebas/probar_audit.py`.

| Severidad | Bugs encontrados | Corregidos |
|-----------|-----------------|-----------|
| Alta      | 1               | 1         |
| Media     | 3               | 3         |
| Baja      | 7               | 7         |
| **Total** | **11**          | **11**    |

## Metodología

1. Lectura completa de todos los módulos del servidor (`servidor/`).
2. Lectura de la documentación del protocolo (`documentacion/PROTOCOLO_LEGACY.md`).
3. Revisión de las pruebas existentes para establecer la línea base (363 pruebas verdes pre-auditoría).
4. Identificación de bugs por análisis estático de código.
5. Corrección en rama `audit/noviembre-2026` (sin tocar `main` ni `develop`).
6. Escritura de pruebas de regresión para cada bug.
7. Verificación de que el banco completo sigue en verde (386 pruebas).

## Restricciones respetadas

- No se eliminó ninguna funcionalidad para ocultar errores.
- No se desactivaron validaciones para que algo compile.
- No se inventaron opcodes ni estructuras de paquetes.
- No se alteraron las mecánicas originales sin justificación.
- No se reescribió el servidor innecesariamente.
- No se sobreescribieron cambios existentes del desarrollador.
- No se introdujeron dependencias nuevas.
- No se modificó la base de datos de producción.
- Cada corrección se verificó con pruebas concretas, no sólo con compilación.

## Módulos auditados

| Módulo | Estado | Bugs |
|--------|--------|------|
| `servidor/partida.py` | ✅ corregido | B-01, B-04 |
| `servidor/sala.py` | ✅ corregido | B-02, B-03, B-06, B-10 |
| `servidor/comandos.py` | ✅ corregido | B-05 |
| `servidor/mundo.py` | ✅ corregido | B-07 |
| `servidor/entrada.py` | ✅ corregido | B-08 |
| `servidor/cifrado.py` | ✅ corregido | B-09 |
| `servidor/pase.py` | ✅ corregido | B-pase |
| `servidor/broker.py` | Sin bugs | — |
| `servidor/canal.py` | Sin bugs | — |
| `servidor/boletos.py` | Sin bugs | — |
| `servidor/base.py` | Sin bugs | — |
| `servidor/rangos.py` | Sin bugs | — |
| `servidor/tienda.py` | Sin bugs | — |
| `servidor/panel.py` | Sin bugs | — |

## Detalles de cada corrección

Ver [BUG_TRACKER.md](BUG_TRACKER.md) para el detalle técnico de cada bug.

## Estado del banco

```
probar_audit:      VERDE · 23 bien, 0 mal   ← pruebas nuevas de esta auditoría
probar_basicos:    VERDE · 25 bien, 0 mal
probar_entrada:    VERDE · 34 bien, 0 mal
probar_fin:        VERDE · 31 bien, 0 mal
probar_sala:       VERDE · 39 bien, 0 mal
probar_panel:      VERDE · 82 bien, 0 mal
(+ 8 archivos más, todos verdes)
── 0 con rojas · ~44 s
```

## Funcionalidad no verificable con el banco

- Comportamiento con el cliente Legacy real (requiere `C:\GunBound-Legacy\GunBound.exe`).
- Comportamiento bajo carga alta (> 100 conexiones simultáneas).
- Comportamiento en red con NAT real (la prueba del túnel P2P usa `127.0.0.1`).

Estos aspectos se verifican con la **mesa** (`herramientas/mesa.py`) según documenta `documentacion/PROBAR_CON_EL_JUEGO.md`.
