# rust/crates/cortex-companion/src/herdr.rs

## Qué tiene adentro

Integración con binario `herdr`:

- `HerdrAgentInfo { pane_id, agent, agent_status, cwd, focused }`
- `detect_target_agent`: `herdr api snapshot`, JSON panes; prioriza cwd del proyecto, luego pane con `agent`
- `send_text_to_pane` (marcado no usar desde Companion: HUD copia OSC 52)
- `report_agent_status` / `report_metadata` (`pane report-agent` / `report-metadata`, source=cortex)
- `spawn_split_sidecar` / `spawn_float_hud` / `spawn_copilot_split`: `herdr plugin pane open --plugin cortex.companion` con entrypoint sidecar/float/copilot, placement split/float
- ratios default 0.30 / 0.25 / 0.35
- `conclude_spawn`, `build_plugin_open_args`, `build_resize_args`

## Para qué sirve

Dock/HUD/copilot de Cortex junto al agente en Herdr.

## Relaciones

### Recibe de

- CLI `herdr` (stdout JSON)
- `project_root`

### Envía a

- procesos herdr (plugin pane, report-*)
- binarios `cortex-herdr-sidecar|float|copilot`

### Notas de implementación observadas en el código

Fallos de herdr se tragan en report_agent (`let _ = cmd.output()`); spawn/metadata sí retornan `Result`.
