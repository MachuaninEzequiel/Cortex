# rust/crates/cortex-workspace/src/lib.rs

## Qué tiene adentro

Fachada pública del crate. Reexporta módulos `git_policy`, `handoff`, `layout`, `pyyaml`, `runtime_context`, `skills` y tipos/funciones clave (`WorkspaceLayout`, `AgentHandoff`, `install_skills`, `slugify`, patrones gitignore).

## Para qué sirve

Punto de entrada único para consumidores (CLI, MCP, doctor, autopilot, webgraph). Documenta que es el porteo P12B-1 y que `resolve_safe` **no** vive aquí.

## Relaciones

### Recibe de

- Módulos internos del crate.

### Envía a

- Cualquier crate que dependa de `cortex-workspace` (en este lote: `cortex-cli`, `cortex-mcp`; también `cortex-autopilot`, `cortex-doctor`, `cortex-enterprise`, `cortex-webgraph-server`, `cortex-pipeline`, `cortex-tutor`, `cortex-companion`, `cortex-brain-app` según el workspace).

### Notas de implementación observadas en el código

`#![forbid(unsafe_code)]`. El comentario del módulo nombra el oráculo `bench/parity/workspace_golden_p12b.py` y el checker `examples/workspace_check.rs`.
