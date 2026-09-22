# cortex/action_engine/scheduler.py

## Qué tiene adentro

- **Ruta de código:** `cortex/action_engine/scheduler.py` (100 líneas).
- **Módulo Python:** `cortex.action_engine.scheduler`.
- **Docstring del módulo:** Registry y scheduler del ActionEngine (Obra 05 Fase B, plan §3.4).
- **Clases definidas:**
  - `Scheduler`
    - Evalúa el registry y propone acciones priorizadas.
    - Métodos públicos/especiales: `propose`, `explain_why_not`
    - Métodos internos: `_score`
- **Constantes / símbolos de módulo:** `MAX_VISIBLE_DEFAULT`

## Para qué sirve

Registry y scheduler del ActionEngine (Obra 05 Fase B, plan §3.4).

- ``Registry``: catálogo de acciones registradas por id.
- ``Scheduler``: evalúa precondiciones + preferencias, calcula score
  (impacto × frescura − costo) y devuelve máximo ``max_visible`` propuestas.

## Relaciones

### Recibe de

- `cortex.action_engine.models` (IMPACTO_BASE, COSTO_PENALIZACION, Action, ProposedAction)
- `cortex.action_engine.registry` (Registry)
- `cortex.action_engine.signals` (MemorySignals, multiplicador_categoria)
- `cortex.action_engine.store` (PreferencesStore)
- Dependencias externas/stdlib: `__future__`, `dataclasses`

### Envía a

- `cortex.action_engine`
- `cortex.cli.next`
- `cortex.tui.core`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 100.
Docstrings de símbolos públicos:
- `Scheduler.propose`: Acciones ofrecibles ahora mismo.
- `Scheduler.explain_why_not`: Para cada acción NO propuesta: qué precondiciones fallaron.

---
Fuente: código de `cortex/action_engine/scheduler.py` (AST + grafo de imports internos). No se usó documentación previa.
