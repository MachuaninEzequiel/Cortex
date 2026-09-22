# rust/crates/cortex-setup/src/lib.rs

## Qué tiene adentro

Módulos públicos listados en 00-estructura. Constante `PY_TEMPLATES_DIR` hacia `cortex/documentation/templates`.

## Para qué sirve

Fachada P8.

## Relaciones

### Recibe de

- Módulos internos + plantillas Python (solo lectura).

### Envía a

- Consumidores CLI/services/MCP.

### Notas de implementación observadas en el código

Los módulos se agregaron por commits atómicos dentro de P8.
