# rust/crates/cortex-mcp/src/server.rs

## Qué tiene adentro

- Constantes: `STARTUP_GRACE_SECONDS=2.0`, `ERROR_RECENT_WINDOW_SECONDS=300`, `ERROR_HISTORY_MAXLEN=10`.
- `ErrorEntry`, `MemoryBackend`, `CountingMemory`, `CortexMcpServer` (backends Option Mutex, `spec_state`, `project_root`).
- `tool_routes()`: mapa nombre → handler Python-espejo (sin sync_vault).
- Dispatch por familia: ping, sessions, search, docs, spec/proposal, self_review, finish, autopilot, sync_vault inline.
- Transporte: `serve_stdio_blocking`.

`cortex_ping` payload: status starting/degraded/ok, version, uptime, indices, models, last_error, JSON indent=2 ensure_ascii=False.

## Para qué sirve

Servidor MCP: anuncia tools y rutea llamadas.

## Relaciones

### Recibe de

- Transporte stdio (agente IDE).
- Backends inyectados por `mcp_cmd`.
- `tools_catalog`.

### Envía a

- Handlers `*_text` que devuelven String al cliente MCP.
- Historial de errores in-memory.

### Notas de implementación observadas en el código

Tool desconocida → mensaje estable. Sin backend → fallo explícito documentado, no se finge paridad. `spec_state` registra cada tool call (gobernanza sync_ticket → create_spec y gap de 2s del proposal).
