# cortex/cli/docs_migrate.py

## Qué tiene adentro

- **Ruta de código:** `cortex/cli/docs_migrate.py` (161 líneas).
- **Módulo Python:** `cortex.cli.docs_migrate`.
- **Docstring del módulo:** cortex.cli.docs_migrate - ``cortex docs migrate/validate/restore`` (Fase 11).
- **Funciones de módulo:**
  - `_main()` — Vault migration tools (Fase 11).
  - `_default_vault(project_root)`
  - `migrate(project_root, path, apply, force, output, no_backup, json_output)` — Backfill the vault to the canonical schema.
  - `validate(project_root, all_files, json_output)` — Validate every note in the vault against the canonical schema.
  - `restore(backup, target, project_root)` — Restore the vault from a backup tar.gz.
  - `list_backups_cmd(project_root)` — List backup snapshots.

## Para qué sirve

cortex.cli.docs_migrate - ``cortex docs migrate/validate/restore`` (Fase 11).

## Relaciones

### Recibe de

- `cortex.documentation.backup` (list_backups, restore_backup)
- `cortex.documentation.migration` (format_report, migrate_vault, validate_vault)
- Dependencias externas/stdlib: `json`, `typer`, `__future__`, `pathlib`

### Envía a

- `cortex.cli.docs_subcommand`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 161.
Docstrings de símbolos públicos:
- `migrate`: Backfill the vault to the canonical schema.
- `validate`: Validate every note in the vault against the canonical schema.
- `restore`: Restore the vault from a backup tar.gz.
- `list_backups_cmd`: List backup snapshots.

---
Fuente: código de `cortex/cli/docs_migrate.py` (AST + grafo de imports internos). No se usó documentación previa.
