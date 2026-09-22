# cortex/context_enricher/budget_resolver.py

## Qué tiene adentro

- **Ruta de código:** `cortex/context_enricher/budget_resolver.py` (58 líneas).
- **Módulo Python:** `cortex.context_enricher.budget_resolver`.
- **Docstring del módulo:** cortex.context_enricher.budget_resolver — Task-aware retrieval budget.
- **Funciones de módulo:**
  - `resolve_budget_profile(task_type, complexity)` — Map a detected ``task_type`` to a budget envelope.
- **Constantes / símbolos de módulo:** `_BUDGET_PROFILES`, `_DEFAULT`, `__all__`

## Para qué sirve

cortex.context_enricher.budget_resolver — Task-aware retrieval budget.

Pure function that maps a detected ``task_type`` (and optional
``complexity``) to a retrieval envelope (``top_k`` and ``max_chars``).
The mapping comes verbatim from the budget profiles that used to live in
the deleted ``cortex/autopilot/context_budget.py`` (see
``docs/pluggable-middle/fases/_internal/autopilot-audit.md`` §11.4) —
Phase 08 / T8.4 reinstates them as data without re-introducing the
original module.

The orchestrator (SDDwork) passes the detected ``task_type`` when it
calls ``cortex_context``; the MCP server uses this resolver to size the
enrichment proportionally. Without it, the enricher always runs at
``fast-code`` defaults — which wastes tokens on docs-only / question
tasks and under-serves deep refactors and security audits.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 58.
Docstrings de símbolos públicos:
- `resolve_budget_profile`: Map a detected ``task_type`` to a budget envelope.

---
Fuente: código de `cortex/context_enricher/budget_resolver.py` (AST + grafo de imports internos). No se usó documentación previa.
