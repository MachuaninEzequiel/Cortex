# cortex/documentation/inventory.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/inventory.py` (130 líneas).
- **Módulo Python:** `cortex.documentation.inventory`.
- **Docstring del módulo:** cortex.documentation.inventory - Scan the vault to produce a diagnostic snapshot.
- **Clases definidas:**
  - `VaultInventory`
    - Snapshot of a vault's current state.
- **Funciones de módulo:**
  - `classify_path(path, vault_root)` — Infer a doc_type slug from a markdown file's location in the vault.
  - `inventory_vault(vault_path)` — Scan a vault directory and produce a ``VaultInventory``.
- **Constantes / símbolos de módulo:** `_SUBFOLDER_TO_DOC_TYPE`, `_ADR_FILENAME_RE`

## Para qué sirve

cortex.documentation.inventory - Scan the vault to produce a diagnostic snapshot.

Used by migration tooling (Fase 11) and by ``cortex docs status`` reports.

## Relaciones

### Recibe de

- `cortex.documentation.common` (parse_frontmatter_lenient)
- Dependencias externas/stdlib: `re`, `__future__`, `collections`, `dataclasses`, `pathlib`

### Envía a

- `cortex.documentation`
- `cortex.semantic.vault_reader`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 130.
Docstrings de símbolos públicos:
- `classify_path`: Infer a doc_type slug from a markdown file's location in the vault.
- `inventory_vault`: Scan a vault directory and produce a ``VaultInventory``.

---
Fuente: código de `cortex/documentation/inventory.py` (AST + grafo de imports internos). No se usó documentación previa.
