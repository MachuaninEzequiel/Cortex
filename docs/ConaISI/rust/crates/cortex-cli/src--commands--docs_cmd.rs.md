# rust/crates/cortex-cli/src/commands/docs_cmd.rs

## Qué tiene adentro

`docs search` (filtros doc-type/status/tag/scope/max-age/project-id/strict, format text|json|compact) vía ContextEnricher. `migrate`, `validate`, `restore`, `list-backups` (`cortex_services::migration`). `routing-table` (tabla de DocType).

## Para qué sirve

Búsqueda documental filtrada y migración de vault.

## Relaciones

### Recibe de

- NativeMemory + `cortex_app::context::{filters, presenter, ContextEnricher}`.
- `cortex_app::semantic::routing`.
- migration APIs.

### Envía a

- stdout / archivos migrados / backups tar.

### Notas de implementación observadas en el código

scope default `"all"` en search CLI (MCP search default local).
