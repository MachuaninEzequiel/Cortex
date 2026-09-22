# rust/crates/cortex-mcp/src/tools_catalog.rs

## Qué tiene adentro

- `SERVER_VERSION = "2.2"`.
- `CHECKPOINT_SOURCE_VALUES`: cortex-sync, cortex-SDDwork, cortex-code-explorer, cortex-code-implementer, cortex-code-designer, user-skill, ide-hook, manual, ci-bot.
- `build_tool_definitions() -> Vec<Value>`: 32 objetos `{name, title:null, description, inputSchema, outputSchema:null, icons, annotations, meta, execution}` en **ese orden de claves**.

Cada tool declara inputSchema (query, session_id, payload por doc_type, etc.).

## Para qué sirve

SSoT de `list_tools`. Cualquier cambio de nombre/description/schema debe ir al golden Python.

## Relaciones

### Recibe de

- Nada en runtime (datos estáticos).

### Envía a

- `server.rs` (list_tools + ping version).
- `tests/mcp_golden_contract.rs`.

### Notas de implementación observadas en el código

`serde_json` con preserve_order para igualar inserción Python. `cortex_write_doc` enum: session, handoff, adr, decision, incident, postmortem, runbook, architecture, changelog, glossary, hu — **no** spec ni design (esos van a create_spec / write_design_note_canonical).
