# cortex/documenter/spec_loader.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documenter/spec_loader.py` (133 líneas).
- **Módulo Python:** `cortex.documenter.spec_loader`.
- **Docstring del módulo:** cortex.documenter.spec_loader — Read a spec back from disk.
- **Clases definidas:**
  - `LoadedSpec`
    - Subset of spec fields the reconstructor cares about.
- **Funciones de módulo:**
  - `load_spec(path)` — Parse the spec at ``path`` and return a :class:`LoadedSpec`.
  - `_empty(path)`
  - `_load_hooks(raw)` — Coerce raw frontmatter entries into :class:`VerificationHook` list.
  - `_extract_section(path, heading)` — Pull the body text under ``heading`` (used as a fallback for legacy specs).
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.documenter.spec_loader — Read a spec back from disk.

The reconstruction algorithm needs to introspect the spec the session was
anchored on (title, goal, files_in_scope, verification_hooks). This module
parses the YAML frontmatter of a persisted spec note and returns a
typed :class:`LoadedSpec`.

The loader is lenient: a spec without ``verification_hooks`` (e.g. one
created before the Pluggable Middle architecture) loads with an empty
list and the reconstruction skips verification with a warning.

## Relaciones

### Recibe de

- `cortex.documentation.common` (parse_frontmatter_lenient)
- `cortex.session.models` (VerificationHook)
- Dependencias externas/stdlib: `logging`, `__future__`, `dataclasses`, `pathlib`, `typing`, `pydantic`

### Envía a

- `cortex.ci.result`
- `cortex.ci.validator`
- `cortex.documenter`
- `cortex.documenter.reconstruction`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 133.
Docstrings de símbolos públicos:
- `load_spec`: Parse the spec at ``path`` and return a :class:`LoadedSpec`.

---
Fuente: código de `cortex/documenter/spec_loader.py` (AST + grafo de imports internos). No se usó documentación previa.
