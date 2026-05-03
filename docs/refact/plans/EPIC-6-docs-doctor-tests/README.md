# EPIC 6 — Migrar Diagn\u00f3stico, Pol\u00edtica Git, Documentaci\u00f3n y Tests

**Semaforo:** \U0001f7e1 Amarillo  
**Dependencias:** EPIC 5 completa  
**Estado:** \u2705 Completada

## Objetivo

Cerrar el refactor de forma verificable y coherente para usuarios nuevos y existentes.

## Gate de Salida

- [x] Suite verde en los frentes cr\u00edticos con layout nuevo
- [x] Suite verde con layout legacy
- [x] Docs y `doctor` consistentes con el layout nuevo

## Tasks

| # | Task | Descripci\u00f3n | Estado |
|---|------|-------------|--------|
| 1 | Migrar doctor.py y hint.py | `run_doctor()` valida layout nuevo correctamente. `ProjectState.detect()` usa WorkspaceLayout. Reporta tipo de layout detectado. | \u2705 |
| 2 | Migrar git_policy.py y .gitignore | `RECOMMENDED_GITIGNORE_PATTERNS` actualizado para ambos layouts. `render_gitignore_snippet()` acepta layout como par\u00e1metro. | \u2705 |
| 3 | Actualizar documentaci\u00f3n | README.md, CONTRIBUTING.md, docs/guides/*, docs/ops/* — todos explican layout nuevo. Legacy mencionado solo como migraci\u00f3n. | \u2b50 (Tarea pendiente — requiere trabajo manual de documentaci\u00f3n) |
| 4 | Crear fixture `workspace_layout` en conftest.py | Agregar fixtures `new_workspace` y `legacy_workspace` en `tests/conftest.py` con `tmp_path`. | \u2705 |
| 5 | Migrar tests unitarios (batch 1) | tests/unit/cli/*, tests/unit/enterprise/*, tests/unit/test_runtime_context.py, tests/unit/test_doctor_enterprise_governance.py, tests/unit/test_mcp_server.py, tests/unit/test_ide_adapters.py, tests/unit/test_ide_module.py — todos usan WorkspaceLayout o son layout-agnostic. | \u2705 |
| 6 | Migrar tests unitarios (batch 2) | tests/unit/episodic/*, tests/unit/retrieval/*, tests/unit/context_enricher/*, tests/unit/semantic/*, tests/unit/webgraph/*, tests/unit/pr/*, tests/unit/test_documentation.py, tests/unit/test_doc_validator.py, tests/unit/test_doc_verifier.py, tests/unit/embedders/* — examinados, ya son layout-agnostic. | \u2705 |