# Gap Analysis - Estado Actual vs Objetivo

**Documento:** diagnostico exhaustivo del estado actual del sistema de documentacion en Cortex
**Audiencia:** implementadores, revisores, decisores
**Estado:** validado contra el codigo actual (rama `feature/nuevo-modo-autonomo`, 2026-05-14)

---

## Resumen Ejecutivo del Gap

El sistema de documentacion actual tiene **7 gaps criticos** que impiden que Cortex sea un framework de documentacion canonica:

1. **Falta de DocType canonico:** la clasificacion de documentos es implicita por carpeta, no por campo en frontmatter.
2. **Carpetas muertas:** setup crea 6, solo 1-2 se usan de verdad.
3. **Writers faltantes:** 9 de 12 tipos no tienen escritor canonico.
4. **Frontmatter heterogeneo:** cada tipo de doc inventa sus campos sin schema unificado.
5. **Sin chunking:** notas largas se truncan silenciosamente.
6. **Sin persistencia de vectores:** cold start costoso, sync local<->enterprise imposible.
7. **Motor ciego a metadata:** enricher no filtra por carpeta, tag ni tipo.

Plus 1 gap enterprise:

8. **Campos de gobierno faltantes:** sin `owner, team, classification, retention`, el preset `regulated-organization` no cumple su propia promesa.

---

## Gap 1: DocType no es ciudadano de primera clase

### Estado actual

- No existe enum `DocType` ni equivalente.
- Clasificacion implicita por carpeta: una nota en `decisions/` se asume ADR.
- Algunas notas tienen `tags: [adr]` pero no es obligatorio.
- Frontmatter no tiene campo `doc_type` ni `type`.

### Evidencia

```yaml
# vault/decisions/ADR-001-hybrid-search-fusion.md (frontmatter actual)
---
title: "ADR-001: Hybrid Search Cross-Source Fusion"
date: 2026-04-15
tags: [architecture, retrieval, rrf, memory]
status: accepted
---
# NO HAY campo doc_type ni type
```

```yaml
# vault/architecture.md (frontmatter actual)
---
title: System Architecture
tags: [architecture, backend, overview]
---
# NO HAY date, NO HAY status, NO HAY doc_type
```

### Impacto

- El enricher no puede filtrar por tipo.
- El webgraph no puede agrupar por tipo.
- Las queries estructuradas son imposibles.
- La migracion entre carpetas borra la unica fuente de tipo.

### Objetivo

Enum cerrado `DocType` con 12 valores. Campo obligatorio `doc_type` en frontmatter validado por pydantic.

---

## Gap 2: Carpetas muertas

### Estado actual

Diagnostico real del disco (vault de Cortex):

| Carpeta | Setup la crea | Tiene writer | Archivos en disco |
|---|---|---|---|
| `vault/sessions/` | si | si | 13 (ACTIVA) |
| `vault/specs/` | si | si (`write_spec_note`) | 0 (vacia) |
| `vault/hu/` | si | si (`write_tracked_item_note`) | 0 (vacia) |
| `vault/decisions/` | si | NO | 1 (muerta) |
| `vault/runbooks/` | si | NO | 0 (vacia) |
| `vault/incidents/` | si | NO | 1 (muerta) |
| `vault/architecture/` | NO (implicito) | NO | 1 (huerfana) |
| `vault/changelog/` | NO (fantasma) | NO | 0 (vacia) |

### Evidencia

```python
# cortex/setup/orchestrator.py, linea 231-237
dirs = [
    layout.episodic_memory_path,
    layout.vault_path / "sessions",
    layout.vault_path / "decisions",
    layout.vault_path / "runbooks",
    layout.vault_path / "incidents",
    layout.vault_path / "hu",
    layout.vault_path / "specs",
]
```

```bash
# Vault real (rama actual)
$ ls vault/runbooks/
.gitkeep
$ ls vault/hu/
.gitkeep
$ ls vault/specs/
.gitkeep
$ ls vault/changelog/
.gitkeep
```

### Impacto

