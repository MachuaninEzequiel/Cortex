# cortex/ci/result.py

## Qué tiene adentro

- **Ruta de código:** `cortex/ci/result.py` (104 líneas).
- **Módulo Python:** `cortex.ci.result`.
- **Docstring del módulo:** cortex.ci.result — Typed inputs and outputs for the CI validator.
- **Clases definidas:**
  - `ValidationInput`
    - Everything the validator needs to evaluate a single PR.
  - `ScopeDriftFinding`
    - One file that violated ``spec.files_in_scope``.
  - `ValidationResult`
    - Outcome of :class:`CiValidator.validate`.
    - Métodos públicos/especiales: `to_json_dict`
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.ci.result — Typed inputs and outputs for the CI validator.

## Relaciones

### Recibe de

- `cortex.documenter.spec_loader` (LoadedSpec)
- `cortex.session.models` (SessionRecord, VerificationHookResult)
- Dependencias externas/stdlib: `__future__`, `dataclasses`, `pathlib`, `typing`

### Envía a

- `cortex.ci`
- `cortex.ci.markdown_formatter`
- `cortex.ci.session_matcher`
- `cortex.ci.validator`
- `cortex.cli.ci`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 104.
Docstrings de símbolos públicos:
- `ValidationResult.to_json_dict`: JSON-serialisable representation. Stable across releases.

---
Fuente: código de `cortex/ci/result.py` (AST + grafo de imports internos). No se usó documentación previa.
