# rust/crates/cortex-enterprise/src/clock.rs

## Qué tiene adentro

Archivo de 60 líneas.
Símbolos públicos observados:
- `pub trait Clock: Send + Sync`
- `pub struct SystemClock`
- `pub struct FixedClock(DateTime<Utc>)`
- `pub fn isoformat_full(value: DateTime<Utc>) -> String`
- `pub fn isoformat_seconds(value: DateTime<Utc>) -> String`
- `pub fn default_now_string() -> String`

## Para qué sirve

Módulo fuente `rust/crates/cortex-enterprise/src/clock.rs` del crate `cortex-enterprise`.

## Relaciones

### Recibe de

- `use crate::error::EnterpriseError`
- Contexto de crate `cortex-enterprise`: cortex-app, cortex-setup, cortex-workspace

### Envía a

- Crate `cortex-enterprise` envía hacia: cortex-cli enterprise, cortex-doctor, cortex-actions knowledge.promote, cortex-brain-app org_memory

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-enterprise/src/clock.rs`.
