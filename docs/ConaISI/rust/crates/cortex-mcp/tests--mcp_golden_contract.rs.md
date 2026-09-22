# rust/crates/cortex-mcp/tests/mcp_golden_contract.rs

## Qué tiene adentro

Gate P9: compara `list_tools` vs `tests/unit/mcp/golden/list_tools.json`; tabla `_TOOL_ROUTES` vs ROUTING_ESPERADO; mensaje herramienta desconocida; sync_vault stub; ping vs golden normalizando `{{UPTIME}}`.

## Para qué sirve

Congelar el contrato MCP observable.

## Relaciones

### Recibe de

- Goldens en el monorepo.
- `build_tool_definitions`, `tool_routes`, `CortexMcpServer`.

### Envía a

- cargo test.

### Notas de implementación observadas en el código

Serialización indent=2 ensure_ascii=False + `\n` final.
