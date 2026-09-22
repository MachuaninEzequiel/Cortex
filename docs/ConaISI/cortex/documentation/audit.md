# cortex/documentation/audit.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/audit.py` (45 líneas).
- **Módulo Python:** `cortex.documentation.audit`.
- **Docstring del módulo:** cortex.documentation.audit - Helpers for enterprise audit_trail.
- **Funciones de módulo:**
  - `append_audit_event(frontmatter, actor, action, reason)` — Return a NEW ``EnterpriseFrontmatter`` with one extra audit event.

## Para qué sirve

cortex.documentation.audit - Helpers for enterprise audit_trail.

The ``audit_trail`` field on ``EnterpriseFrontmatter`` is append-only. This
module provides the canonical way to add entries.

## Relaciones

### Recibe de

- `cortex.documentation.schemas` (AuditEvent, EnterpriseFrontmatter)
- Dependencias externas/stdlib: `__future__`, `datetime`

### Envía a

- `cortex.documentation.writers`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 45.
Docstrings de símbolos públicos:
- `append_audit_event`: Return a NEW ``EnterpriseFrontmatter`` with one extra audit event.

---
Fuente: código de `cortex/documentation/audit.py` (AST + grafo de imports internos). No se usó documentación previa.
