# rust/crates/cortex-cli/src/commands/mod.rs

## Qué tiene adentro

`pub mod` de todos los subcomandos: autopilot, ci_cmd, docs_cmd, doctor, finish_cmd, hu_cmd, ide_cmd, mcp_cmd, memory_report, misc, next_cmd, org_config, pr_context_cmd, promote, remember_cmd, review, session_cmd, setup_cmd, tutor, webgraph.

## Para qué sirve

Registro de módulos de comandos.

## Relaciones

### Recibe de

- Archivos hermanos.

### Envía a

- `main.rs` / `lib.rs`.

### Notas de implementación observadas en el código

search/context/stats/reindex no están aquí: viven en `memory_cmds`.
