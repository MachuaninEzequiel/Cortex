# rust/crates/cortex-setup/src/doc_type.rs

## Qué tiene adentro

Enum `DocType` (13 valores), `as_str`, `parse`, `valid_statuses` (ordenados; primer status = default Python).

## Para qué sirve

Tipos documentales canónicos del vault.

## Relaciones

### Recibe de

- Strings slug.

### Envía a

- routing, writers, migration (services), CLI routing-table.

### Notas de implementación observadas en el código

Statuses session incluyen auto-draft/completed/draft/fallback/handoff; spec abandoned/approved/done/draft/implementing; etc.
