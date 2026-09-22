# rust/crates/cortex-tui/src/app/effect.rs

## Qué tiene adentro

Efectos (spec §2/§5): el reducer puede devolver efectos pero NUNCA ejecutarlos. El runtime (loop de la pantalla) los interpreta y devuelve acciones tipadas (`SessionsLoaded`/`SessionsFailed`, más adelante `TaskEvent`).
Archivo de 37 líneas.
Símbolos públicos observados:
- `pub enum Effect`
Tests en el mismo archivo: `efectos_son_comparables`

## Para qué sirve

Efectos (spec §2/§5): el reducer puede devolver efectos pero NUNCA ejecutarlos. El runtime (loop de la pantalla) los interpreta y devuelve acciones tipadas (`SessionsLoaded`/`SessionsFailed`, más adelante `TaskEvent`).

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/app/effect.rs`.