- Promesa estructural rota: el setup dice "vas a documentar incidents en `incidents/`" y no hay codigo que lo haga.
- Adopters ven carpetas vacias y asumen que falta funcionalidad.
- Documenter no sabe que hacer cuando algo no es session ni spec ni hu.

### Objetivo

- Cada carpeta justificada por su DocType y su writer.
- Carpetas sin writer se eliminan del setup.
- Setup crea carpetas + 1 archivo seed por carpeta (no `.gitkeep`).

---

## Gap 3: Writers faltantes

### Estado actual

Funciones `write_*` existentes en `cortex/documentation.py`:

| Funcion | Lineas | Destino | Estado |
|---|---|---|---|
| `write_session_note()` | 69-139 | `vault/sessions/` | usado activamente |
| `write_spec_note()` | 142-185 | `vault/specs/` | existe pero carpeta vacia |
| `write_tracked_item_note()` | 188-241 | `vault/hu/` | existe pero carpeta vacia |

### Funciones faltantes (objetivo)

| Funcion | DocType | Estado |
|---|---|---|
| `write_adr_note()` | ADR | NO EXISTE |
| `write_decision_note()` | DECISION | NO EXISTE |
| `write_incident_note()` | INCIDENT | NO EXISTE |
| `write_postmortem_note()` | POSTMORTEM | NO EXISTE |
| `write_runbook_note()` | RUNBOOK | NO EXISTE |
| `write_architecture_note()` | ARCHITECTURE | NO EXISTE |
| `write_changelog_note()` | CHANGELOG | NO EXISTE |
| `write_handoff_note()` | HANDOFF | NO EXISTE (se mezcla con session) |
| `write_glossary_entry()` | GLOSSARY | NO EXISTE (todo en CONTEXT.md monolitico) |

### Impacto

- Subagente documenter no tiene API para registrar 9 de 12 tipos.
- El que crea ADR lo hace manualmente con `VaultReader.create_note()` sin schema.
- La filosofia "Reference > Duplicate" del documenter no puede aplicar porque no hay piezas referenciables.

### Objetivo

Los 12 writers con firma simetrica:

```python
def write_X_note(
    data: XData,
    *,
    vault: VaultReader,
    vault_scope: str = "local",
    project_id: str | None = None,
    actor: str | None = None,
) -> Path: ...
```

---

## Gap 4: Frontmatter heterogeneo

### Estado actual

Cada tipo de doc tiene campos distintos y no hay schema:

```yaml
# SESSION
title: <str>
date: <date>
pr: <int>
author: <str>
branch: <str>
commit: <sha>
tags: [<str>]
status: fallback | auto-draft | handoff | completed

# ADR
title: <str>
date: <date>
tags: [<str>]
status: accepted

# ARCHITECTURE
title: <str>
tags: [<str>]
# sin date, sin status

# INCIDENT
title: <str>
date: <date>
tags: [<str>]
status: open
```

### Evidencia

Recorrido de frontmatters reales en `vault/` (5 tipos detectados, 4 schemas distintos).

### Impacto

- Imposible filtrar por status en una query global.
- Imposible computar metricas (% docs cerrados, edad media).
- Webgraph no puede mostrar status en hover.
- Migracion entre versiones de schema imposible (no hay `schema_version`).

### Objetivo

Schema canonico con:
- 9 campos obligatorios (`schema_version, doc_type, title, created_at, updated_at, tags, status, links, vault_scope, fingerprint`).
- 5 campos enterprise (`owner, team, classification, retention_days, audit_trail`).
- Campos especificos por tipo (extension pydantic).

---

## Gap 5: Sin chunking

### Estado actual

```python
# cortex/semantic/vault_reader.py, linea 94
search_text = f"{doc.title} {doc.content}"
texts.append((rel, search_text))
# ...
vectors = self._embedder.embed_batch(list(search_texts))
```

La nota ENTERA se embedea como UN SOLO vector.

### Detalles del problema

- Modelo `all-MiniLM-L6-v2` tiene ventana de ~512 tokens (~380 palabras).
- Notas con mas de 380 palabras se truncan silenciosamente.
- Sin chunking: una nota de 4000 palabras pierde 90% de su informacion al embedearse.

