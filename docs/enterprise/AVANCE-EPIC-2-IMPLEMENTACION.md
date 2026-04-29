# Avance EPIC 2: Retrieval Multi-Nivel

## Documento

- Fecha inicio: 2026-04-29
- Estado: En progreso
- Epic: `E2 - Retrieval multi-nivel`
- Base: `EPIC 1 completada`

---

## Objetivo de este documento

Registrar de forma incremental cada decision, implementacion y validacion realizada durante la EPIC 2.

---

## Bitacora de implementacion

### 2026-04-29 - Preparacion y alineacion tecnica

- Se relevo en detalle el backlog enterprise y el plan especifico de EPIC 2.
- Se validaron dependencias y estado previo de EPIC 1.
- Se inspeccionaron modulos actuales de retrieval:
  - `cortex/models.py`
  - `cortex/retrieval/hybrid_search.py`
  - `cortex/semantic/vault_reader.py`
  - `cortex/episodic/memory_store.py`
  - `cortex/core.py`
  - `cortex/cli/main.py`
  - `cortex/enterprise/config.py`
  - `cortex/enterprise/models.py`
- Decision de arquitectura para primer corte:
  - Mantener `HybridSearch` local intacto.
  - Agregar capa enterprise separada:
    - `cortex/enterprise/sources.py`
    - `cortex/enterprise/retrieval_service.py`
  - Integrar por delegacion desde `AgentMemory.retrieve(scope=...)`.

### 2026-04-29 - Primer corte de implementacion (en curso)

- Alcance del corte:
  - Scopes operativos: `local`, `enterprise`, `all`.
  - Metadata de origen en hits.
  - Servicio enterprise de retrieval multi-fuente.
  - Soporte CLI inicial con `cortex search --scope`.

### 2026-04-29 - Implementacion realizada

- Se extendieron modelos de retrieval con metadata de origen:
  - `SemanticDocument`: `origin_scope`, `origin_project_id`, `origin_vault`, `origin_persist_dir`
  - `EpisodicHit`: `origin_scope`, `origin_project_id`, `origin_vault`, `origin_persist_dir`
  - `UnifiedHit`: campo `metadata` tipado.
- Se implemento `cortex/enterprise/sources.py` con:
  - `VaultSource`, `EpisodicSource`
  - `MultiVaultReader`
  - `MultiEpisodicReader`
- Se implemento `cortex/enterprise/retrieval_service.py` con:
  - `EnterpriseRetrievalService`
  - fusion multi-fuente por RRF con pesos por scope.
- Se integro `scope` en `AgentMemory.retrieve(...)`:
  - `local`: flujo actual (`HybridSearch`)
  - `enterprise|all`: delegacion a `EnterpriseRetrievalService`
  - manejo de error claro cuando no existe `.cortex/org.yaml`.
- Se integro `--scope` en CLI `cortex search`.
- Se agregaron tests iniciales:
  - `tests/unit/enterprise/test_retrieval_service.py`
  - extensiones en `tests/unit/cli/test_main.py`

### 2026-04-29 - Segundo corte (completado)

- Se agregaron pesos configurables por scope en `org.yaml`:
  - `memory.retrieval_local_weight`
  - `memory.retrieval_enterprise_weight`
- Se cablearon dichos pesos al servicio enterprise desde `AgentMemory`.
- Se incorporo `source_breakdown` en `RetrievalResult` para observabilidad de origen.
- Se implemento `--show-scores` en `cortex search` para mostrar metadata de scope por hit.
- Se ampliaron tests para validar:
  - defaults de pesos enterprise
  - breakdown por scope en resultados
  - salida CLI con `--show-scores`

### 2026-04-29 - Tercer corte (iniciado)

- Se agregaron tests unitarios de integracion en `AgentMemory.retrieve(scope=...)` para:
  - garantizar error controlado cuando se pide `enterprise` sin `org.yaml`
  - garantizar que `local` mantiene delegacion al `HybridSearch` existente

### 2026-04-29 - Validacion de cortes 2 y 3

