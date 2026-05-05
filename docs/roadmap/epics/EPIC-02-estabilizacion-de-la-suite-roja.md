# EPIC-02 - Estabilizacion de la suite roja

> Importante: marcar cada tarea completada en este archivo.
> Al cerrar la epica, completar [EPIC-02-estabilizacion-de-la-suite-roja-REALIZACION.md](./EPIC-02-estabilizacion-de-la-suite-roja-REALIZACION.md).

## Objetivo

Recuperar una base de pruebas estable sobre los casos hoy rojos que no pertenecen al pipeline de promotion enterprise: delegacion MCP parcial y performance de retrieval enterprise.

## Historia de usuario 1

**Como** maintainer del servidor MCP  
**Quiero** que la delegacion funcione incluso cuando el objeto fue construido en tests parciales  
**Para** que `_delegate_task()` no dependa de un constructor completo para operar de forma segura.

### Tarea 2.1 - Hacer lazy la resolucion de layout en MCP

**Archivo principal a cambiar**

- `cortex/mcp/server.py`

**Dependencias que deben revisarse o corregirse por arrastre**

- `tests/integration/mcp/test_server.py` - cobertura del caso `__new__`
- `tests/unit/test_mcp_server.py` - helpers privados y rutas
- `cortex/cli/main.py` - contrato del `project_root` que llega al server
- `cortex/workspace/layout.py` - si hace falta encapsular mejor discovery/reuse

**Checklist**

- [x] Introducir un helper interno que garantice acceso seguro a `WorkspaceLayout` aunque `_layout` no exista todavia.
- [x] Reemplazar en `_delegate_task()` el acceso directo a `self._layout.subagents_dir` por el helper nuevo.
- [x] Garantizar que `project_root` siga siendo el fallback minimo cuando el server fue construido de forma parcial.
- [x] Verificar que la delegacion siga reportando correctamente el caso "opencode no instalado".

## Historia de usuario 2

**Como** maintainer del retrieval enterprise  
**Quiero** que el smoke test de performance no pague costos pesados antes de ejecutar la busqueda  
**Para** mantener el servicio usable y evitar latencias artificiales en paths de prueba y en runtime.

### Tarea 2.2 - Volver lazy la construccion de readers/stores multi-source

**Archivos principales a cambiar**

- `cortex/enterprise/sources.py`
- `cortex/enterprise/retrieval_service.py`

**Dependencias que deben revisarse o corregirse por arrastre**

- `tests/unit/enterprise/test_retrieval_performance.py`
- `tests/unit/enterprise/test_retrieval_service.py`
- `tests/unit/enterprise/test_sources.py`
- `cortex/semantic/vault_reader.py` - costo de construccion de `VaultReader`
- `cortex/episodic/memory_store.py` - costo de construccion de `EpisodicMemoryStore`

**Checklist**

- [x] Evitar que `MultiVaultReader` cree todos los `VaultReader` en `__init__` si todavia no se va a buscar.
- [x] Evitar que `MultiEpisodicReader` cree todos los `EpisodicMemoryStore` en `__init__` si todavia no se va a buscar.
- [x] Mantener intacta la forma en que se inyecta metadata de `origin_scope`, `origin_project_id`, `origin_vault` y `origin_persist_dir`.
- [x] Confirmar que `EnterpriseRetrievalService.search()` sigue devolviendo el mismo contrato externo.

## Historia de usuario 3

**Como** maintainer del repositorio  
**Quiero** cerrar la epica con la porcion roja estabilizada  
**Para** evitar dejar arreglos parciales no validados.

### Tarea 2.3 - Ejecutar y fijar regresiones de la epica

**Archivos principales a cambiar**

- `tests/integration/mcp/test_server.py`
- `tests/unit/test_mcp_server.py`
- `tests/unit/enterprise/test_retrieval_performance.py`

**Dependencias que deben revisarse o corregirse por arrastre**

- `cortex/mcp/server.py`
- `cortex/enterprise/sources.py`
- `cortex/enterprise/retrieval_service.py`

**Checklist**

- [x] Ejecutar `pytest -q tests/integration/mcp/test_server.py`.
- [x] Ejecutar `pytest -q tests/unit/test_mcp_server.py`.
- [x] Ejecutar `pytest -q tests/unit/enterprise/test_retrieval_performance.py`.
- [x] Ejecutar `pytest -q` y confirmar que los fallos restantes, si existieran, pertenecen a otra epica y no a esta.

## Validacion de la epica

- [x] La falla de `_delegate_task()` sin `_layout` desaparecio.
- [x] El smoke test de performance enterprise vuelve a quedar por debajo del umbral esperado.
- [x] Completar el archivo de realizacion de la epica.