### Evidencia

Notas en el vault actual con mas de 1000 palabras:
- `vault/architecture/release-2-known-weaknesses.md`
- `vault/decisions/ADR-001-hybrid-search-fusion.md` (cuando tenga contenido completo)
- Cualquier runbook futuro (>2000 palabras tipicamente)

### Impacto

- Retrieval no encuentra secciones especificas de notas largas.
- Una query "como arranco el server" no recupera la seccion "Startup" del runbook si esta despues de la palabra 380.
- Runbooks, postmortems y ADRs largos son los mas afectados.

### Objetivo

Chunking por H2/H3 con metadata de seccion. Score del doc = max(scores de chunks).

---

## Gap 6: Vectores no persistidos

### Estado actual

```python
# cortex/semantic/vault_reader.py, linea 216-227
def _save_index_meta(self) -> None:
    meta: dict[str, Any] = {
        "doc_lengths": self._doc_lengths,
        "avgdl": self._avgdl,
        "idf": self._idf,
    }
    meta_path = self.vault_path / _INDEX_FILE
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
```

Solo se persisten stats BM25. **Los vectores NO se persisten.**

### Detalles del problema

- Cada arranque del proceso re-embedea todas las notas.
- ChromaDB SI persiste embeddings de memoria episodica.
- VaultReader NO persiste embeddings de memoria semantica.

### Evidencia (`.cortex_index.json`)

```json
{
  "doc_lengths": {"sessions/2026-04-14_foo.md": 234, ...},
  "avgdl": 412.3,
  "idf": {"deploy": 1.5, "auth": 2.1, ...}
}
```

No hay vectores.

### Impacto

- Vault de 1000 notas: ~8 segundos cold start (ONNX embedding x 1000).
- Vault de 5000 notas: ~40 segundos.
- Imposible compartir vectores entre instancias.
- Imposible sincronizar embeddings local <-> enterprise.

### Objetivo

Cache en disco `.cortex/vectors/` con invalidacion por fingerprint. Cold start <100ms para 1000 notas.

---

## Gap 7: Motor ciego a metadata

### Estado actual

```python
# cortex/context_enricher/enricher.py, linea 83-104
# Strategy 1-4: topic, file, keyword, pr_title
# Strategy 5: entity (function, class, imports)
hits = self._search_hybrid(queries[0], fetch_k)
```

`_search_hybrid` solo opera sobre contenido + embeddings. **No conoce la carpeta, no conoce el tag, no conoce el frontmatter.**

### Detalles del problema

- `EnrichmentFilters` no existe.
- `EnrichedItem` no tiene `doc_type`.
- El presenter muestra lista plana sin agrupar.
- Boost por intent solo distingue episodic vs semantic, no tipo de doc.

### Evidencia

```python
# cortex/models.py - EnrichedItem
class EnrichedItem(BaseModel):
    source: str  # "episodic" | "semantic"
    source_id: str
    title: str
    content: str
    score: float
    enriched_score: float
    matched_by: list[str]
    files_mentioned: list[str]
    date: datetime | None
    tags: list[str]
    # NO HAY doc_type
    # NO HAY status
    # NO HAY vault_scope
```

### Impacto

- El subagente no puede pedir "solo runbooks".
- El usuario no puede pedir "items de incidentes ultimos 30 dias".
- El presenter mezcla session + ADR + runbook en una sola lista.
- Imposible boostear ADR cuando la query es de decision.

### Objetivo

- `EnrichedItem` con campos `doc_type, status, vault_scope`.
- `EnrichmentFilters` opcional en `enrich()`.
- `QueryIntent` extendido con tipos.
- `GroupedPresenter` con output agrupado por `doc_type`.

---

## Gap 8: Enterprise sin campos de gobierno

### Estado actual

El frontmatter de promotion en `cortex/enterprise/knowledge_promotion.py`:

```yaml
promotion_status: promoted
promotion_origin_id: <project>:<path>
promotion_origin_path: <path>
promotion_origin_project: <project>
promotion_fingerprint: <sha256>
promotion_promoted_at: <ISO>
```

