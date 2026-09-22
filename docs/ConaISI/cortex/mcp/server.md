# cortex/mcp/server.py

## Qué tiene adentro

- Clase `CortexMCPServer` (mixins: `SearchToolsMixin`, `DocumenterToolsMixin`, `SessionToolsMixin`, `WorkspaceToolsMixin`).
- SDK MCP 1.x (`mcp.server.Server`, stdio). `SERVER_VERSION = "2.2"`.
- Cada tool corre en `ThreadPoolExecutor` (`CORTEX_MCP_MAX_WORKERS` default 4) con timeout por tool (default 30s; search_vector 60s, sync_vault 120s, ping 5s, create_spec 60s, documenter_briefing 180s).
- Logs **a archivo** en `layout.logs_dir` (`mcp_calls_*.log`). Stderr solo si `CORTEX_MCP_LOG_TO_STDERR=1` (evita bloquear el pipe JSON-RPC).
- Durante `AgentMemory(...)` redirige stdout→stderr para no contaminar stdio.
- Autopilot: `AutopilotService.from_project_root` + `AutopilotMCPTools`.
- Health: `_startup_time`, `_error_history` (10), ventana 300s para status `degraded`.
- Phase 09.A: `_last_proposal_emitted_at` + gap mínimo 2s entre `cortex_emit_proposal` y `cortex_create_spec` confirmado.

Definiciones de tools (en `mcp/schemas.py`, no en este archivo): `cortex_ping`, `cortex_search_vector`, `cortex_search`, `cortex_context`, `cortex_sync_ticket`, `cortex_create_spec`, `cortex_emit_proposal`, `cortex_save_session`, `cortex_validate_handoff`, `cortex_verify_session_claims`, `cortex_import_hu`, `cortex_get_hu`, `cortex_sync_vault`, tools autopilot (`start/preflight/checkpoint/finish/status`), session (`open/checkpoint/close/status/list`, tasks, `review_checkpoint`), `cortex_finish_session`, `cortex_documenter_briefing`, `cortex_close_session`, `cortex_self_review_note`, `cortex_write_doc`. Comentario en schemas: tools `cortex_delegate_*` fueron retirados.

## Para qué sirve

Motor pasivo MCP: memoria, búsqueda, specs, sesiones y documenter para IDEs. No orquesta subagentes.

## Relaciones

### Recibe de

- `WorkspaceLayout`, `AgentMemory`, `build_tool_definitions`.
- Mixins en `mcp/tools/*`.
- `AutopilotService` / `AutopilotMCPTools`.
- Disco: config, vault, chroma, sessions YAML.

### Envía a

- Cliente MCP por stdio (JSON-RPC).
- Logs en `.cortex/logs/` (layout).
- Mutaciones vía `AgentMemory` / session / documenter / autopilot.
- CLI `cortex mcp-server` (`cli.mcp_cmd`).

### Notas de implementación observadas en el código

- Timeouts nacieron de incidentes citados en comentarios (stdio bloqueado, ONNX frío, npm build en briefing).
- `cortex_ping` es el health check que otros tools (documenter) usan como gate.

---
Fuente: lectura de `cortex/mcp/server.py` + nombres en `mcp/schemas.py`. No se usó documentación previa.
