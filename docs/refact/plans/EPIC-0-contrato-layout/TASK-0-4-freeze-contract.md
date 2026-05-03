# TASK 0-4 — Congelar documento y verificar contrato

**Epic:** EPIC 0  
**Dependencias:** TASK 0-1, TASK 0-2, TASK 0-3  
**Rama:** `refac/epic-0-task-4-freeze-contract`

## Objetivo

Verificar que la API de `WorkspaceLayout` está completa, es consistente con el documento REFAC, y congelar el contrato.

## Verificaciones

### Contrato vs Implementación

- [ ] Todas las propiedades del contrato (Sección 7 del REFAC) están implementadas
- [ ] `discover()` implementa la precedencia definida
- [ ] `from_repo_root()` funciona
- [ ] `resolve_workspace_relative()` funciona
- [ ] `legacy_*` paths funcionan
- [ ] No hay contradicciones entre el documento y la implementación

### Contrato vs Código existente

Verificar que cada consumidor actual tiene un path correspondiente en `WorkspaceLayout`:

| Consumidor actual | Path buscado | Propiedad en WorkspaceLayout |
|---|---|---|
| `core.py` | `config_path.parent` | `workspace_root` |
| `enterprise/config.py` | `.cortex/org.yaml` | `org_config_path` |
| `enterprise/models.py` | `project_root / "vault-enterprise"` | `enterprise_vault_path` |
| `enterprise/models.py` | `project_root / ".memory/enterprise/chroma"` | `enterprise_memory_path` |
| `webgraph/config.py` | `.cortex/webgraph/config.yaml` | `webgraph_config_path` |
| `ide/__init__.py` | `.cortex/` existence | `workspace_root.exists()` |
| `mcp/server.py` | `.cortex/logs/` | `logs_dir` |
| `mcp/server.py` | `.cortex/subagents/` | `subagents_dir` |
| `doctor.py` | `config.yaml`, `.cortex/`, `vault/` | `config_path`, `workspace_root`, `vault_path` |
| `knowledge_promotion.py` | `enterprise_vault / ".cortex" / "promotion"` | `promotion_records_path` |
| `setup/orchestrator.py` | `.memory/`, `vault/`, `scripts/` | `episodic_memory_path`, `vault_path`, `scripts_dir` |
| `tutor/hint.py` | `config.yaml`, `.cortex/` | `config_path`, `workspace_root` |
| `cold_start.py` | git log en `project_root` | `repo_root` |
| `vault_reader.py` | `.cortex_index.json` | `vault_index_path` |

- [ ] Todas las propiedades están cubiertas
- [ ] No hay paths huérfanos que WorkspaceLayout no resuelva

### Verificación de layout

- [ ] No se produce `.cortex/.cortex/` en ningún path
- [ ] No se produce `cortex/cortex/` en ningún path
- [ ] `.github/workflows/` está fuera de `.cortex/`
- [ ] Todos los paths dentro de `.cortex/` son accesibles (no hay subdirectorios ocultos)
- [ ] Promotion records van a `.cortex/vault-enterprise/promotion/` (sin `.cortex` intermedio)

## Checklist

- [ ] Contrato verificado contra implementación
- [ ] Contrato verificado contra código existente
- [ ] Layout verificado sin anidación duplicada
- [ ] Documento REFAC actualizado si hubo cambios durante la implementación
- [ ] Gate de salida de EPIC 0 marcado como ✅