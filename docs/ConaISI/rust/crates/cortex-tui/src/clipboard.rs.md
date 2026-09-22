# rust/crates/cortex-tui/src/clipboard.rs

## Qué tiene adentro

Copia nativa al portapapeles mediante secuencia de escape OSC 52 (spec §7). Copia texto al portapapeles del emulador de terminal usando OSC 52.
Archivo de 8 líneas.
Símbolos públicos observados:
- `pub fn copy_to_clipboard(text: &str)`

## Para qué sirve

Copia nativa al portapapeles mediante secuencia de escape OSC 52 (spec §7). Copia texto al portapapeles del emulador de terminal usando OSC 52.

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/clipboard.rs`.
