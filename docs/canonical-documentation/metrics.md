# Metrics - Metricas de Excelencia

**Documento:** definiciones operativas de las metricas que validan la iniciativa
**Audiencia:** implementadores, decisores
**Estado:** especificacion normativa

---

## 1. Filosofia de medicion

1. **Toda metrica tiene definicion operativa.** Como se calcula, donde se toma, que cuenta y que no.
2. **Toda metrica tiene objetivo numerico.** No "mejor" ni "alto"; numero concreto.
3. **Toda metrica tiene query reproducible.** Como sacarla de los datos del proyecto.
4. **Metricas de gate de fase son binarias** (cumple/no cumple). Metricas de salud son continuas.

---

## 2. Metricas de excelencia (objetivos globales del proyecto)

### 2.1 Frontmatter Drift

**Definicion:** porcentaje de notas en el vault cuyo frontmatter NO valida contra el schema de su `doc_type`.

**Calculo:**
```
drift = (notas_invalidas / total_notas) * 100
```

**Como medir:**
```bash
$ cortex docs validate --all
> 142/142 notas validan correctamente.
> Drift: 0%
```

**Objetivo:** **0%** tras Fase 11 (backfill). Cualquier nota nueva creada por writers canonicos garantiza 0% por diseno.

**Cuando se mide:** continuo (cada commit a `vault/`). CI rompe si > 0.

---

### 2.2 DocType Coverage

**Definicion:** porcentaje de notas con campo `doc_type` declarado en frontmatter.

**Calculo:**
```
coverage = (notas_con_doc_type / total_notas) * 100
```

**Como medir:**
```bash
$ cortex docs coverage --doc-type
> Notas con doc_type: 138/142 (97.2%)
> Notas sin doc_type:
>   - vault/notes/legacy-note-1.md
>   - vault/notes/legacy-note-2.md
>   ...
```

**Objetivo:** **>= 90%** despues de Fase 11. Notas restantes son legacy intencionalmente sin migrar.

---

### 2.3 Context Hit Rate Global

**Definicion:** porcentaje de items ofrecidos por el enricher que el agente realmente cita (via wiki-link en el body de la session note).

**Calculo:**
```
hit_rate = sum(items_used) / sum(items_offered)
```

Por sesion: cada sesion contribuye con su `cortex_telemetry.context_items_used / cortex_telemetry.context_items_offered`.

**Como medir:**
```bash
$ cortex memory-report --since 30d --metric hit-rate
> Window: 2026-04-14 to 2026-05-14
> Sessions: 23
> Items offered: 156
> Items used: 92
> Hit rate global: 59.0%
```

**Objetivo:** **>= 70%** tras 4 semanas de uso post Fase 05 (telemetria habilitada).

**Interpretacion:**
- < 50%: el enricher inyecta ruido en mas de la mitad de los casos. Hay que ajustar filtros o boost.
- 50-70%: aceptable; revisar tipos con hit rate bajo.
- >= 70%: el enricher rinde; revisar tipos especificos si quedan.

---

### 2.4 Hit Rate por DocType

**Definicion:** hit rate desagregado por tipo de documento recuperado.

**Calculo:** por DocType X:
```
hit_rate[X] = items_used_de_tipo_X / items_offered_de_tipo_X
```

**Objetivo por tipo:**

| DocType | Objetivo |
|---|---|
| ADR | >= 50% (decisiones referenciables) |
| RUNBOOK | >= 40% (mas operativos, menos universales) |
| ARCHITECTURE | >= 35% |
| POSTMORTEM | >= 30% (mas situacionales) |
| SESSION | >= 20% (mucho ruido, menor expectativa) |
| INCIDENT | >= 35% |
| DECISION | >= 40% |
| SPEC | >= 30% |
| OTROS | sin objetivo (data exploratoria) |

**Razon de los objetivos:** ADRs son densos en informacion permanente; sessions tienen mucho debugging que no se cita. Es esperado.

**Senial de alarma:** si ADR < 30% o runbook < 20%, el motor esta sobre-pesando esos tipos o el corpus es debil.

---

### 2.5 Embedding Cold Start

**Definicion:** tiempo desde `VaultReader.__init__` hasta el primer `search()` exitoso, con cache valido.

**Calculo:** instrumentar con `time.perf_counter()`.

**Como medir:**
```python
# tests/integration/test_cold_start_perf.py
def test_cold_start_with_cache():
    start = time.perf_counter()
    vault = VaultReader(vault_path)
    _ = vault.search("test")
    elapsed = (time.perf_counter() - start) * 1000
    assert elapsed < 100, f"Cold start {elapsed}ms > 100ms"
```

**Objetivo por tamano de vault:**

| Tamano | Cold start con cache |
|---|---|
| 100 notas | < 50ms |
| 1000 notas | < 100ms |
| 5000 notas | < 300ms |
| 10000 notas | < 800ms |

**Sin cache (primer arranque o cache invalidado):**

| Tamano | Cold start sin cache |
|---|---|
| 100 notas | < 1000ms |
| 1000 notas | < 10s |
| 10000 notas | < 100s |

---

### 2.6 Chunk Recall Delta

