# cortex/enterprise/maintenance.py

## Qué tiene adentro

- **Ruta de código:** `cortex/enterprise/maintenance.py` (169 líneas).
- **Módulo Python:** `cortex.enterprise.maintenance`.
- **Docstring del módulo:** cortex.enterprise.maintenance - Retention scan and archival.
- **Clases definidas:**
  - `RetentionViolation`
    - A note whose retention window has elapsed.
- **Funciones de módulo:**
  - `scan_retention_violations(vault_root)` — Return notes in ``vault_root`` whose retention window has elapsed.
  - `archive_violations(violations, vault_root)` — Move ``violations`` into ``<vault_root>/_archived/`` preserving paths.
  - `_resolve_retention(fm, doc_type, policy)`
  - `_parse_dt(value)`
- **Constantes / símbolos de módulo:** `_ARCHIVE_FOLDER`, `__all__`

## Para qué sirve

cortex.enterprise.maintenance - Retention scan and archival.

Implements the *retention policy enforcement* part of Fase 10:

- ``scan_retention_violations`` walks a vault and returns notes whose
  ``retention_days`` (or the default for their DocType) has elapsed.
- ``archive_violations`` moves the violators to ``<vault>/_archived/``
  preserving the original directory structure.

No automatic execution: callers must invoke the functions explicitly. A
CLI wrapper (e.g. ``cortex docs maintenance``) is the natural entrypoint
but lives outside this module.

## Relaciones

### Recibe de

- `cortex.documentation.common` (parse_frontmatter_lenient)
- `cortex.enterprise.models` (EnterpriseOrgConfig, RetentionPolicy)
- Dependencias externas/stdlib: `logging`, `shutil`, `__future__`, `dataclasses`, `datetime`, `pathlib`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 169.
Docstrings de símbolos públicos:
- `scan_retention_violations`: Return notes in ``vault_root`` whose retention window has elapsed.
- `archive_violations`: Move ``violations`` into ``<vault_root>/_archived/`` preserving paths.

---
Fuente: código de `cortex/enterprise/maintenance.py` (AST + grafo de imports internos). No se usó documentación previa.
