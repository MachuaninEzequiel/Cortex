# EPIC 2 — Centralizar la Resolución de Paths

**Semaforo:** 🔴 Rojo  
**Dependencias:** EPIC 1 completa  

## Objetivo

Eliminar todos los hardcodes de paths estructurales y reemplazarlos por el resolvedor central. Ningún módulo crítico construye paths sin WorkspaceLayout.

## Gate de Salida

- [ ] Los módulos críticos de lectura usan el resolvedor central
- [ ] No hay dependencia estructural fuerte de `.memory`, `config.yaml` en raíz o `vault` en raíz
- [ ] `AgentMemory.workspace_root` funciona correctamente en ambos layouts
- [ ] DeprecationWarning emitido cuando se usa `project_root`

## Tasks

| # | Task | Descripción | Estado |
|---|------|-------------|--------|
| 1 | Migrar enterprise/knowledge_promotion.py | `PromotionPaths` usa `WorkspaceLayout` para `local_vault`, `enterprise_vault`, `records_path`. `from_project_root()` acepta `workspace_layout`. | ✅ |
| 2 | Migrar enterprise/reporting.py y sources.py | `EnterpriseReportingService` acepta `workspace_layout`. `_local_source` usa `layout.vault_path`. `_enterprise_source` y `_promotion_report` usan `workspace_layout`. `sources.py` no necesitaba cambios. | ✅ |
| 3 | Migrar webgraph/*.py (7 archivos) | `config.py`, `service.py`, `cache.py`, `semantic_source.py`, `episodic_source.py`, `federation.py`, `setup.py`, `cli.py`, `server.py` todos aceptan y usan `workspace_layout`. | ✅ |
| 4 | Migrar semantic/vault_reader.py | `VaultReader` recibe `vault_path` desde callers — no necesita `WorkspaceLayout` directamente. Los callers ya usan `layout.vault_path`. | ✅ |
| 5 | Migrar mcp/server.py | `CortexMCPServer.__init__` usa `WorkspaceLayout.discover()` para `logs_dir`, `config_path`, `subagents_dir`. | ✅ |
| 6 | Migrar ide/__init__.py | `_find_project_root()` usa `WorkspaceLayout.discover()` en vez de búsqueda manual de `.cortex/`. | ✅ |