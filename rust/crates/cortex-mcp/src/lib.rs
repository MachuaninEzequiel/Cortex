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
//! - [`handlers_sessions`]: handlers in-process de la familia sesiones
//!   (P12A-9, stream A) sobre un backend inyectable nativo.
//!
//! - [`handlers_search`]/[`handlers_docs`]/[`handlers_spec`]/
//!   [`handlers_finish`]: handlers in-process de las familias no-sesión
//!   (Cierre Obra 07 T1) sobre backends inyectables por familia.
//!
//! Paridad: los tools que dependen de backends aún no nativos devuelven
//! fallo explícito documentado (patrón P6) — no se finge paridad
//! conductual; el gate de P9 es el contrato list_tools byte-a-byte +
//! dispatch de ping.

pub mod backends;
pub mod handlers_autopilot;
pub mod handlers_docs;
pub mod handlers_finish;
pub mod handlers_search;
pub mod handlers_sessions;
pub mod handlers_spec;
pub mod pyjson;
pub mod server;
pub mod tools_catalog;
