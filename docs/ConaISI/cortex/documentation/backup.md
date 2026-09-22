# cortex/documentation/backup.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/backup.py` (102 líneas).
- **Módulo Python:** `cortex.documentation.backup`.
- **Docstring del módulo:** cortex.documentation.backup - Tar.gz backup helpers for migrate operations.
- **Funciones de módulo:**
  - `create_backup(vault_path)` — Create a tar.gz snapshot of ``vault_path``.
  - `restore_backup(backup_path, target_parent)` — Extract ``backup_path`` into ``target_parent``.
  - `list_backups(backups_dir)` — Return backups in ``backups_dir`` sorted by name (timestamp asc).
- **Constantes / símbolos de módulo:** `_BACKUP_PREFIX`, `_BACKUP_SUFFIX`, `__all__`

## Para qué sirve

cortex.documentation.backup - Tar.gz backup helpers for migrate operations.

The migration tool (``cortex docs migrate --apply``) calls
``create_backup`` before writing anything to disk so the operator can
``cortex docs restore`` if something goes sideways.

Backups live in ``<workspace>/.cortex/backups/`` and are named after a
UTC timestamp.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `logging`, `tarfile`, `__future__`, `datetime`, `pathlib`

### Envía a

- `cortex.cli.docs_migrate`
- `cortex.documentation.migration`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 102.
Docstrings de símbolos públicos:
- `create_backup`: Create a tar.gz snapshot of ``vault_path``.
- `restore_backup`: Extract ``backup_path`` into ``target_parent``.
- `list_backups`: Return backups in ``backups_dir`` sorted by name (timestamp asc).

---
Fuente: código de `cortex/documentation/backup.py` (AST + grafo de imports internos). No se usó documentación previa.
