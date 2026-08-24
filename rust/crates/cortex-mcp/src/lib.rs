//! cortex-mcp — Obra 07 P9 (stream B)
//!
//! Servidor MCP nativo con rmcp exponiendo los tools canónicos de Cortex.
//!
//! - [`tools_catalog`]: las 32 definiciones de `list_tools` (porteo de
//!   `cortex/mcp/schemas.py`), contrato congelado por
//!   `tests/unit/mcp/golden/list_tools.json`.
//! - [`server`]: dispatcher con la tabla `_TOOL_ROUTES` espejo, ruta inline
//!   `cortex_sync_vault`, mensaje estable de herramienta desconocida y
//!   `cortex_ping` completo (estado starting/degraded/ok + ventana de
//!   errores). El transporte stdio rmcp vive en [`server::serve_stdio`].
//!
//! Paridad: los tools que dependen de backends aún no nativos devuelven
//! fallo explícito documentado (patrón P6) — no se finge paridad
//! conductual; el gate de P9 es el contrato list_tools byte-a-byte +
//! dispatch de ping.

pub mod server;
pub mod tools_catalog;