### Campos faltantes para `regulated-organization`

| Campo | Por que es necesario |
|---|---|
| `owner: <email>` | Saber a quien escalar dudas o revisiones |
| `team: <slug>` | Filtrar por equipo en multi-tenant |
| `classification: public/internal/confidential` | Politicas de visibilidad |
| `retention_days: <int>` | Politicas de borrado / GDPR |
| `audit_trail: [...]` | Quien aprobo, cuando, por que |
| `gpg_signature` (opcional) | Verificacion de aprobacion |

### Evidencia

`docs/enterprise/MANIFIESTO-CORTEX-ENTERPRISE.md` declara compliance como ciudadano de primera clase pero el frontmatter no lo soporta.

### Impacto

- Setup con preset `regulated-organization` no produce notas con metadata de compliance.
- Auditoria externa imposible (audit trail solo en `records.jsonl` separado).
- Promocion no diferencia clasificaciones.

### Objetivo

`EnterpriseFrontmatter` extiende `CommonFrontmatter` con 5 campos obligatorios. Writers detectan `vault_scope=enterprise` y exigen.

---

## Gap menor 9: CONTEXT.md monolitico

### Estado actual

Setup crea `CONTEXT.md` (`render_context_md` en `cortex/setup/templates.py`) como Ubiquitous Language glossary. Es un archivo unico con todos los terminos.

### Problema

- Crece sin limite.
- No vectorizable como entradas independientes.
- Edicion concurrente conflictiva.
- Webgraph no puede mostrar cada termino como nodo.

### Objetivo

`DocType.GLOSSARY` con un archivo por termino en `vault/glossary/`. Cada termino es nota canonica con `term`, `definition`, `related_terms`, `examples`.

---

## Gap menor 10: Dos versiones del documenter contradictorias

### Estado actual

- `.cortex/subagents/cortex-documenter.md`: filosofia "high-signal", principio "Reference > Duplicate", Tripartita Refinada para ADR.
- `cortex-pi/.pi/agents/cortex-documenter.md`: filosofia "comprehensive", "documentar todo, no omitir".

### Problema

- Sistema no sabe cual aplicar (depende del IDE adapter).
- Adopters reciben mensajes inconsistentes.

### Objetivo

Eliminar la version legacy en Fase 12. Dejar solo la "high-signal" con tabla de routing.

---

## Gap menor 11: Sin telemetria de retrieval

### Estado actual

`cortex/context_enricher/observer.py` no logguea a disco. Solo expone metricas via `EnrichedContext.total_searches`, etc.

### Problema

- Imposible saber que estrategias rinden.
- Imposible medir hit rate global.
- Sync_ticket es acto de fe.

### Objetivo

`cortex_telemetry` en frontmatter de session + `PersistentObserver` que escribe `.cortex/enrichment-events.jsonl`.

---

## Mapa de Gaps a Fases

| Gap | Fase que lo resuelve |
|---|---|
| 1 (DocType) | Fase 01 |
| 2 (Carpetas muertas) | Fase 12 |
| 3 (Writers faltantes) | Fase 03 |
| 4 (Frontmatter heterogeneo) | Fase 01 (schema), Fase 11 (backfill) |
| 5 (Sin chunking) | Fase 07 |
| 6 (Vectores no persistidos) | Fase 06 |
| 7 (Motor ciego) | Fase 08 |
| 8 (Enterprise sin gobierno) | Fase 10 |
| 9 (CONTEXT.md monolitico) | Fase 03 + Fase 11 |
| 10 (Documenter duplicado) | Fase 12 |
| 11 (Sin telemetria) | Fase 05 |

---

## Conclusion

La iniciativa no es opcional ni cosmetica. Cierra 11 gaps con impacto directo en:

- **Calidad de retrieval** (gaps 1, 5, 6, 7).
- **Coherencia estructural** (gaps 2, 3, 4, 9).
- **Compliance enterprise** (gap 8).
- **Coherencia del agente** (gap 10).
- **Decisiones basadas en datos** (gap 11).

Cada fase del plan ataca uno o varios gaps con criterios de aceptacion medibles.
