# rust/crates/cortex-companion/src/clipboard.rs

## Qué tiene adentro

Copia al clipboard del terminal (OSC 52). Cero deps nuevas.  El HUD nunca inyecta texto al pane del agente: el usuario pega.
Archivo de 54 líneas.
Símbolos públicos observados:
- `pub fn copy(text: &str) -> io::Result<()>`
Tests en el mismo archivo: `base64_hello`

## Para qué sirve

Copia al clipboard del terminal (OSC 52). Cero deps nuevas.  El HUD nunca inyecta texto al pane del agente: el usuario pega.

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-companion`: cortex-cli, cortex-actions, cortex-app, cortex-config, cortex-workspace, cortex-branding, cortex-brain, herdr CLI

### Envía a

- Crate `cortex-companion` envía hacia: TUI ratatui, action_log.jsonl, panes herdr

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/src/clipboard.rs`.
