# cortex/cli/review_knowledge.py

## Qué tiene adentro

- **Ruta de código:** `cortex/cli/review_knowledge.py` (216 líneas).
- **Módulo Python:** `cortex.cli.review_knowledge`.
- **Docstring del módulo:** cortex.cli.review_knowledge - Manage the promotion review queue.
- **Funciones de módulo:**
  - `_resolve_layout(project_root)`
  - `_enterprise_vault(layout)`
  - `pending_command(doc_type, project_root, json_output)` — List enterprise notes awaiting promotion review (status: draft).
  - `approve_command(path, reviewer, reason, project_root)` — Promote a draft note to status: accepted and append an audit_trail entry.
  - `reject_command(path, reviewer, reason, delete, project_root)` — Reject a draft note. Default: move to rejected/. With --delete: remove.
  - `candidate_command(selector, approve, actor, reason, project_root, json_output)` — Legacy candidate review (KnowledgePromotionService JSONL records).
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.cli.review_knowledge - Manage the promotion review queue.

This module exposes ``cortex review-knowledge`` as a typer subapp with
three subcommands (Item #9 from PLAN-DEUDA-RESIDUAL):

    - ``pending``    List enterprise notes currently in ``status: draft``.
    - ``approve``    Move a draft note to ``status: accepted`` (with audit_trail).
    - ``reject``     Move a draft note into ``rejected/`` (or delete with --delete).

For the legacy promotion candidate workflow (``KnowledgePromotionService``
that records JSONL events under ``.cortex/enterprise/promotion/``), a
fourth subcommand ``candidate`` preserves the original single-command
behavior.

## Relaciones

### Recibe de

- `cortex.enterprise.promotion_doctype` (PromotionError, list_pending_drafts, mark_as_accepted, mark_as_rejected)
- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `getpass`, `json`, `typer`, `__future__`, `pathlib`

### Envía a

- `cortex.cli.main`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 216.
Docstrings de símbolos públicos:
- `pending_command`: List enterprise notes awaiting promotion review (status: draft).
- `approve_command`: Promote a draft note to status: accepted and append an audit_trail entry.
- `reject_command`: Reject a draft note. Default: move to rejected/. With --delete: remove.
- `candidate_command`: Legacy candidate review (KnowledgePromotionService JSONL records).

---
Fuente: código de `cortex/cli/review_knowledge.py` (AST + grafo de imports internos). No se usó documentación previa.
