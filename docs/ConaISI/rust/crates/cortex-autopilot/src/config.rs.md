# rust/crates/cortex-autopilot/src/config.rs

## Qué tiene adentro

Puerto de `cortex.autopilot.config`: `autopilot.yaml` opcional con defaults seguros.
Archivo de 64 líneas.
Símbolos públicos observados:
- `pub struct ConfigError(pub String)`
- `pub struct AutopilotConfig`
- `pub fn load_autopilot_config(layout: &WorkspaceLayout) -> Result<AutopilotConfig, ConfigError>`

## Para qué sirve

Puerto de `cortex.autopilot.config`: `autopilot.yaml` opcional con defaults seguros.

## Relaciones

### Recibe de

- `use cortex_workspace::WorkspaceLayout`
- Contexto de crate `cortex-autopilot`: cortex-app, cortex-enterprise, cortex-workspace, cortex-mcp

### Envía a

- Crate `cortex-autopilot` envía hacia: cortex-cli autopilot, cortex-mcp handlers

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-autopilot/src/config.rs`.
