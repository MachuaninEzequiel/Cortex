# Fase 5 — MCP Tools Autopilot: Realización

## Fecha
2026-05-09

## Resumen
Se implementó la exposición de Autopilot vía MCP tools, registrando 5 herramientas (`cortex_autopilot_start`, `cortex_autopilot_preflight`, `cortex_autopilot_checkpoint`, `cortex_autopilot_finish`, `cortex_autopilot_status`) en el `CortexMCPServer` existente. Toda la lógica de negocio se delega a `AutopilotService`; no se duplicó ninguna lógica dentro del MCP server.

## Archivos creados
1. `cortex/autopilot/mcp_tools.py` — adaptadores MCP delgados que envuelven `AutopilotService`.
2. `tests/unit/autopilot/test_mcp_tools.py` — 14 tests unitarios cubriendo los 5 tools + helpers de errores.

## Archivos modificados
1. `cortex/mcp/server.py` — primera y única fase autorizada para tocar este archivo.
   - Se importa `AutopilotMCPTools` y `AutopilotService`.
   - Se inicializa `self._autopilot_service` y `self._autopilot_tools` en `__init__`.
   - Se agregan las 5 `types.Tool` al listado de `handle_list_tools()`.
   - Se agregan los 5 `elif` handlers en `handle_call_tool()` que delegan a `self._autopilot_tools`.

## Diseño clave
- **No duplicación de lógica**: cada método de `AutopilotMCPTools` valida argumentos requeridos (`_req`, `_opt`, `_str_list`) y delega inmediatamente a `AutopilotService`.
- **Manejo de errores robusto**: todos los métodos capturan excepciones (incluyendo `ValueError` por argumentos faltantes y `SessionNotFoundError`) y retornan strings de error amigables para el consumidor MCP, sin propagar excepciones crudas.
- **Coexistencia**: las nuevas tools no interfieren con las existentes (`cortex_search`, `cortex_context`, `cortex_sync_ticket`, etc.).
- **Sin paths hardcodeados**: `AutopilotService.from_project_root(project_root)` usa `WorkspaceLayout` internamente.

## Tests
- `pytest tests/unit/autopilot/test_mcp_tools.py` — 14/14 passed.
- Suite completa Autopilot — 147/147 passed (sin regresiones).

## Incidentes y resoluciones
**Ninguno.** La integración fue directa porque `AutopilotService` ya exponía la interfaz completa de lifecycle (start, preflight, checkpoint, finish, status) con manejo de estado, detectores, políticas y renderers. Solo fue necesario crear la capa de adaptación MCP.
