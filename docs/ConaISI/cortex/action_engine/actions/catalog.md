# cortex/action_engine/actions/catalog.py

## Qué tiene adentro

- **Ruta de código:** `cortex/action_engine/actions/catalog.py` (396 líneas).
- **Módulo Python:** `cortex.action_engine.actions.catalog`.
- **Docstring del módulo:** Catálogo v1 del ActionEngine (plan §3.3) — 10 acciones sobre servicios existentes.
- **Funciones de módulo:**
  - `_no_op_undo()`
  - `_report_action(id_, title, category, effect, checks, runner)` — Acción de sólo-lectura: reversible formal, auto-ok, instant.
  - `_sesiones_abiertas(ctx)`
  - `_feedback_eventos(ctx)`
  - `setup_finish_bootstrap(ctx)`
  - `session_close_stale(ctx)`
  - `session_checkpoint_now(ctx)`
  - `vault_reindex(ctx)`
  - `vault_validate_docs(ctx)`
  - `quality_run_gates(ctx)`
  - `learn_topic(ctx)`
  - `_ahora_dia()`
  - `knowledge_promote(ctx)`
  - `memory_prune(ctx)`
  - `ide_resync(ctx)`

## Para qué sirve

Catálogo v1 del ActionEngine (plan §3.3) — 10 acciones sobre servicios existentes.

Cada fábrica recibe el :class:`ActionContext` y devuelve la :class:`Action`
con precondiciones baratas (on-open), dry-run nativo y delegación total en
los servicios de Cortex. Report-only ⇒ reversible con undo no-op para
satisfacer el contrato sin fingir cambios que no hay.

## Relaciones

### Recibe de

- `cortex.action_engine.context` (ActionContext)
- `cortex.action_engine.models` (Action, ActionResult, Check)
- Dependencias externas/stdlib: `json`, `__future__`, `collections.abc`, `pathlib`

### Envía a

- `cortex.action_engine.actions`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 396.

---
Fuente: código de `cortex/action_engine/actions/catalog.py` (AST + grafo de imports internos). No se usó documentación previa.
