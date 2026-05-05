# Realizacion - EPIC-02

> Completar este archivo al terminar todos los checklists de [EPIC-02-estabilizacion-de-la-suite-roja.md](./EPIC-02-estabilizacion-de-la-suite-roja.md).

## Estado

- Fecha de inicio: 2026-05-05
- Fecha de cierre: 2026-05-05
- Responsable: agente autonomo de desarrollo

## Resumen ejecutivo

Se estabilizaron dos lineas de falla identificadas como ajenas al pipeline de promotion enterprise:

1. **Delegacion MCP parcial**: `_delegate_task()` en `cortex/mcp/server.py` fallaba con `AttributeError` cuando el servidor se construia via `__new__` (sin `__init__`), porque accedia directamente a `self._layout`. Se introdujo `_get_layout()` con descubrimiento lazy y se reemplazo el acceso directo.

2. **Performance de retrieval enterprise**: `MultiVaultReader` y `MultiEpisodicReader` en `cortex/enterprise/sources.py` construian instancias de `VaultReader` y `EpisodicMemoryStore` en `__init__`, pagando costos pesados (carga de modelos ONNX, inicializacion de ChromaDB) antes de que se necesitaran. Se convirtieron a construccion lazy via `_get_readers()` y `_get_stores()`, preservando intacta la inyeccion de metadata (`origin_scope`, `origin_project_id`, `origin_vault`, `origin_persist_dir`).

## Archivos modificados

- `cortex/mcp/server.py` — helper `_get_layout()` y uso en `_delegate_task()`
- `cortex/enterprise/sources.py` — construccion lazy en `MultiVaultReader` y `MultiEpisodicReader`

## Validaciones ejecutadas

- `pytest -q tests/integration/mcp/test_server.py` — 6 passed
- `pytest -q tests/unit/test_mcp_server.py` — 7 passed
- `pytest -q tests/unit/enterprise/test_retrieval_performance.py` — 1 passed
- `pytest -q tests/unit/enterprise/test_sources.py` — 3 passed
- `pytest -q tests/unit/enterprise/test_retrieval_service.py` — 5 passed
- `pytest -q` (suite completa) — 380 passed, 6 skipped, 3 failed (los 3 restantes pertenecen a EPIC-03/promotion enterprise)

## Decisiones tomadas

- **_get_layout como metodo de instancia**: se opto por un metodo privado en lugar de un helper externo para mantener el encapsulamiento y no expandir la superficie publica del servidor MCP.
- **Lazy construction con cache**: los readers/stores se crean una sola vez en la primera llamada a `search()` y se cachean, evitando pagar el costo repetidamente pero sin penalizar paths que nunca buscan.
- **Sin tocar retrieval_service.py**: `EnterpriseRetrievalService.search()` no requirio cambios porque ya instanciaba `MultiVaultReader`/`MultiEpisodicReader` en cada llamada; el beneficio provino de hacer lazy la construccion interna de esas clases.

## Pendientes o riesgos abiertos

- Ninguno para esta epica. La suite de MCP y retrieval enterprise queda estable.
