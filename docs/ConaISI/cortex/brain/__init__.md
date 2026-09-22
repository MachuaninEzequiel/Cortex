# cortex/brain/__init__.py

## Qué tiene adentro

Docstring: paquete **DEPRECATED** (2026-08-25). Duplicado legacy del brain oficial `cortex-brain` (Rust + llama.cpp). Se mantiene como oráculo hasta bajar Python; el subcomando nativo ya no pasa por aquí.

Permisos históricos citados en el código: READ (search/doctor/stats/sesión), SAFE_ACTION (webgraph serve), mutaciones NUNCA (propone comando CLI, no ejecuta).

Reexporta `Tier`, `ToolSpec`, `build_tools` desde `cortex.brain.tools`.

## Para qué sirve

Compatibilidad / inventario de tools del brain Python. No es la implementación actual del asistente.

## Relaciones

### Recibe de

- `cortex.brain.tools`.

### Envía a

- `cortex.brain.cli` (aún registrado desde `cli.main`).

---
Fuente: lectura completa de `cortex/brain/__init__.py`. No se usó documentación previa.
