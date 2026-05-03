# EPIC 4 — Migrar Setup y Generadores

**Semaforo:** 🟡 Amarillo  
**Dependencias:** EPIC 3 completa  

## Objetivo

Hacer que el bootstrap escriba exclusivamente el layout nuevo dentro de `.cortex/`.

## Gate de Salida

- [ ] Un repo inicializado desde cero genera exclusivamente el layout nuevo
- [ ] `.github/workflows/` se crea en raíz (no dentro de `.cortex/`)
- [ ] `workspace.yaml` tiene `layout_version: 2`
- [ ] Jira integration escribe en `.cortex/vault/hu/`

## Tasks

| # | Task | Descripción | Estado |
|---|------|-------------|--------|
| 1 | Migrar setup/orchestrator.py | `_create_directories()`, `_create_config()`, `_create_vault_docs()`, `_create_enterprise_vault()`, `_create_workflows()`, `_create_devsecdocops_script()`, `_create_agent_guidelines()` todos escriben dentro de `.cortex/`. Workflows siguen en `.github/`. | ⬜ |
| 2 | Migrar setup/templates.py | `render_config_yaml()` genera paths relativos a workspace (`persist_dir: memory`, `vault_path: vault`). Workflows usan autodiscovery o `.cortex/vault`. | ⬜ |
| 3 | Migrar setup/cortex_workspace.py | `ensure_cortex_workspace()` escribe en `.cortex/` (ya es así). Agregar `workspace.yaml` con `layout_version: 2`. | ⬜ |
| 4 | Migrar setup/cold_start.py y detector.py | `run_cold_start()` usa `repo_root` para git, `workspace_root` para escribir vault index. `ProjectDetector` usa WorkspaceLayout. | ⬜ |
| 5 | Migrar setup/enterprise_*.py | `write_enterprise_config()` escribe en `layout.org_config_path`. Presets usan paths relativos al workspace. | ⬜ |