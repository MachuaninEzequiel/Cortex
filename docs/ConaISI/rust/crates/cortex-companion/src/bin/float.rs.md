# rust/crates/cortex-companion/src/bin/float.rs

## Qué tiene adentro

Binario `cortex-herdr-float`: Abre el Companion en modo HUD flotante (overlay sobre la terminal).
Archivo de 53 líneas.

## Para qué sirve

Binario `cortex-herdr-float`: Abre el Companion en modo HUD flotante (overlay sobre la terminal).

## Relaciones

### Recibe de

- `use cortex_companion::herdr`
- `use cortex_companion::runner::run_app`
- `use cortex_companion::CompanionMode`
- Contexto de crate `cortex-companion`: cortex-cli, cortex-actions, cortex-app, cortex-config, cortex-workspace, cortex-branding, cortex-brain, herdr CLI

### Envía a

- Crate `cortex-companion` envía hacia: TUI ratatui, action_log.jsonl, panes herdr
- Proceso: argv/stdio o spawn de UI.

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/src/bin/float.rs`.
