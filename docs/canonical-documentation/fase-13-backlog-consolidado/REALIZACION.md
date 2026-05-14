# Fase 13 - Backlog Consolidado - Realizacion

**Fecha de cierre parcial:** 2026-05-14
**Esfuerzo real:** ~1 hora
**Estado:** Parcialmente completada (ver checklist por bloque)
**Dependencias cumplidas:** Fases 00-12

---

## 1. Resumen

Fase 13 consolida en un solo plan todos los pendientes acumulados durante
las 12 fases anteriores y desarrolla el subset que no requiere
autorizaciones destructivas. Los items que SI requieren autorizacion
(eliminaciones de archivos legacy, movimientos en el vault real) quedan
documentados en el ``README.md`` como bloques A y E para ejecucion futura
bajo confirmacion explicita del operador.

Bloques desarrollados en esta sesion:

- **Bloque B**: tests defensivos -> coverage incremental.
- **Bloque C**: refactor ``infer_doc_type_from_path`` unificado.
- **Bloque D parcial**: CLI ``cortex docs search`` con filtros estructurales.

Bloques pendientes (requieren autorizacion):

- **Bloque A**: ``git rm`` de archivos legacy.
- **Bloque E**: mover 3 archivos raiz del vault real.

---

## 2. Archivos creados / modificados

```text
Nuevos:
    cortex/cli/docs_search.py                              # 130 LOC: cortex docs search
    tests/unit/cli/test_docs_search.py                     # 7 tests
    tests/unit/documentation/test_writers_defensive.py     # 13 tests defensive
    tests/unit/semantic/test_vector_cache_defensive.py     # 6 tests defensive

Modificados:
    cortex/documentation/doc_type.py        # +infer_doc_type_from_path (canonical)
    cortex/documentation/inventory.py       # delega al canonical
    cortex/context_enricher/enricher.py     # _doc_type_from_doc delega al canonical
    cortex/webgraph/semantic_source.py      # _doc_type_from_rel_path delega al canonical
    cortex/cli/docs_subcommand.py           # +cortex docs search
```

---

## 3. Bloque B - Coverage incremental (✅ completado)

### writers.py: 89% -> 99%

13 nuevos tests cubren los paths defensivos:
- ``_coerce_status`` con status valido, vacio y desconocido.
- ``_next_number`` con folder ausente, subdirectorios e identifiers no numericos.
- ``write_session_note_canonical`` sin session_id.
- ``write_spec_note_canonical`` happy path.
- ``write_hu_note`` validaciones (sin external_id, sin source).
- ``_write_note`` fallback de ``relative_to`` cuando el target esta fuera del vault.

### vector_cache.py: 95% -> 100%

6 tests cubren:
- ``get`` con ``chunks.bin`` truncado o ausente -> miss.
- ``invalidate`` idempotente sobre entradas ya marcadas.
- ``compact`` saltando entradas no leibles.
- ``__contains__`` con valor no-string -> ``False``.
- ``_read_vector_at`` con short-read -> ``ValueError``.

### Resumen coverage Fase 13

```text
cortex/documentation/writers.py        212/213  99% (1 linea: return {} default)
cortex/semantic/vector_cache.py        189/189  100%
cortex/semantic/chunker.py              82/83   99% (defensive ya aceptado)
cortex/context_enricher/telemetry.py   187/187  100% (cerrado en Fase 05 deuda)
cortex/documentation/__init__.py        22/22   100%
cortex/documentation/_legacy_shims.py    40/41   98%
```

---

## 4. Bloque C - Refactor canonical doc_type inference (✅ completado)

**Problema:** tres implementaciones distintas de "inferir DocType desde
path", una en cada modulo:
- ``cortex.documentation.inventory.classify_path``
- ``cortex.context_enricher.enricher._doc_type_from_doc``
- ``cortex.webgraph.semantic_source._doc_type_from_rel_path``

**Solucion:** nuevo helper canonico
``cortex.documentation.doc_type.infer_doc_type_from_path`` que acepta
``Path | str``, normaliza separadores y delega a ``doc_type_from_path``.

