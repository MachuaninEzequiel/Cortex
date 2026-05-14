# Fase 05 - Telemetria In-Vault - Realizacion

**Fecha de cierre:** 2026-05-14
**Esfuerzo real:** ~1 hora
**Estado:** Completado
**Dependencias cumplidas:** Fase 00, 01, 02, 03, 04

---

## 1. Resumen

Se implemento el Mecanismo 1 acordado: telemetria in-vault para medir
si el enricher rinde. Componentes:

1. **`PersistentObserver`** en `cortex/context_enricher/telemetry.py` que
   persiste eventos enrichment + citation a `.cortex/enrichment-events.jsonl`.
2. **`detect_citations()`** helper que parsea el body de una session note y
   detecta cuales items del enricher fueron citados via wiki-links o
   markdown links.
3. **Integracion con `ContextEnricher`**: nuevo parametro opcional
   `observer` en `__init__`. Cuando esta seteado, `enrich()` registra un
   evento al final del pipeline.
4. **`enricher_run_id`** propagado al `EnrichedContext`.
5. **`cortex_telemetry` en frontmatter de session**: el wrapper legacy
   `write_session_note` y `SessionService.create()` aceptan ahora el
   parametro opcional `cortex_telemetry: dict | None`. Se valida contra el
   schema `CortexTelemetry` (definido en Fase 01) y se persiste en el
   frontmatter de la session note.
6. **`cortex memory-report --telemetry --since-days N`**: el comando
   existente se extendio con dos flags opt-in que agregan una seccion de
   "Retrieval Telemetry" leyendo el JSONL y agregando stats globales y por
   estrategia.

---

## 2. Archivos creados / modificados

```text
Nuevos:
    cortex/context_enricher/telemetry.py            # 365 LOC: PersistentObserver, detect_citations, EnrichmentEvent, CitationEvent
    tests/unit/context_enricher/test_telemetry.py   # 25 tests

Modificados:
    cortex/models.py                                 # +1 campo: EnrichedContext.enricher_run_id
    cortex/context_enricher/enricher.py              # +observer opcional, registro de evento, propagacion de run_id
    cortex/documentation/_legacy_shims.py            # +cortex_telemetry kwarg en write_session_note
    cortex/services/session_service.py                # +cortex_telemetry kwarg en create() y propagacion
    cortex/cli/main.py                                # +flags --telemetry y --since-days en memory-report
```

---

## 3. Decisiones tomadas durante implementacion

### 3.1 Observer como parametro de `__init__`, no de `enrich()`

**Decision:** `ContextEnricher.__init__(observer=None)`, no
`enrich(observer=None)`.

**Razon:** un observer es una dependencia long-lived; configurarla por
llamada complica el codigo de los servicios. Tambien permite que cualquier
codigo que ya construye un `ContextEnricher` pueda inyectar telemetria sin
tocar las llamadas a `enrich()`.

**Trade-off:** un proceso que quiera deshabilitar telemetria temporalmente
debe reconstruir el enricher. Aceptable; el caso de uso normal es "ON o
OFF para siempre" segun config.

### 3.2 Telemetria no-bloqueante

`enrich()` envuelve `observer.record_enrichment(ctx, latency_ms)` en
`try/except`. Si la persistencia falla (disco lleno, JSONL corrupto,
permisos), loggea warning y devuelve el `EnrichedContext` igual. El run_id
puede quedar como `None`.

**Razon:** la telemetria es un sensor, no parte del contrato. Falla del
sensor != falla del enricher.

### 3.3 `enricher_run_id` se propaga via `model_copy(update=...)`

`EnrichedContext` es un pydantic `BaseModel` no frozen, asi que podria
mutarse. Pero usar `model_copy` mantiene inmutabilidad logica y devuelve
una instancia separada del observer.

### 3.4 Citation detection acepta multiples shapes del source_id

El agente puede citar de varias formas:
- Wiki-link con path completo: `[[decisions/ADR-007-foo]]`.
- Wiki-link con stem: `[[ADR-007-foo]]`.
- Wiki-link con alias o anchor: `[[ADR-007|Mi ADR]]`, `[[ADR-007#Decision]]`.
- Markdown link: `[texto](decisions/ADR-007-foo.md)`.

El helper construye un set de candidatos (`sid`, `stem`, `name`,
`posix_full`, `posix_no_ext`) y verifica interseccion con los targets
extraidos del body.

**Bug encontrado y resuelto:** la primera implementacion omitia el shape
"path sin extension" (`decisions/ADR-007-foo`), que es comun en wiki-links.
El smoke test inicial detecto la omision; fix en una linea.

### 3.5 `--telemetry` opt-in en `cortex memory-report`

**Decision:** mantener el comportamiento default del comando intacto
(enterprise reporting). La seccion de telemetria solo aparece con
`--telemetry`.

**Razon:** muchos adopters ya parsean el JSON del comando; agregar el
campo `telemetry` por default rompia esos consumidores. Opt-in conserva
backwards-compat absoluta.

El flag `--since-days N` (default 30) controla la ventana.

### 3.6 `cortex_telemetry` se valida en pydantic al guardar

Cuando el caller pasa un `dict`, pydantic v2 lo coerciona automaticamente
a `CortexTelemetry`. Si el dict carece de campos requeridos
(`enricher_run_id`, `context_items_offered`, etc), pydantic levanta
`ValidationError` que `_build_frontmatter` convierte a
`SchemaValidationError`. Fail loud, no degradacion silenciosa.

