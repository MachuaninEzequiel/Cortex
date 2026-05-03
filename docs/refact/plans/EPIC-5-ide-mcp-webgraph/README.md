# EPIC 5 — Migrar IDE, MCP y WebGraph

**Semaforo:** 🟡 Amarillo  
**Dependencias:** EPIC 4 completa  

## Objetivo

Alinear los consumidores externos y de integración con el nuevo modelo de workspace.

## Gate de Salida

- [ ] Cursor descubre proyecto via WorkspaceLayout
- [ ] VSCode/Cline descubre proyecto via WorkspaceLayout
- [ ] MCP arranca y encuentra config, subagentes y logs en `.cortex/`
- [ ] WebGraph serve/export/doctor funcionan en layout nuevo

## Tasks

| # | Task | Descripción | Estado |
|---|------|-------------|--------|
| 1 | Migrar ide/__init__.py y registry.py | `_find_project_root()` delega en `WorkspaceLayout.discover()`. Todos los adapters reciben `workspace_root`. | ⬜ |
| 2 | Migrar ide/adapters/*.py y prompts.py | Cada adapter recibe `workspace_root` vía `build_all_prompts()` y `build_cursor_prompts()`. Prompts referencian `.cortex/skills/` y `.cortex/subagents/`. | ⬜ |
| 3 | Migrar mcp/server.py | Constructor recibe `project_root` → deriva `repo_root` → `WorkspaceLayout.from_repo_root()`. config_path, logs_dir, subagents_dir via layout. | ⬜ |
| 4 | Migrar webgraph/*.py | service.py, config.py, cli.py, setup.py, cache.py, federation.py, semantic_source.py, episodic_source.py, server.py — todos usan WorkspaceLayout. WebGraph no cambia de ubicación (.cortex/webgraph/) pero sí cómo resuelve paths. | ⬜ |
| 5 | Smoke tests de integración | Probar manualmente: Cursor, VSCode, MCP delegation, WebGraph serve. Mínimo 1 smoke test por integración. | ⬜ |