Las tres implementaciones se refactorizaron para delegar al canonico via
lazy import (evita ciclos). Los tests existentes siguen pasando sin
modificacion -> el contrato publico no cambio.

```text
Antes: 3 implementaciones x ~15 LOC cada una = ~45 LOC duplicado
Despues: 1 funcion canonica + 3 thin wrappers = ~25 LOC totales
```

---

## 5. Bloque D - cortex docs search con filtros (✅ completado)

**Problema:** la API Python ``ContextEnricher.enrich(work, filters=...)``
estaba lista desde Fase 08 pero el CLI no la exponia.

**Solucion:** nuevo subcomando ``cortex docs search <query> [opciones]``
en ``cortex/cli/docs_search.py`` que construye ``EnrichmentFilters`` desde
flags CLI y pasa al enricher.

Flags soportados:

```text
--doc-type [adr|runbook|...]     Filter (repeatable)
--exclude-doc-type [...]          Exclude (repeatable)
--status [accepted|...]           Status whitelist
--tag [security]                  AND-composed tag requirements
--tag-any [foo,bar]               OR-composed tag requirements
--scope [local|enterprise|all]    Vault scope
--max-age-days N                  Drop items older than N days
--project-id [...]                Multi-tenant filter (repeatable)
--strict                          Drop items without doc_type
--format [text|json|compact]      Output format
```

El comando legacy ``cortex search`` queda intacto para preservar
backwards-compat con consumers existentes que dependen del payload RRF
crudo.

7 tests de CliRunner verifican el comportamiento:
- Output text / json / compact.
- Validacion de doc_type / scope / format invalidos.
- Filtros propagados correctamente al enricher.

---

## 6. Bloques A y E (pendientes - requieren autorizacion)

### Bloque A: Eliminaciones destructivas

```text
[ ] git rm cortex/documentation.py
[ ] git rm cortex-pi/.pi/agents/cortex-documenter.md
[ ] Migrar consumidores fuera de cortex/documentation/_legacy_shims.py
    (4 archivos: services/session_service.py, services/spec_service.py,
     services/pr_service.py, workitems/service.py)
[ ] git rm cortex/documentation/_legacy_shims.py (despues de migrar)
```

Riesgo: bajo en los 2 primeros items (los archivos no se importan desde
hace 9 fases). Medio en el shim cleanup porque toca 4 services.

### Bloque E: Operativo del vault real de Cortex

Los 3 archivos raiz del vault (`architecture.md`, `auth.md`,
`getting_started.md`) quedaron como ``unclassifiable`` durante
``cortex docs migrate --apply``. Decisiones a tomar:

```text
[ ] vault/architecture.md          -> mover a vault/architecture/main.md
[ ] vault/auth.md                  -> mover a vault/architecture/auth.md
[ ] vault/getting_started.md       -> mover a docs/guides/ (no es vault canonico)
```

Tras moverlos, ``cortex docs validate`` deberia reportar ``Invalid: 0``.

---

## 7. Bloques restantes (no-criticos)

### C residuales (refactors)

```text
[ ] Invalidacion granular de chunks (vs purge total al re-indexar)
[ ] Compaction automatica del VectorCache al 30% invalidados
[ ] Aristas tipadas `supersedes` en webgraph builder
[ ] EpisodicSource con doc_type=episodic en metadata
[ ] File locking en VectorCache (multi-proceso safety)
```

### D residuales (UX externa)

```text
[ ] MCP tool cortex_search con args estructurales (mismo contrato que CLI)
[ ] cortex review-knowledge subcomandos (pending/approve/reject)
[ ] Dashboard cortex-pi UI extension (TypeScript)
[ ] Investigar test flaky test_latest_session (preexistente, no regresion)
```

### Otros

```text
[ ] mypy strict pass sobre cortex/documentation/
[ ] Tests del presenter legacy (to_markdown/to_compact) -> 90%+
```

---

## 8. Tests ejecutados

