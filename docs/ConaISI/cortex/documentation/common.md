# cortex/documentation/common.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/common.py` (139 líneas).
- **Módulo Python:** `cortex.documentation.common`.
- **Docstring del módulo:** cortex.documentation.common - Shared helpers used across documentation layers.
- **Funciones de módulo:**
  - `slugify(value)` — Convert a string to a filesystem-safe slug.
  - `compute_fingerprint(content)` — Compute SHA-256 hex digest of content. Returns 64-char lowercase hex.
  - `yaml_dump_safe(data)` — Dump dict to YAML with safe defaults.
  - `yaml_load_safe(text)` — Parse YAML safely. Returns empty dict for empty or whitespace-only input.
  - `split_frontmatter_and_body(content)` — Split markdown content into ``(frontmatter_yaml, body)``.
  - `has_frontmatter(content)` — Return True if content starts with a valid frontmatter block.
  - `parse_frontmatter_lenient(path)` — Parse a markdown file's frontmatter without strict schema validation.
- **Constantes / símbolos de módulo:** `_SLUG_STRIP`, `_SLUG_SEP`, `_SLUG_COLLAPSE`, `_FRONTMATTER_RE`

## Para qué sirve

cortex.documentation.common - Shared helpers used across documentation layers.

All functions here are pure: no I/O, no global state mutation (except for
file reads in ``parse_frontmatter_lenient``).

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `hashlib`, `re`, `unicodedata`, `yaml`, `__future__`, `pathlib`, `typing`

### Envía a

- `cortex.documentation`
- `cortex.documentation.inventory`
- `cortex.documentation.migration`
- `cortex.documentation.validation`
- `cortex.documentation.writers`
- `cortex.documenter.spec_loader`
- `cortex.enterprise.maintenance`
- `cortex.enterprise.promotion_doctype`
- `cortex.semantic.chunker`
- `cortex.semantic.vault_reader`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 139.
Docstrings de símbolos públicos:
- `slugify`: Convert a string to a filesystem-safe slug.
- `compute_fingerprint`: Compute SHA-256 hex digest of content. Returns 64-char lowercase hex.
- `yaml_dump_safe`: Dump dict to YAML with safe defaults.
- `yaml_load_safe`: Parse YAML safely. Returns empty dict for empty or whitespace-only input.
- `split_frontmatter_and_body`: Split markdown content into ``(frontmatter_yaml, body)``.
- `has_frontmatter`: Return True if content starts with a valid frontmatter block.
- `parse_frontmatter_lenient`: Parse a markdown file's frontmatter without strict schema validation.

---
Fuente: código de `cortex/documentation/common.py` (AST + grafo de imports internos). No se usó documentación previa.
