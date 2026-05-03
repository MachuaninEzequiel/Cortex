# EPIC 5 — Migrar IDE, MCP y WebGraph

**Semaforo:** 🟡 Amarillo  
**Dependencias:** EPIC 4 completa  
**Estado:** ✅ Completada

## Objetivo

Alinear los consumidores externos y de integración con el nuevo modelo de workspace.

## Gate de Salida

- [x] Cursor descubre proyecto via WorkspaceLayout
- [x] VSCode/Cline descubre proyecto via WorkspaceLayout
- [x] MCP arranca y encuentra config, subagentes y logs en `.cortex/`
- [x] WebGraph serve/export/doctor funcionan en layout nuevo

## Tasks

| # | Task | Descripción | Estado |
|---|------|-------------|--------|
| 1 | Migrar ide/__init__.py y registry.py | `_find_project_root()` delega en `WorkspaceLayout.discover()`. Todos los adapters reciben `workspace_root`. | ✅ |
| 2 | Migrar ide/adapters/*.py y prompts.py | Cada adapter recibe `workspace_root` vía `build_all_prompts()` y `build_cursor_prompts()`. Prompts referencian skills y subagents via `WorkspaceLayout`. | ✅ |
| 3 | Migrar mcp/server.py | Constructor ya usa `WorkspaceLayout` para config_path, logs_dir, subagents_dir. Sin cambios necesarios. | ✅ |
| 4 | Migrar webgraph/*.py | Todos los módulos ya usan `WorkspaceLayout` (config, service, cli, setup, cache, federation, semantic_source, episodic_source, server). Sin cambios necesarios. | ✅ |
| 5 | Smoke tests de integración | Tests unitarios de IDE adapters, prompts y webgraph pasan con layout-aware paths. | ✅ |