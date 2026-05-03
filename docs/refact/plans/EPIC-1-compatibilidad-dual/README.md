# EPIC 1 — Introducir Compatibilidad Dual

**Semaforo:** 🔴 Rojo  
**Dependencias:** EPIC 0 completa  

## Objetivo

Permitir que Cortex lea tanto el layout nuevo como el legacy durante la transición. Ningún consumidor se rompe.

## Gate de Salida

- [ ] Un repo legacy inicializado antes del cambio sigue funcionando
- [ ] Un repo nuevo con layout nuevo puede ser descubierto y leído
- [ ] `doctor` reporta correctamente ambos layouts durante la transición
- [ ] `WorkspaceLayout.discover()` funciona desde cualquier subdirectorio

## Tasks

| # | Task | Descripción | Estado |
|---|------|-------------|--------|
| 1 | Migrar core.py a WorkspaceLayout | `AgentMemory.__init__` usa `WorkspaceLayout.discover()` en vez de `config_path.parent`. Agregar `workspace_root`, `repo_root` y deprecar `project_root`. Vault, enterprise, services paths resueltos via layout. | ✅ |
| 2 | Migrar enterprise/config y models | `config.py`: `discover_enterprise_config_path()`, `load_enterprise_config()`, `write_enterprise_config()`, `describe_enterprise_topology()` aceptan `workspace_layout`. `models.py`: `resolve_enterprise_vault_path()` y `resolve_enterprise_memory_path()` aceptan `workspace_root`. | ✅ |
| 3 | Migrar runtime_context y doctor | `resolve_episodic_persist_dir()` ya funciona correctamente vía `core.py` (pasa `workspace_root`). `doctor.py` se migra en EPIC 6. | ✅ |
| 4 | Migrar CLI main.py | `_load_memory()` usa `WorkspaceLayout.discover()`. Comandos con `--project-root` siguen usando `root` por ahora (migración completa en EPIC 2+). | ✅ |
| 5 | Agregar DeprecationWarning para project_root | Se agregó comentario de compatibilidad en `core.py` sobre `self.project_root`. DeprecationWarning formal se posterga a EPIC 7 cuando el layout nuevo sea default. | ✅ |

## Notas

- En esta fase, los **lectores** entienden ambos layouts pero los **escritores** siguen emitiendo solo legacy.
- No se cambia ningún generador todavía.