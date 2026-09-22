# cortex/action_engine/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/action_engine/__init__.py` (31 líneas).
- **Módulo Python:** `cortex.action_engine`.
- **Docstring del módulo:** cortex.action_engine — motor de acciones con aprendizaje (Obra 05).
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.action_engine — motor de acciones con aprendizaje (Obra 05).

Ciclo: OBSERVAR → PROPONER → APROBAR → EJECUTAR → APRENDER.
Ver docs/transformacion/05-UX-TUI-ACTIONENGINE.md §3.

## Relaciones

### Recibe de

- `cortex.action_engine.models` (Action, ActionResult, Check, Decision, ProposedAction)
- `cortex.action_engine.registry` (Registry)
- `cortex.action_engine.runner` (Runner)
- `cortex.action_engine.scheduler` (Scheduler)
- `cortex.action_engine.store` (ActionLog, PreferencesStore)

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 31.
Reexportes observados:
- cortex.action_engine.models: Action, ActionResult, Check, Decision, ProposedAction
- cortex.action_engine.registry: Registry
- cortex.action_engine.runner: Runner
- cortex.action_engine.scheduler: Scheduler
- cortex.action_engine.store: ActionLog, PreferencesStore

---
Fuente: código de `cortex/action_engine/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
