# cortex/action_engine/registry.py

## Qué tiene adentro

- **Ruta de código:** `cortex/action_engine/registry.py` (30 líneas).
- **Módulo Python:** `cortex.action_engine.registry`.
- **Docstring del módulo:** Registry del ActionEngine (plan §3.2).
- **Clases definidas:**
  - `Registry`
    - Catálogo de acciones registradas por id (sin duplicados).
    - Métodos públicos/especiales: `__init__`, `register`, `get`, `all`
    - Métodos internos: `__len__`, `__contains__`

## Para qué sirve

Registry del ActionEngine (plan §3.2).

## Relaciones

### Recibe de

- `cortex.action_engine.models` (Action)
- Dependencias externas/stdlib: `__future__`

### Envía a

- `cortex.action_engine`
- `cortex.action_engine.actions`
- `cortex.action_engine.scheduler`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 30.

---
Fuente: código de `cortex/action_engine/registry.py` (AST + grafo de imports internos). No se usó documentación previa.
