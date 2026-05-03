# EPIC 3 — Migrar Runtime Crítico

**Semaforo:** 🟡 Amarillo  
**Dependencias:** EPIC 2 completa  

## Objetivo

Hacer que la operación real de Cortex use el nuevo layout correctamente. Todos los flujos de negocio funcionan en layout nuevo.

## Gate de Salida

- [ ] Un proyecto nuevo puede: guardar specs, guardar sesiones, sincronizar vault, recuperar contexto local, cargar config enterprise
- [ ] Un proyecto legacy sigue siendo legible
- [ ] `git log` funciona (usa `repo_root`, no `workspace_root`)
- [ ] Jira integration funciona en layout nuevo
- [ ] Promotion records se escriben en `.cortex/vault-enterprise/promotion/`

## Tasks

| # | Task | Descripción | Estado |
|---|------|-------------|--------|
| 1 | Migrar AgentMemory init | Ya completado en EPIC 1: `self._layout`, `self.workspace_root`, `self.repo_root` agregados. `project_root` = `workspace_root`. | ✅ |
| 2 | Migrar episodic y semantic paths | Ya completado en EPIC 1: `EpisodicMemoryStore` recibe `persist_dir` de `resolve_episodic_persist_dir(workspace_root)`. `VaultReader` recibe `vault_path` de `layout.resolve_workspace_relative()`. | ✅ |
| 3 | Migrar enterprise retrieval | `EnterpriseRetrievalService` acepta `workspace_root`. `resolve_enterprise_vault_path()` y `resolve_enterprise_memory_path()` aceptan `workspace_root`. `core.py` pasa `workspace_root` via layout. | ✅ |
| 4 | Migrar services (spec, session, pr, workitems) | Sin cambios necesarios — los servicios reciben `vault_path` desde `core.py`, ya resuelto via layout. | ✅ |
| 5 | Migrar cold_start y context_enricher | `run_cold_start()` acepta `workspace_layout`. `context_enricher` no tiene paths hardcodeados. `git_policy` tiene templates de `.gitignore` que migra en EPIC 7. | ✅ |
| 6 | Migrar embedder factory | Sin cambios necesarios — `EmbedderFactory` es un registry puro sin paths. | ✅ |