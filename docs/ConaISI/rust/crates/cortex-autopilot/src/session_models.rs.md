# rust/crates/cortex-autopilot/src/session_models.rs

## Qué tiene adentro

Subconjunto mínimo y fiel de `cortex.session.models` consumido por la capa de decisión (SessionStatus/CheckpointSource/Checkpoint/Record). Campos no usados por policies/lifecycle quedan fuera por diseño; el motor completo de sesiones es territorio futuro.
Archivo de 116 líneas.
Símbolos públicos observados:
- `pub struct Checkpoint`
- `pub struct SessionRecord`

## Para qué sirve

Subconjunto mínimo y fiel de `cortex.session.models` consumido por la capa de decisión (SessionStatus/CheckpointSource/Checkpoint/Record). Campos no usados por policies/lifecycle quedan fuera por diseño; el motor completo de sesiones es territorio futuro.

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-autopilot`: cortex-app, cortex-enterprise, cortex-workspace, cortex-mcp

### Envía a

- Crate `cortex-autopilot` envía hacia: cortex-cli autopilot, cortex-mcp handlers

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-autopilot/src/session_models.rs`.