### 3.7 Aggregate filtra eventos antes de procesar

`aggregate(since_days=N)` filtra los eventos en memoria antes de agregar
por strategy/scope. Esto evita procesar eventos viejos cuando se quiere
una vista reciente.

**Optimizacion futura (no en MVP):** indexar el JSONL por timestamp para
seek directo. No necesario hasta que el archivo supere ~100MB.

---

## 4. Inconvenientes encontrados

### 4.1 Citation detection inicial omitia path sin extension

Descrito en 3.4. Resuelto en 1 minuto.

### 4.2 Sin otros inconvenientes

Tests pasaron al primer intento (excepto la deteccion mencionada). El
parche al `EnrichedContext` (agregar `enricher_run_id`) NO rompio ningun
consumidor existente porque el campo tiene default `None`.

---

## 5. Tests ejecutados

```text
tests/unit/context_enricher/test_telemetry.py    25 passed
---
Fase 05 nuevos:                                  25 passed
Modulo cortex/documentation/ (Fase 00-04):      ~216 passed (sin cambios)
Suite unit completa:                             983 passed, 6 skipped
```

Pre-Fase 05: 958 passed. Ahora: 983 passed. **+25 nuevos, 0 regresion.**

---

## 6. Coverage

```text
cortex/context_enricher/telemetry.py    160/170  94%
```

10 lineas no cubiertas son paths defensive (OSError en `_append`,
timestamps malformados en `_parse_ts`, edge cases en `_percentile` con
0 o 1 elemento) que requieren mocks de sistema. Coverage 94% supera el
objetivo del gate (>= 90%).

---

## 7. Checklist final (del README de la fase)

- [x] `cortex/context_enricher/telemetry.py` con `PersistentObserver`
- [x] `ContextEnricher` acepta `observer` opcional
- [x] `CortexTelemetry` agregado a `SessionFrontmatter` (ya en Fase 01)
- [x] `SessionService.create()` acepta y persiste `cortex_telemetry`
- [x] `cortex memory-report` extendido con flags `--telemetry` y `--since-days`
- [x] Citation detection implementada (`detect_citations`)
- [x] Tests >= 20 (25 implementados)
- [x] Coverage >= 90% (94%)

---

## 8. Gate de salida

- [x] `pytest tests/unit/context_enricher/test_telemetry.py` pasa al 100% (25/25)
- [x] Una session creada con `cortex_telemetry` persiste el bloque en frontmatter
- [x] `cortex memory-report --help` muestra los nuevos flags
- [x] Disabled telemetry no escribe archivo
- [x] Sin regresion en suite global (983 passed)
- [x] `REALIZACION.md` documentado

---

## 9. Cierre de deuda (post-Fase 06)

Tras completar Fase 06 (vector persistence) se cerro la deuda pendiente
de Fase 05 con +23 tests adicionales:

1. **Config `retrieval.telemetry`** en `config.yaml` template:
   ```yaml
   retrieval:
     telemetry:
       enabled: true
       path: .cortex/enrichment-events.jsonl
   ```

2. **Helper `make_observer(workspace_layout, *, enabled=None, config=None, project_root=None)`**
   en `telemetry.py`. Resuelve el path canonico y honora overrides de
   config. Usado por el CLI `cortex memory-report --telemetry`.

3. **Tests CLI con `CliRunner`** (`tests/unit/cli/test_memory_report_telemetry.py`):
   - `test_memory_report_without_telemetry_omits_section` (compat).
   - `test_memory_report_with_telemetry_empty` (gate).
   - `test_memory_report_with_telemetry_populated` (lectura).
   - `test_memory_report_json_output_with_telemetry` (formato JSON).

4. **Tests integration E2E** (`tests/integration/test_telemetry_e2e.py`):
   - `test_full_pipeline_enrich_cite_aggregate`.
   - `test_make_observer_returns_disabled_via_config`.
   - `test_session_persists_telemetry_block_in_frontmatter`.
   - `test_enricher_observer_records_real_items`.

5. **Tests helper `make_observer` y defensive paths**
   (`tests/unit/context_enricher/test_telemetry_helper.py`): 16 tests
   adicionales que llevaron `telemetry.py` al **100% de coverage** (subio
   de 94%).

6. **Citation detection mas robusta**: el helper actual usa heuristicas
   (wiki-links, markdown links). Una version futura podria usar un AST
   parser para markdown (`markdown-it-py`) y soportar mas formatos. No
   bloqueante para MVP.

### Resultado final

- **`cortex/context_enricher/telemetry.py`: 100% coverage** (187/187 lineas).
- **48 tests Fase 05 totales** (25 originales + 23 de deuda).
- **`config.yaml`** template incluye seccion `retrieval.telemetry`.
- **`make_observer`** disponible para servicios y CLI.
- **Suite global** estable, sin regresion: 1127+ tests passed.

---

## 10. Proximos pasos (Fase 06)

Implementar persistencia de vectores en disco segun
`fase-06-vector-persistence/README.md`:
- `cortex/semantic/vector_cache.py` con `VectorCache`.
- Integracion con `VaultReader.sync()` y `index_file()`.
- Layout `.cortex/vectors/index.json + chunks.bin`.
- Invalidacion por fingerprint, schema_version, mtime.
- Compaction de espacio reclamado.
- Tests + performance benchmark.

Beneficio principal: cold start de vault de 1000 notas pasa de ~8s a
<100ms.

Fase 06 no depende de Fase 05; puede paralelizar con Fase 07 (chunking)
si el equipo lo requiere.
