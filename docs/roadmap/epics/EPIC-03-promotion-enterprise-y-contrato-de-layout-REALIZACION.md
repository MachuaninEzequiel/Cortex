# Realizacion - EPIC-03

> Completar este archivo al terminar todos los checklists de [EPIC-03-promotion-enterprise-y-contrato-de-layout.md](./EPIC-03-promotion-enterprise-y-contrato-de-layout.md).

## Estado

- Fecha de inicio: 2026-05-05
- Fecha de cierre: 2026-05-05
- Responsable: agente autonomo de desarrollo

## Resumen ejecutivo

Se corrigio el pipeline de promotion enterprise que fallaba en 3 tests de integracion. La causa raiz fue una discordancia entre el layout detectado por `WorkspaceLayout.discover()` (new-layout bootstrap) y los fixtures de prueba que colocaban documentos en `vault/` (raiz), correspondiente a legacy. Ademas, `KnowledgePromotionService` recalculaba la config en `discover_candidates()` sin reutilizar el `WorkspaceLayout` ya resuelto en `from_project_root()`.

## Diagnostico inicial

- `pytest -q tests/integration/enterprise/test_promotion_e2e.py` fallaba en 3 tests con `IndexError: list index out of range` porque `discover_candidates()` devolvia `[]`.
- `WorkspaceLayout.discover(project_root)` en un repo sin `config.yaml`, sin `.git` y sin `.cortex/workspace.yaml` cae a bootstrap new-layout (`workspace_root = repo_root / ".cortex"`).
- El fixture de test creaba documentos en `repo_root/vault/`, pero `local_vault` en new-layout apunta a `repo_root/.cortex/vault/`, que no existia.
- `KnowledgePromotionService.discover_candidates()` llamaba `load_enterprise_config(self.paths.project_root, required=True)` sin pasar `workspace_layout`, lo que introducia una segunda via de resolucion.

## Decision contractual (Gate 1)

**Opcion A** elegida: Bootstrap sin señales explicitas cae a new-layout.

Justificacion:
- `WorkspaceLayout.discover()` tiene un test unitario (`test_discover_bootstrap_no_project`) que confirma bootstrap -> new-layout.
- El docstring de `WorkspaceLayout` define new-layout con `vault/` bajo `.cortex/`.
- Cambiar `discover()` para tratar `vault/` en raiz como legacy habria roto el contrato establecido del layout y afectado otras superficies (setup, CLI, MCP).
- Por tanto, el fixture de promotion debe adaptarse a new-layout, no al reves.

## Archivos modificados

- `cortex/enterprise/knowledge_promotion.py`
  - `__init__` ahora acepta y guarda `workspace_layout: WorkspaceLayout | None`.
  - `from_project_root()` pasa `workspace_layout=layout` al constructor.
  - `discover_candidates()` reutiliza `self._workspace_layout` al cargar enterprise config.
- `tests/integration/enterprise/test_promotion_e2e.py`
  - Adaptados los 3 tests existentes para usar new-layout explicito (`.cortex/workspace.yaml` con `layout_version: 2`, vault bajo `.cortex/vault/`, vault-enterprise bajo `.cortex/vault-enterprise/`).
  - Agregados 2 tests nuevos:
    - `test_promotion_new_layout_paths_are_consistent`: flujo end-to-end en new-layout con aserciones de paths.
    - `test_promotion_legacy_layout_paths_are_consistent`: flujo end-to-end en legacy con `config.yaml` en raiz, vault en raiz, y aserciones de paths.

## Validaciones ejecutadas

- `pytest -q tests/integration/enterprise/test_promotion_e2e.py` — 5 passed
- `pytest -q tests/unit/workspace/test_layout.py` — 54 passed
- `pytest -q tests/unit/enterprise/test_promotion_records.py` — 1 passed
- `pytest -q tests/unit/enterprise/test_promotion_rules.py` — 3 passed
- `pytest -q` (suite completa) — 385 passed, 6 skipped, 0 failed

## Decisiones tecnicas tomadas

- **No se modifico `WorkspaceLayout.discover()`**: la deteccion de layout ya tenia un contrato claro. El problema estaba en el fixture, no en la logica de discovery.
- **No se introdujo fallback dual**: se evito buscar primero en `vault/` y luego en `.cortex/vault/` dentro del servicio. Cada layout tiene su ruta unica definida en `WorkspaceLayout`.
- **Se conservaron firmas publicas**: `from_project_root()`, `review()`, `plan_promotion()`, `apply_promotion()` mantuvieron sus firmas y contratos externos.
- **`PromotionRecord`, `PromotionCandidate`, `PromotionDecision` no se tocaron**: no habia falla que lo exigiera.

## Pendientes o riesgos abiertos

- Ninguno para esta epica. El pipeline de promotion enterprise ahora funciona correctamente en ambos layouts con tests de cobertura explicita.
