# cortex/autopilot/mcp_tools.py

## Qué tiene adentro

- **Ruta de código:** `cortex/autopilot/mcp_tools.py` (182 líneas).
- **Módulo Python:** `cortex.autopilot.mcp_tools`.
- **Docstring del módulo:** cortex.autopilot.mcp_tools — MCP tool wrappers for Autopilot.
- **Clases definidas:**
  - `AutopilotMCPTools`
    - Thin MCP adapters for the Autopilot lifecycle.
    - Métodos públicos/especiales: `__init__`, `start`, `preflight`, `checkpoint`, `finish`, `status`
    - Métodos internos: `_opt`, `_str_list`, `_parse_mode`
- **Funciones de módulo:**
  - `_format_error(tool_name, exc)`

## Para qué sirve

cortex.autopilot.mcp_tools — MCP tool wrappers for Autopilot.

Phase 03 refactor: every tool delegates to the new :class:`AutopilotService`.
Tool signatures are kept identical to the legacy version so existing MCP
consumers (Claude Code, custom skills) don't observe a breaking change in
the output schema beyond the natural shift from JSONL state files to
``SessionRecord`` shape.

Tools:
    cortex_autopilot_start      — adopt active session.
    cortex_autopilot_preflight  — dry-run the detector pipeline.
    cortex_autopilot_checkpoint — append a checkpoint.
    cortex_autopilot_finish     — close the session (``auto=True`` →
                                  documenter pipeline).
    cortex_autopilot_status     — describe the active session.

T3.5 will polish the human-readable formatting; this module ensures the
tools stay invokable end-to-end after the Phase 03 fusion.

## Relaciones

### Recibe de

- `cortex.autopilot.errors` (AutopilotError, NoActiveSessionError)
- `cortex.autopilot.lifecycle` (AutopilotCheckpointRequest, AutopilotFinishRequest, AutopilotPreflightRequest, AutopilotStartRequest)
- `cortex.autopilot.policies` (AutopilotMode)
- `cortex.autopilot.service` (AutopilotService)
- `cortex.session.errors` (SessionNotFound)
- Dependencias externas/stdlib: `__future__`, `typing`

### Envía a

- `cortex.mcp.server`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 182.

---
Fuente: código de `cortex/autopilot/mcp_tools.py` (AST + grafo de imports internos). No se usó documentación previa.
