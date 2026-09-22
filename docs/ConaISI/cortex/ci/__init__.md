# cortex/ci/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/ci/__init__.py` (31 líneas).
- **Módulo Python:** `cortex.ci`.
- **Docstring del módulo:** cortex.ci — Phase 07 CI plugin (Pluggable Middle).
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.ci — Phase 07 CI plugin (Pluggable Middle).

Provider-agnostic validation of pull requests against the matching
Cortex Session + spec. Exposes:

* :func:`validate_pull_request` — top-level entry point used by the
  CLI (``cortex ci validate-pr``).
* :class:`ValidationResult` — typed output (also serialised to JSON for
  workflow consumers).
* :func:`render_pr_comment` — Markdown formatter for the Level 2 PR
  comment workflow.

The CLI lives in :mod:`cortex.cli.ci`; this package holds the pure
logic.

## Relaciones

### Recibe de

- `cortex.ci.markdown_formatter` (render_pr_comment)
- `cortex.ci.result` (ScopeDriftFinding, ValidationInput, ValidationResult)
- `cortex.ci.validator` (CiValidator, validate_pull_request)
- Dependencias externas/stdlib: `__future__`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 31.
Reexportes observados:
- cortex.ci.markdown_formatter: render_pr_comment
- cortex.ci.result: ScopeDriftFinding, ValidationInput, ValidationResult
- cortex.ci.validator: CiValidator, validate_pull_request

---
Fuente: código de `cortex/ci/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
