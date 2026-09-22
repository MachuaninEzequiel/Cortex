# rust/crates/cortex-tui/src/terminal.rs

## Qué tiene adentro

Ciclo de vida de terminal (spec §15): raw mode + alternate screen + cursor oculto, con restauración RAII garantizada (Drop) y hook de panic.  Extraído de `cortex-cli session watch` (T6-b): el CLI ya no contiene el lifecycle; acá vive y se reutiliza por cualquier pantalla.
Archivo de 99 líneas.
Símbolos públicos observados:
- `pub struct Tui`
- `pub fn terminal_size() -> (u16, u16)`
Tests en el mismo archivo: `restore_es_idempotente`, `drop_restaura_si_falta_restore_explicito`

## Para qué sirve

Ciclo de vida de terminal (spec §15): raw mode + alternate screen + cursor oculto, con restauración RAII garantizada (Drop) y hook de panic.  Extraído de `cortex-cli session watch` (T6-b): el CLI ya no contiene el lifecycle; acá vive y se reutiliza por cualquier pantalla.

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/terminal.rs`.
