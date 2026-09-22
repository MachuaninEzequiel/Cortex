# cortex/ci/validator.py

## Qué tiene adentro

- **Ruta de código:** `cortex/ci/validator.py` (264 líneas).
- **Módulo Python:** `cortex.ci.validator`.
- **Docstring del módulo:** cortex.ci.validator — Validate a PR against its Session + spec.
- **Clases definidas:**
  - `CiValidator`
    - Run the Level 1 validation pipeline.
    - Métodos públicos/especiales: `__init__`, `validate`
    - Métodos internos: `_load_spec`, `_build_summary`
- **Funciones de módulo:**
  - `validate_pull_request(payload)` — Convenience wrapper used by the CLI.
  - `_parse_files_from_diff(diff_text)` — Extract the changed file paths from a unified diff body.
  - `_no_session_result()` — Build a ``status=blocked`` result when no Session matches.
- **Constantes / símbolos de módulo:** `EXIT_PASS`, `EXIT_WARN`, `EXIT_BLOCKED`, `EXIT_ERROR`, `__all__`

## Para qué sirve

cortex.ci.validator — Validate a PR against its Session + spec.

The validator orchestrates the existing primitives (session matcher,
spec loader, scope cross-check, verification runner) into a single
result object. It is the heart of ``cortex ci validate-pr`` (Phase 07 /
Level 1).

## Relaciones

### Recibe de

- `cortex.ci.result` (ScopeDriftFinding, ValidationInput, ValidationResult)
- `cortex.documenter.reconstruction` (_scope_cross_check)
- `cortex.documenter.spec_loader` (LoadedSpec, load_spec)
- `cortex.session.models` (SessionRecord, SessionStatus)
- `cortex.session.service` (SessionService)
- `cortex.session.verification` (VerificationRunner)
- Dependencias externas/stdlib: `__future__`, `collections.abc`, `pathlib`

### Envía a

- `cortex.ci`
- `cortex.cli.ci`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 264.
Docstrings de símbolos públicos:
- `CiValidator.validate`: Return a :class:`ValidationResult` for ``payload``.
- `validate_pull_request`: Convenience wrapper used by the CLI.

---
Fuente: código de `cortex/ci/validator.py` (AST + grafo de imports internos). No se usó documentación previa.
