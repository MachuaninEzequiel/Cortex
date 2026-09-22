# cortex/enterprise/promotion_doctype.py

## Qué tiene adentro

- **Ruta de código:** `cortex/enterprise/promotion_doctype.py` (449 líneas).
- **Módulo Python:** `cortex.enterprise.promotion_doctype`.
- **Docstring del módulo:** cortex.enterprise.promotion_doctype - DocType-aware promotion (Fase 10).
- **Clases definidas:**
  - `PromotionResult`
    - Outcome of a DocType-aware promotion call.
  - `PromotionError` (RuntimeError)
    - Raised when a DocType-aware promotion cannot proceed.
- **Funciones de módulo:**
  - `promote_note_doctype_aware(source_path)` — Promote ``source_path`` into ``enterprise_vault_root`` honouring
  - `_read_note(path)`
  - `_resolve_target(route, source_path, fm, enterprise_vault_root, project_id)` — Pick the enterprise destination preserving the doc identity.
  - `_build_enterprise_frontmatter()` — Compose the enterprise frontmatter dict ready for ``yaml_dump_safe``.
  - `_summarize_session(fm, body)` — Generate a compact digest from a SESSION body.
  - `_split_sections(body)` — Split a markdown body into ``{section_title: section_body}`` by H2.
  - `_audit_event(actor, action, reason)`
  - `_write_with_updates(path, fm, body)`
  - `mark_as_accepted(path)` — Promote a draft enterprise note to status=accepted (Item #9 deuda residual).
  - `mark_as_rejected(path)` — Reject a draft enterprise note (Item #9 deuda residual).
  - `list_pending_drafts(vault_root)` — List notes with ``status: draft`` in ``vault_root`` (Item #9).
- **Constantes / símbolos de módulo:** `_SESSION_INTRO`, `_H2_HEADER_RE`, `__all__`

## Para qué sirve

cortex.enterprise.promotion_doctype - DocType-aware promotion (Fase 10).

The legacy ``knowledge_promotion.py`` treats every promotable note the
same: copy + inject frontmatter. The canonical-documentation initiative
introduces three promotion modes (driven by ``RouteSpec.promotion_mode``):

    - ``as-is``           Copy the body unchanged.
    - ``summarize``       Synthesize a compact knowledge digest from the
                          source body (used for SESSION notes).
    - ``review-required`` Copy but set status='draft' so a reviewer must
                          approve before the doc goes ``published``.

This module provides ``promote_note_doctype_aware`` which is the entry
point the new pipeline calls. It does not replace
``KnowledgePromotionService`` — for now both coexist, and the new function
is opt-in.

The function is intentionally side-effect-free at the filesystem level
when ``dry_run=True``, so callers (CLI, tests) can preview the operation.

## Relaciones

### Recibe de

- `cortex.documentation.common` (compute_fingerprint, parse_frontmatter_lenient, split_frontmatter_and_body, yaml_dump_safe)
- `cortex.documentation.doc_type` (DocType)
- `cortex.documentation.errors` (RoutingError)
- `cortex.documentation.routing` (RouteSpec, resolve_route)
- `cortex.enterprise.governance` (ADMIN_TEAM, assert_can_promote)
- `cortex.enterprise.models` (EnterpriseOrgConfig)
- Dependencias externas/stdlib: `logging`, `re`, `yaml`, `__future__`, `dataclasses`, `datetime`, `pathlib`, `typing`

### Envía a

- `cortex.cli.review_knowledge`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 449.
Docstrings de símbolos públicos:
- `promote_note_doctype_aware`: Promote ``source_path`` into ``enterprise_vault_root`` honouring
- `mark_as_accepted`: Promote a draft enterprise note to status=accepted (Item #9 deuda residual).
- `mark_as_rejected`: Reject a draft enterprise note (Item #9 deuda residual).
- `list_pending_drafts`: List notes with ``status: draft`` in ``vault_root`` (Item #9).

---
Fuente: código de `cortex/enterprise/promotion_doctype.py` (AST + grafo de imports internos). No se usó documentación previa.
