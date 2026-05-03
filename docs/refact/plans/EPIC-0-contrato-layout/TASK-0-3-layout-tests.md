# TASK 0-3 — Tests unitarios de WorkspaceLayout

**Epic:** EPIC 0  
**Dependencias:** TASK 0-1, TASK 0-2  
**Rama:** `refac/epic-0-task-3-layout-tests`

## Objetivo

Escribir tests unitarios que verifiquen que `WorkspaceLayout` funciona correctamente en todos los escenarios.

## Archivos a crear

- `tests/unit/workspace/__init__.py`
- `tests/unit/workspace/test_layout.py`

## Escenarios a testear

### Discovery

- [ ] Nuevo layout: `discover()` encuentra `.cortex/workspace.yaml` con `layout_version: 2`
- [ ] Nuevo layout (sin workspace.yaml): `discover()` encuentra `.cortex/config.yaml`
- [ ] Legacy layout: `discover()` encuentra `config.yaml` en raíz y `.cortex/`
- [ ] Legacy layout: `discover()` encuentra `.cortex/` con `.git/`
- [ ] Bootstrap limpio: `discover()` no encuentra nada y retorna layout nuevo
- [ ] Discovery desde subdirectorio: `discover()` sube hasta el repo root
- [ ] Prioridad correcta: si existen ambos layouts, nuevo tiene prioridad

### Paths en nuevo layout

- [ ] `config_path` = `repo_root / ".cortex" / "config.yaml"`
- [ ] `vault_path` = `repo_root / ".cortex" / "vault"`
- [ ] `enterprise_vault_path` = `repo_root / ".cortex" / "vault-enterprise"`
- [ ] `episodic_memory_path` = `repo_root / ".cortex" / "memory"`
- [ ] `enterprise_memory_path` = `repo_root / ".cortex" / "enterprise-memory"`
- [ ] `org_config_path` = `repo_root / ".cortex" / "org.yaml"`
- [ ] `skills_dir` = `repo_root / ".cortex" / "skills"`
- [ ] `subagents_dir` = `repo_root / ".cortex" / "subagents"`
- [ ] `webgraph_dir` = `repo_root / ".cortex" / "webgraph"`
- [ ] `workflows_dir` = `repo_root / ".github" / "workflows"` (fuera de .cortex)
- [ ] `promotion_records_path` = `repo_root / ".cortex" / "vault-enterprise" / "promotion" / "records.jsonl"`
- [ ] `vault_index_path` = `repo_root / ".cortex" / "vault" / ".cortex_index.json"`

### Paths en legacy layout

- [ ] `legacy_config_path` = `repo_root / "config.yaml"`
- [ ] `legacy_vault_path` = `repo_root / "vault"`
- [ ] `legacy_memory_path` = `repo_root / ".memory"`
- [ ] En legacy layout, `workspace_root = repo_root`
- [ ] En legacy layout, los paths apuntan a las ubicaciones legacy

### resolve_workspace_relative

- [ ] `resolve_workspace_relative("vault")` = `workspace_root / "vault"`
- [ ] En nuevo layout: `workspace_root / "vault"` = `repo_root / ".cortex" / "vault"`
- [ ] En legacy layout: `workspace_root / "vault"` = `repo_root / "vault"`

### Workspace YAML parsing

- [ ] Parsea `layout_version` correctamente
- [ ] `layout_version: 1` → legacy
- [ ] `layout_version: 2` → nuevo
- [ ] Ausencia de `layout_version` → legacy

## Checklist

- [ ] Todos los escenarios de discovery pasan
- [ ] Todos los paths en nuevo layout son correctos
- [ ] Todos los paths en legacy layout son correctos
- [ ] `resolve_workspace_relative` funciona en ambos layouts
- [ ] Tests corren con `pytest tests/unit/workspace/`