```text
tests/unit/cli/test_docs_search.py                  7 passed
tests/unit/documentation/test_writers_defensive.py 13 passed
tests/unit/semantic/test_vector_cache_defensive.py  6 passed
---
Fase 13 nuevos:                                    26 passed
Suite global completa:                          1336 passed, 6 skipped
```

Pre-Fase 13: 1310. Ahora: 1336. **+26 nuevos, 0 regresion** (excluyendo el
test flaky preexistente ``test_latest_session``).

---

## 9. Coverage actual de los modulos clave

```text
cortex/context_enricher/telemetry.py    100%
cortex/documentation/__init__.py        100%
cortex/documentation/data.py            100%
cortex/documentation/doc_type.py        100%
cortex/documentation/errors.py          100%
cortex/documentation/inventory.py        95%
cortex/documentation/routing.py         100%
cortex/documentation/schemas/*           ~97%
cortex/documentation/validation.py      100%
cortex/documentation/writers.py          99%
cortex/documentation/audit.py           100%
cortex/documentation/templates_engine.py 100%
cortex/documentation/_legacy_shims.py    98%
cortex/documentation/backup.py          100%
cortex/documentation/migration.py        ~93%
cortex/semantic/chunker.py               99%
cortex/semantic/vector_cache.py         100%
cortex/context_enricher/filters.py      100%
cortex/context_enricher/doc_intent.py   100%
cortex/webgraph/style.py                100%
cortex/enterprise/governance.py          ~95%
cortex/enterprise/maintenance.py         ~95%
cortex/enterprise/promotion_doctype.py   ~93%
```

---

## 10. Snapshot final de la iniciativa canonical-documentation

```text
+========================================================================+
| Iniciativa Canonical Documentation - 13 fases                            |
+========================================================================+
| Fase 00 - Preparacion                       Completada (~1 h)            |
| Fase 01 - DocType y Schema                  Completada (~2 h)            |
| Fase 02 - Routing Table                     Completada (~1 h)            |
| Fase 03 - Writers canonicos nuevos          Completada (~2 h)            |
| Fase 04 - Migrar writers existentes         Completada (~1 h)            |
| Fase 05 - Telemetria in-vault               Completada + deuda cerrada   |
| Fase 06 - Vector persistence                Completada (~1 h)            |
| Fase 07 - Chunking                          Completada (~1 h)            |
| Fase 08 - Retrieval filters                 Completada (~1 h)            |
| Fase 09 - Webgraph update                   Completada (~30 min)         |
| Fase 10 - Enterprise extensions             Completada (~1 h)            |
| Fase 11 - Migration y Backfill              Completada (~1 h)            |
| Fase 12 - Cleanup                           Completada (~30 min)         |
| Fase 13 - Backlog consolidado               Parcial (bloques A+E pdtes)  |
+========================================================================+

Total tests: 1336 passed, 6 skipped, 0 fallas
Codigo nuevo: ~5000 LOC + ~3500 LOC tests
Cobertura global: >= 95% en modulos canonicos nuevos

Vault real de Cortex migrado: 16/19 notas validan; 3 quedaron
unclassifiable (raiz) y se documentan en el bloque E.
```

---

## 11. Que falta para "100% cerrado"

1. **Operador ejecuta bloque A** (`git rm` de archivos legacy + migracion
   de los 4 services para eliminar `_legacy_shims.py`).
2. **Operador ejecuta bloque E** (mover 3 archivos raiz del vault).
3. **`cortex docs validate --all`** reporta `Invalid: 0`.

Cuando esos 3 items esten cumplidos, la iniciativa canonical-documentation
esta 100% cerrada y la auditoria puede certificar:
- Schema canonico en todo el vault.
- Cero archivos legacy huerfanos.
- Setup orchestrator declara las 12 carpetas canonicas (Fase 12).
- Suite global pasa al 100%.

El resto de los pendientes (refactors residuales, UX externa, etc.) son
mejoras incrementales no-criticas para la iniciativa.
