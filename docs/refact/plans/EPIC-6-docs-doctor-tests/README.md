# EPIC 6 — Migrar Diagnóstico, Política Git, Documentación y Tests

**Semaforo:** 🟡 Amarillo  
**Dependencias:** EPIC 5 completa  

## Objetivo

Cerrar el refactor de forma verificable y coherente para usuarios nuevos y existentes.

## Gate de Salida

- [ ] Suite verde en los frentes críticos con layout nuevo
- [ ] Suite verde con layout legacy
- [ ] Docs y `doctor` consistentes con el layout nuevo

## Tasks

| # | Task | Descripción | Estado |
|---|------|-------------|--------|
| 1 | Migrar doctor.py y hint.py | `run_doctor()` valida layout nuevo correctamente. `ProjectState.detect()` usa WorkspaceLayout. Reporta tipo de layout detectado. | ⬜ |
| 2 | Migrar git_policy.py y .gitignore | `RECOMMENDED_GITIGNORE_PATTERNS` actualizado para ambos layouts. Generar `.gitignore` con compatibilidad dual. | ⬜ |
| 3 | Actualizar documentación | README.md, CONTRIBUTING.md, docs/guides/*, docs/ops/* — todos explican layout nuevo. Legacy mencionado solo como migración. | ⬜ |
| 4 | Crear fixture `workspace_layout` en conftest.py | Agregar fixtures `workspace_layout` y `legacy_workspace` en `tests/conftest.py` con `tmp_path`. | ⬜ |
| 5 | Migrar tests unitarios (batch 1) | tests/unit/cli/*, tests/unit/enterprise/*, tests/unit/test_runtime_context.py, tests/unit/test_doctor_enterprise_governance.py, tests/unit/test_mcp_server.py, tests/unit/test_ide_adapters.py, tests/unit/test_ide_module.py | ⬜ |
| 6 | Migrar tests unitarios (batch 2) | tests/unit/episodic/*, tests/unit/retrieval/*, tests/unit/context_enricher/*, tests/unit/semantic/*, tests/unit/webgraph/*, tests/unit/pr/*, tests/unit/test_documentation.py, tests/unit/test_doc_validator.py, tests/unit/test_doc_verifier.py, tests/unit/embedders/* | ⬜ |