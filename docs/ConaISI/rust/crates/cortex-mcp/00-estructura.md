# Estructura interna — `rust/crates/cortex-mcp`

Servidor MCP nativo (rmcp, stdio). Catálogo congelado de **32 tools**, versión de servidor `"2.2"`. Dispatcher + backends nativos inyectables.

Dependencias: `rmcp`, `serde`, `serde_json` (preserve_order), `tokio`, `cortex-setup`, `cortex-app`, `cortex-workspace`, `cortex-services`, `cortex-autopilot`, `cortex-embed`, `serde_yaml`, `chrono`, `regex`.

```
cortex-mcp/
├── Cargo.toml
├── examples/
│   ├── cierre_check.rs
│   └── p12a9_check.rs
├── src/
│   ├── lib.rs
│   ├── tools_catalog.rs
│   ├── server.rs
│   ├── pyjson.rs
│   ├── handlers_sessions.rs
│   ├── handlers_search.rs
│   ├── handlers_docs.rs
│   ├── handlers_spec.rs
│   ├── handlers_finish.rs
│   ├── handlers_autopilot.rs
│   └── backends/
│       ├── mod.rs
│       ├── sessions.rs
│       ├── search.rs
│       ├── spec.rs
│       ├── finish.rs
│       ├── docs.rs
│       └── autopilot.rs
└── tests/
    └── mcp_golden_contract.rs
```

## Las 32 tools (orden de `build_tool_definitions`)

1. `cortex_ping`
2. `cortex_search_vector`
3. `cortex_search`
4. `cortex_context`
5. `cortex_sync_ticket`
6. `cortex_create_spec`
7. `cortex_emit_proposal`
8. `cortex_save_session`
9. `cortex_validate_handoff`
10. `cortex_verify_session_claims`
11. `cortex_import_hu`
12. `cortex_get_hu`
13. `cortex_sync_vault` — **ruta inline** (no está en `tool_routes()`)
14. `cortex_autopilot_start`
15. `cortex_autopilot_preflight`
16. `cortex_autopilot_checkpoint`
17. `cortex_autopilot_finish`
18. `cortex_autopilot_status`
19. `cortex_session_open`
20. `cortex_session_checkpoint`
21. `cortex_session_close`
22. `cortex_session_status`
23. `cortex_finish_session`
24. `cortex_documenter_briefing`
25. `cortex_close_session`
26. `cortex_session_list`
27. `cortex_self_review_note`
28. `cortex_write_doc`
29. `write_design_note_canonical`
30. `cortex_session_task_list`
31. `cortex_session_task_update`
32. `cortex_review_checkpoint`

`cortex_sync_vault` cuenta como tool del catálogo; el dispatcher la resuelve contra `MemoryBackend::sync_vault`.

## Arranque de producción

`cortex-cli mcp-server --stdio` construye `CortexMcpServer`, inyecta todos los `Native*Backend` y llama `serve_stdio_blocking`. Search puede quedar `None` si no hay config (fallo explícito documentado).
