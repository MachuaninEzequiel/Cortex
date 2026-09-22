# cortex/action_engine/actions/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/action_engine/actions/__init__.py` (52 líneas).
- **Módulo Python:** `cortex.action_engine.actions`.
- **Docstring del módulo:** Catálogo v1 del ActionEngine (plan §3.3).
- **Funciones de módulo:**
  - `build_default_registry(ctx)` — Registra las 10 acciones v1 sobre el contexto dado.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

Catálogo v1 del ActionEngine (plan §3.3).

## Relaciones

### Recibe de

- `cortex.action_engine.actions.catalog` (ide_resync, knowledge_promote, learn_topic, memory_prune, quality_run_gates, session_checkpoint_now, session_close_stale, setup_finish_bootstrap, vault_reindex, vault_validate_docs)
- `cortex.action_engine.context` (ActionContext)
- `cortex.action_engine.registry` (Registry)
- Dependencias externas/stdlib: `__future__`

### Envía a

- `cortex.cli.next`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 52.
Docstrings de símbolos públicos:
- `build_default_registry`: Registra las 10 acciones v1 sobre el contexto dado.
Reexportes observados:
- cortex.action_engine.actions.catalog: ide_resync, knowledge_promote, learn_topic, memory_prune, quality_run_gates, session_checkpoint_now, session_close_stale, setup_finish_bootstrap, vault_reindex, vault_validate_docs
- cortex.action_engine.context: ActionContext
- cortex.action_engine.registry: Registry

---
Fuente: código de `cortex/action_engine/actions/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
