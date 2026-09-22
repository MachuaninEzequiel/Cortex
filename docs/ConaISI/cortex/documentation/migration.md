# cortex/documentation/migration.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/migration.py` (566 líneas).
- **Módulo Python:** `cortex.documentation.migration`.
- **Docstring del módulo:** cortex.documentation.migration - Vault backfill to the canonical schema.
- **Clases definidas:**
  - `NoteDiff`
    - Description of a single migration step.
  - `MigrationResult`
    - Aggregated outcome of a ``migrate_vault`` call.
- **Funciones de módulo:**
  - `migrate_vault(vault_path)` — Migrate ``vault_path`` to the canonical schema.
  - `validate_vault(vault_path)` — Validate every note in ``vault_path`` against the canonical schema.
  - `format_report(result)` — Human-readable summary of a ``MigrationResult``.
  - `_compute_diff(md_path, vault_root)`
  - `_build_new_frontmatter(md_path, legacy, doc_type, vault_root, preserve_legacy, now)`
  - `_apply_diff(diff)`
  - `_read_body(md_path)`
  - `_resolve_tags(value)`
  - `_resolve_status(value, doc_type)`
  - `_resolve_datetime(value, path, now)`
  - `_extract_wiki_links(body)`
  - `_type_specific_for(doc_type, md_path, legacy)` — Compute the minimum type-specific fields required by each schema.
  - `_derive_session_id(path)`
- **Constantes / símbolos de módulo:** `_CANONICAL_TOP_LEVEL`, `_LEGACY_MAPPED`, `_TYPE_SPECIFIC_FIELDS`, `_ADR_NUMBER_RE`, `_INC_NUMBER_RE`, `_PM_NUMBER_RE`, `_WIKI_LINK_RE`, `_SESSION_ID_PREFIX_RE`, `__all__`

## Para qué sirve

cortex.documentation.migration - Vault backfill to the canonical schema.

Reads every ``.md`` file in a vault, infers the DocType from the path,
builds a canonical frontmatter, and either reports the diff (dry-run) or
rewrites the file (``apply=True``).

Idempotency: a file whose frontmatter already declares ``schema_version: 1``
and a known ``doc_type`` is skipped. Re-running on a migrated vault is a
no-op (unless ``force=True``).

Backwards-compat: legacy fields not part of the canonical schema are
preserved under a ``legacy_<name>`` prefix so they remain auditable.

## Relaciones

### Recibe de

- `cortex.documentation.backup` (create_backup)
- `cortex.documentation.common` (compute_fingerprint, parse_frontmatter_lenient, slugify, split_frontmatter_and_body, yaml_dump_safe)
- `cortex.documentation.doc_type` (VALID_STATUSES, DocType, doc_type_from_path)
- Dependencias externas/stdlib: `logging`, `re`, `__future__`, `dataclasses`, `datetime`, `pathlib`, `typing`

### Envía a

- `cortex.cli.docs_migrate`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 566.
Docstrings de símbolos públicos:
- `migrate_vault`: Migrate ``vault_path`` to the canonical schema.
- `validate_vault`: Validate every note in ``vault_path`` against the canonical schema.
- `format_report`: Human-readable summary of a ``MigrationResult``.

---
Fuente: código de `cortex/documentation/migration.py` (AST + grafo de imports internos). No se usó documentación previa.