- Suite ejecutada y passing:
  - `tests/unit/enterprise/test_config.py`
  - `tests/unit/enterprise/test_retrieval_service.py`
  - `tests/unit/enterprise/test_core_retrieve_scope.py`
  - `tests/unit/cli/test_main.py`
- Resultado: `19 passed`
- Lint de archivos tocados: sin errores.

### 2026-04-29 - Ajuste de comportamiento (scope default)

- Se corrigio CLI `search` para que `--scope` sea opcional real.
- Si no se pasa `--scope`, ahora se delega `scope=None` y `AgentMemory` aplica el default de `org.yaml` (`retrieval_default_scope`).
- Se agregaron tests para:
  - validar que CLI pasa `None` cuando no hay override
  - validar que runtime aplica `retrieval_default_scope` cuando existe org config.

### 2026-04-29 - Siguiente tramo (filtros + deduplicacion)

- Se agrego filtro opcional por proyecto en retrieval:
  - API runtime: `AgentMemory.retrieve(..., project_id=...)`
  - Servicio enterprise: `EnterpriseRetrievalService.search(..., project_id=...)`
  - CLI: `cortex search --project-id <id>`
- Se implemento deduplicacion cross-source en fusion unificada:
  - semantic: merge por clave canonica de path/titulo
  - episodic: merge por firma de contenido normalizado
- Regla de resolucion cuando hay duplicado local/enterprise:
  - se prioriza representante enterprise para metadata de salida.
- Tests agregados:
  - filtro por `project_id` en retrieval enterprise
  - deduplicacion de hits semantic duplicados
  - forwarding de `--project-id` desde CLI

### 2026-04-29 - Validacion de este tramo

- Suite ejecutada y passing:
  - `tests/unit/enterprise/test_retrieval_service.py`
  - `tests/unit/enterprise/test_core_retrieve_scope.py`
  - `tests/unit/cli/test_main.py`
- Resultado: `20 passed`

### 2026-04-29 - Cierre de pendientes EPIC 2

- Se resolvieron paths enterprise contra `project_root` para evitar ambiguedad de rutas relativas.
- Se agrego validacion explicita para `scope=enterprise` sin fuentes enterprise habilitadas.
- Se completo cobertura de `sources`:
  - `MultiVaultReader` (1 y 3 fuentes)
  - `MultiEpisodicReader` (2 fuentes)
- Se agregaron tests de integracion/E2E de CLI para:
  - `--scope local`
  - `--scope enterprise`
  - `--scope all`
  - error claro cuando falta `org.yaml` para enterprise scope.
- Se agrego smoke test de performance para retrieval enterprise multi-fuente.
- Se actualizo backlog y plan de EPIC 2 con checks de completitud.
- Suite final EPIC 2 ejecutada:
  - `tests/unit/enterprise/test_sources.py`
  - `tests/unit/enterprise/test_retrieval_service.py`
  - `tests/unit/enterprise/test_retrieval_performance.py`
  - `tests/unit/enterprise/test_core_retrieve_scope.py`
  - `tests/unit/cli/test_main.py`
  - `tests/integration/enterprise/test_retrieval_e2e.py`
  - Resultado: `29 passed`

---

## Checklist EPIC 2 (primer corte)

- [x] Relevamiento tecnico completo del estado actual
- [x] Documento de trazabilidad de implementacion creado
- [x] Modelado final de metadata de origen en hits
- [x] Multi-vault semantic reader implementado
- [x] Multi-source episodic reader implementado
- [x] Servicio enterprise de fusion implementado
- [x] Integracion en `AgentMemory.retrieve(scope=...)`
- [x] Integracion CLI `cortex search --scope`
- [x] Tests unitarios nuevos de capa enterprise
- [x] Tests CLI de scope
- [x] Validacion local de tests objetivo
- [x] Validacion local de tests objetivo (segundo + tercer corte)

---

## Notas

Este documento se ira actualizando durante cada iteracion de implementacion y validacion.
