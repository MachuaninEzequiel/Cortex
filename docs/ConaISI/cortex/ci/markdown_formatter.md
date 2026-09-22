# cortex/ci/markdown_formatter.py

## Qué tiene adentro

- **Ruta de código:** `cortex/ci/markdown_formatter.py` (121 líneas).
- **Módulo Python:** `cortex.ci.markdown_formatter`.
- **Docstring del módulo:** cortex.ci.markdown_formatter — Render a ``ValidationResult`` as Markdown for the Level 2 PR comment workflow.
- **Funciones de módulo:**
  - `render_pr_comment(result)` — Format a Markdown block ready to post as a PR comment.
  - `_title(result)`
  - `_render_files_section(result)`
  - `_render_hooks_section(result)`
  - `_render_scope_drift_section(drift)`
- **Constantes / símbolos de módulo:** `DEFAULT_MARKER`, `__all__`

## Para qué sirve

cortex.ci.markdown_formatter — Render a ``ValidationResult`` as Markdown
for the Level 2 PR comment workflow.

The output is delimited by a sentinel marker so the workflow can
de-duplicate on re-runs (``gh pr comment --edit-last`` or equivalent).
The marker is exact and stable across releases.

## Relaciones

### Recibe de

- `cortex.ci.result` (ScopeDriftFinding, ValidationResult)
- Dependencias externas/stdlib: `__future__`

### Envía a

- `cortex.ci`
- `cortex.cli.ci`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 121.
Docstrings de símbolos públicos:
- `render_pr_comment`: Format a Markdown block ready to post as a PR comment.

---
Fuente: código de `cortex/ci/markdown_formatter.py` (AST + grafo de imports internos). No se usó documentación previa.