**Definicion:** mejora en recall@5 con chunking vs sin chunking, medida en A/B test con corpus controlado.

**Calculo:**
```
recall@5 = |queries con relevante en top-5| / |total queries|
delta = recall@5_with_chunking - recall@5_without_chunking
```

**Como medir:** test set de 50 queries con relevantes marcados manualmente:
```bash
$ cortex docs eval-retrieval --test-set tests/data/retrieval-test-set.jsonl
> Without chunking: recall@5 = 0.68
> With chunking:    recall@5 = 0.85
> Delta: +0.17
```

**Objetivo:** **>= +0.25** en notas > 1000 palabras. Para notas mas cortas, sin objetivo (esperamos paridad).

---

### 2.7 Webgraph Density

**Definicion:** numero promedio de wiki-links salientes por nota.

**Calculo:**
```
density = total_wiki_links / total_notas
```

**Como medir:**
```bash
$ cortex webgraph stats
> Total nodes: 142
> Total wiki-links: 387
> Average links per node: 2.73
```

**Objetivo:** **>= 2** post-backfill. Notas aisladas (sin links) son sospechosas.

---

### 2.8 Cache Hit Rate (Vector Cache)

**Definicion:** porcentaje de embeddings recuperados del cache vs computados.

**Calculo:**
```
cache_hit_rate = cache_hits / (cache_hits + cache_misses)
```

**Como medir:**
```bash
$ cortex docs vectorization stats
> Cache hits: 1842
> Cache misses: 23
> Hit rate: 98.8%
> Cache size: 4.2 MB
> Total entries: 1865
```

**Objetivo:** **>= 90%** en operacion normal. Si baja, hay churn excesivo (notas modificadas constantemente o fingerprint mismatch).

---

## 3. Metricas de gate de fase

### 3.1 Fase 00 - Preparacion

| Metrica | Objetivo |
|---|---|
| Inventario completo | 100% (todos los archivos `cortex/documentation/` planeados existen como stubs) |

### 3.2 Fase 01 - DocType y Schema

| Metrica | Objetivo |
|---|---|
| Tests unitarios pasan | 100% |
| `DocType` enum tiene 12 valores | si |
| 12 dataclasses creadas | si |
| 12 pydantic models creados | si |
| Validator rechaza frontmatter invalido | si (>= 8 casos de test) |

### 3.3 Fase 02 - Routing Table

| Metrica | Objetivo |
|---|---|
| Tabla `DOC_TYPE_ROUTING` tiene 12 entradas | si |
| Tests estaticos pasan | si (each DocType has entry, each template_path exists) |
| `resolve_route()` covering all DocTypes | si |

### 3.4 Fase 03 - Writers Canonicos Nuevos

| Metrica | Objetivo |
|---|---|
| 9 nuevos writers implementados | si (`write_adr_note, write_decision_note, write_incident_note, write_postmortem_note, write_runbook_note, write_architecture_note, write_changelog_note, write_handoff_note, write_glossary_entry`) |
| Tests por writer | >= 8 por writer (minimo, full, edge cases) |
| Templates Jinja2 | 12 archivos `.md.j2` |
| Tests por template | >= 4 por template |
| Coverage del modulo `documentation/` | >= 90% |

### 3.5 Fase 04 - Migrar Writers Existentes

| Metrica | Objetivo |
|---|---|
| `write_session_note` migrado al schema | si |
| `write_spec_note` migrado | si |
| `write_tracked_item_note` -> `write_hu_note` | si |
| Tests existentes pasan | si (no regresion) |
| Tests nuevos para campos extra | >= 3 por writer migrado |

### 3.6 Fase 05 - Telemetria In-Vault

| Metrica | Objetivo |
|---|---|
| `cortex_telemetry` en frontmatter de session | si |
| `PersistentObserver` escribe jsonl | si |
| `cortex memory-report` extendido | si |
| Tests | >= 12 |

### 3.7 Fase 06 - Vector Persistence

| Metrica | Objetivo |
|---|---|
| `VectorCache` operativo | si |
| Cold start 1000 notas < 100ms | si |
| Hit rate test > 90% | si |
| Invalidacion correcta | tests >= 5 |

### 3.8 Fase 07 - Chunking

| Metrica | Objetivo |
|---|---|
| `Chunker` operativo | si |
| Recall delta > +0.25 en notas largas | si (medido) |
| Tests chunking | >= 9 |
| Tests integracion con VaultReader | >= 3 |

### 3.9 Fase 08 - Retrieval Filters

| Metrica | Objetivo |
|---|---|
| `EnrichmentFilters` operativo | si |
| Boost por intent funciona | si |
| `GroupedPresenter` operativo | si |
| Tests | >= 15 |

### 3.10 Fase 09 - Webgraph Update

| Metrica | Objetivo |
|---|---|
| Nodos coloreados por `doc_type` | si |
| Density >= 2 medible en vault de pruebas | si |
| Tests | >= 5 |

### 3.11 Fase 10 - Enterprise Extensions

| Metrica | Objetivo |
|---|---|
| `EnterpriseFrontmatter` valido | si |
| Audit trail append-only verificable | si |
| Promotion DocType-aware funciona | si por cada tipo promotable |
| Tests enterprise | >= 20 |

