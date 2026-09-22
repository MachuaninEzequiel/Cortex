# cortex/pr_capture.py

## Qué tiene adentro

- Helpers git: `_run_git`, `_get_files_changed` (`diff --name-only base...head`), `_get_diff_summary` (`--stat`), `_detect_db_migrations` por substrings (`migration`, `schema`, alembic, sql, prisma, …).
- API pública (docstring): `capture_from_github()` (env GitHub Actions), `capture_manual(...)`, `capture_from_json`.
- Sale un `PRContext`.

## Para qué sirve

Entrada DevSecDocOps: materializar un PR como objeto tipado.

## Relaciones

### Recibe de

- Env vars GH / git / JSON.
- `cortex.models.PRContext`.

### Envía a

- CLI `pr-context`, `PRService`, `DocGenerator`.

---
Fuente: lectura de `cortex/pr_capture.py`. No se usó documentación previa.
