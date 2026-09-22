# rust/crates/cortex-companion/src/lib.rs

## Qué tiene adentro

cortex-companion — superficie única mouse-first (Obra 08 stream B).  Especificación: `docs/transformacion/14-HERDR-COMPANION.md`. Estado por task: B1 engine (Backend + paridad), B2 aprobaciones (run_guarded), B3 app ELM-lite mouse-first, B4 widgets + Home, B5 Menu anti-olvido, B6 Sessions+Actions con modal integrado a la máquina de estados (`app::pending` + `effects::apply`), B7 Search con feedback explícito formato-oráculo (`feedback.rs`), B8 Brain híbrido (`brain_panel.rs`: reads directas por el engine in-process, propuestas de mutación con [Ejecutar] → `run_guarded`, router determinista cero tokens / LLM opcional con protocolo TOOL).
Archivo de 59 líneas.
Símbolos públicos observados:
- `pub mod app`
- `pub mod approval`
- `pub mod brain_panel`
- `pub mod clipboard`
- `pub mod effects`
- `pub mod engine`
- `pub mod feedback`
- `pub mod herdr`
- `pub mod hud_brand`
- `pub mod menu`
- `pub mod runner`
- `pub mod screens`
- `pub mod theme`
- `pub mod widgets`
- `pub enum CompanionMode`
- `pub enum Screen`
- `pub struct UiRequest`

## Para qué sirve

cortex-companion — superficie única mouse-first (Obra 08 stream B).  Especificación: `docs/transformacion/14-HERDR-COMPANION.md`. Estado por task: B1 engine (Backend + paridad), B2 aprobaciones (run_guarded), B3 app ELM-lite mouse-first, B4 widgets + Home, B5 Menu anti-olvido, B6 Sessions+Actions con modal integrado a la máquina de estados (`app::pending` + `effects::apply`), B7 Search con feedback explícito formato-oráculo (`feedback.rs`), B8 Brain híbrido (`brain_panel.rs`: reads directas por el engine in-process, propuestas de mutación con [Ejecutar] → `run_guarded`, router determinista cero tokens / LLM opcional con protocolo TOOL).

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-companion`: cortex-cli, cortex-actions, cortex-app, cortex-config, cortex-workspace, cortex-branding, cortex-brain, herdr CLI

### Envía a

- Crate `cortex-companion` envía hacia: TUI ratatui, action_log.jsonl, panes herdr

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/src/lib.rs`.
El crate/archivo declara `forbid(unsafe_code)`.