### 3.12 Fase 11 - Migration y Backfill

| Metrica | Objetivo |
|---|---|
| Comando `cortex docs migrate` operativo | si |
| Dry-run muestra diffs sin escribir | si |
| Re-ejecucion idempotente | si |
| Vault de Cortex migrado | 100% notas validan |
| Reporte de cambios generado | si |

### 3.13 Fase 12 - Cleanup

| Metrica | Objetivo |
|---|---|
| Carpetas muertas eliminadas | si |
| Legacy documenter eliminado | si (`cortex-pi/.pi/agents/cortex-documenter.md`) |
| Gate global cumple | ver `README.md` seccion 13 |

---

## 4. Metricas de salud continua (dashboards)

### 4.1 Distribuciones a monitorear

**Notas por DocType:**
```
session:      45%
adr:          12%
runbook:       8%
architecture:  7%
spec:          5%
incident:      4%
postmortem:    3%
decision:      3%
hu:            8%
changelog:     3%
glossary:      2%
handoff:       0% (auto-expira)
```

**Status por tipo:**
- `adr.proposed` vs `adr.accepted` vs `adr.superseded`: distribucion sana ~10/70/20.
- `runbook.verified` vs `runbook.draft`: deseable > 80% verified.
- `incident.open` count: si > 5 abiertos por mas de 7 dias, alarma.

### 4.2 Salud del enricher (over time)

```
$ cortex memory-report --since 90d --plot
[ASCII chart de hit rate por semana]
```

Trend descendente -> investigar.

### 4.3 Salud del vault enterprise

| Metrica | Donde se lee | Objetivo |
|---|---|---|
| Promotions/semana | `records.jsonl` | depende del proyecto |
| Pending reviews | `cortex review-knowledge --pending` | < 10 |
| Notas con classification missing | `cortex docs audit` | 0 |
| Retention violations | `cortex docs maintenance --check` | 0 |

---

## 5. Reportes automatizados

### 5.1 `cortex docs status` (resumen)

```bash
$ cortex docs status
Cortex Documentation System Status
==================================

Vault: vault/ (local)
Total notas: 142
DocType coverage: 138/142 (97.2%)
Frontmatter drift: 0/142 (0%)

Distribucion por tipo:
  session:       64 (45.1%)
  adr:           17 (12.0%)
  runbook:       11 (7.7%)
  architecture:  10 (7.0%)
  spec:           7 (4.9%)
  ...

Vectorization:
  Cache hit rate: 98.8%
  Total chunks: 287
  Cache size: 4.2 MB

Retrieval (last 30d):
  Enrichments: 142
  Hit rate: 67.3%
  By type:
    adr:      71% (top performer)
    runbook:  82% (top performer)
    session:  29% (mucho ruido, ok)
  Average latency: 187ms p50

Webgraph:
  Density: 2.73 links/node
  Isolated nodes: 4 (3%)

Status: HEALTHY
```

### 5.2 `cortex docs status --enterprise`

Vista enterprise: agrega scope by team, retention violations, pending reviews.

---

## 6. Testing de metricas

Cada metrica tiene su test de calculo:

```python
# tests/unit/documentation/test_metrics.py

def test_frontmatter_drift_calculation():
    """drift = 0% when all notes validate."""

def test_doc_type_coverage_calculation():
    """coverage = 100% when all notes declare doc_type."""

def test_hit_rate_calculation():
    """hit_rate = used / offered."""

def test_chunk_recall_delta_with_corpus():
    """Recall mejora con chunking en notas largas."""
```

---

## 7. Anti-patrones de medicion

1. **No medir tiempo de implementacion como metrica de calidad.** Mide salud del sistema, no esfuerzo.
2. **No promediar metricas heterogeneas.** "Hit rate promedio 65%" ocultando que ADR=20% y RUNBOOK=90% es enganoso.
3. **No optimizar a una sola metrica.** Hit rate alto con coverage bajo significa que solo se citan items obvios.
4. **No medir sin baseline.** Antes de Fase 05, no hay hit rate. Es 0/0 = ND, no 0%.
5. **No exigir 100% en gates blandos.** "100% hit rate" indica overfit, no excelencia.

---

## 8. Ciclo de revision de metricas

Cada 90 dias post-launch:

1. Revisar objetivos numericos vs realidad.
2. Identificar metricas que no se mueven (utilidad cuestionable).
3. Identificar metricas que correlacionan demasiado (redundantes).
4. Proponer ajustes via ADR.

---

## 9. Decisiones clave

1. **Hit rate como reina:** mide impacto real, no actividad.
2. **Objetivos diferenciados por tipo:** ADR != SESSION; mismo umbral es injusto.
3. **Cold start medido con cache valido:** si invalido es siempre peor; no ocultar el caso real.
4. **Drift 0% es no-negociable:** si una nota no valida, hay bug en el writer.
5. **Coverage 90% acepta legacy:** no obsesionarse con backfill perfecto.
6. **Telemetria persistida en local, opt-in en enterprise:** privacidad first.
