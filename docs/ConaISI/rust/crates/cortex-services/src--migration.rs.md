# rust/crates/cortex-services/src/migration.rs

## Qué tiene adentro

Migrador de bóvedas. Tipos: `NoteDiff`, `MigrationResult`, `MigrateOpts`, `ValidatePayload`. APIs: `migrate_vault`, `validate_vault`, `format_report`, `python_title`, `doc_type_from_path`, `split_frontmatter_and_body`, `create_backup` (`tar czf`), `list_backups`, `restore_backup`.

Lee cada `.md` ordenado, infiere `doc_type` por ruta, construye frontmatter canónico. Idempotente si `schema_version: 1` y `doc_type` string (salvo `force`). Campos legacy → prefijo `legacy_`.

## Para qué sirve

`cortex docs migrate|validate|restore|list-backups`.

## Relaciones

### Recibe de

- Vault en disco.
- `cortex_setup::{DocType, slugify, yaml::Yaml, fingerprint}`.
- `regex`, `chrono`, `serde_yaml`.

### Envía a

- Archivos reescritos (si apply) o reporte dry-run.
- Backups `.tar.gz` vía CLI `tar`.

### Notas de implementación observadas en el código

Parser YAML es `serde_yaml` (mensajes de error ≠ PyYAML; gates normalizan `{{YAML_ERR}}`). El contenido exacto del tar no es contrato, sí existencia/nombre.
