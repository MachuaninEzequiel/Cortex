# rust/crates/cortex-cli/src/commands/misc.rs

## Qué tiene adentro

`AGENT_GUIDELINES` via `include_str!` de `cortex/agent_guidelines.md`. `agent_guidelines()` imprime + newline. `install_skills --dest` (default `.cortex/skills`) llama `cortex_workspace::skills::install_skills`.

## Para qué sirve

`cortex agent-guidelines` e `install-skills`.

## Relaciones

### Recibe de

- Markdown embebido del paquete Python.
- Bundle Obsidian de cortex-workspace.

### Envía a

- stdout; archivos en dest.

### Notas de implementación observadas en el código

Si empty: `"All skills already installed."`
