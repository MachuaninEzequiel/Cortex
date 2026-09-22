# cortex/tui/core.py

## Qué tiene adentro

- **Ruta de código:** `cortex/tui/core.py` (326 líneas).
- **Módulo Python:** `cortex.tui.core`.
- **Docstring del módulo:** Núcleo de la TUI Home (Obra 05 Fase D, plan §4.2/§4.3).
- **Clases definidas:**
  - `HomeState`
- **Funciones de módulo:**
  - `_rama_actual(repo_root)`
  - `_sesion_activa_line(ctx)`
  - `snapshot_home(project_root)` — Snapshot barato del estado para el Home (gate <300ms).
  - `render_home(state)`
  - `render_actions_screen(proposals)`
  - `_ejecutar_accion(ctx, proposal)`
  - `_pantalla_acciones(ctx, console)`
  - `_pantalla_busqueda(ctx, console)`
  - `run_home(project_root)` — Loop principal del Home (`cortex` sin argumentos).
- **Constantes / símbolos de módulo:** `MAX_ACCIONES`

## Para qué sirve

Núcleo de la TUI Home (Obra 05 Fase D, plan §4.2/§4.3).

- ``snapshot_home``: snapshot barato <300ms (mtimes + puntero activo +
  conteos; SIN abrir ChromaDB salvo demanda).
- ``render_home`` / ``render_actions_screen``: renderers puros testeables.
- ``run_home``: loop de teclas de una letra (a/s/…/q). La TUI orquesta
  comandos y servicios existentes — nunca duplica lógica.

## Relaciones

### Recibe de

- `cortex.action_engine.context` (ActionContext)
- `cortex.action_engine.i18n` (DEFAULT_LANG, etiquetas, idioma_de)
- `cortex.action_engine.learning` (Learner)
- `cortex.action_engine.models` (ProposedAction)
- `cortex.action_engine.runner` (Runner)
- `cortex.action_engine.scheduler` (Scheduler)
- `cortex.action_engine.store` (PreferencesStore)
- Dependencias externas/stdlib: `subprocess`, `sys`, `time`, `__future__`, `dataclasses`, `pathlib`, `rich.console`, `rich.panel`, `rich.table`

### Envía a

- `cortex.tui`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 326.
Docstrings de símbolos públicos:
- `snapshot_home`: Snapshot barato del estado para el Home (gate <300ms).
- `run_home`: Loop principal del Home (`cortex` sin argumentos).

---
Fuente: código de `cortex/tui/core.py` (AST + grafo de imports internos). No se usó documentación previa.
