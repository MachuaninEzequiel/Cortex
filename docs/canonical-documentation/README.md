# Cortex Canonical Documentation - Plan por Fases

**Fecha:** 2026-05-14
**Estado:** Propuesta tecnica aprobada, pendiente de ejecucion por fases
**Alcance:** Rediseno del sistema de documentacion de Cortex (modelo de datos, schema de frontmatter, escritores canonicos, routing por tipo, vectorizacion inteligente, filtros estructurales en retrieval, extensiones enterprise)
**Principio rector:** cada tipo de documento es un ciudadano de primera clase con contrato canonico end-to-end (modelo + schema + template + writer + ruta + estrategia de indexacion + estrategia de retrieval)

---

## 1. Resumen Ejecutivo

El sistema de documentacion actual de Cortex tiene tres problemas estructurales:

1. **El motor es ciego a la estructura.** El enricher no filtra por carpeta, tag ni tipo de documento. La carpeta es invisible para el modelo. El frontmatter no tiene campo `doc_type` canonico. Esto significa que organizar carpetas por si solo no mejora retrieval.

2. **Las carpetas muertas son falsa promesa.** Setup crea 6 carpetas (`sessions, decisions, runbooks, incidents, hu, specs`); solo `sessions` se usa de verdad. No existen funciones `write_adr_note, write_incident_note, write_runbook_note, write_decision_note, write_architecture_note, write_postmortem_note, write_changelog_note, write_handoff_note`.

3. **La vectorizacion es naive.** No hay chunking (notas largas se truncan silenciosamente), embeddings no se persisten (se recalculan en cada arranque), frontmatter no se incluye en el texto a embedear (pierde senal estructural).

La propuesta resuelve los tres problemas a la vez con un rediseno en seis capas: DocType canonico, schema de frontmatter unificado, tabla de routing por tipo, escritores simetricos, vectorizacion inteligente (chunking + persistencia + boost por tipo), y recuperacion consciente del schema con telemetria in-vault.

Cada capa contempla extensiones enterprise (campos de gobierno, namespacing por proyecto, audit trail, promotion DocType-aware) sin duplicar codigo.

---

## 2. Objetivos

### 2.1 Objetivos funcionales

1. Cada tipo de documento (ADR, INCIDENT, RUNBOOK, DECISION, ARCHITECTURE, POSTMORTEM, CHANGELOG, HANDOFF, SESSION, SPEC, HU, GLOSSARY) tiene escritor canonico simetrico.
2. Frontmatter canonico con schema unificado validado contra `pydantic`. Notas que no validan no se persisten.
3. Tabla de routing `DOC_TYPE_ROUTING` como unica fuente de verdad para subfolder, naming, template, writer y estrategia de indexacion.
4. Vectorizacion con chunking por seccion (H2/H3), embeddings persistidos en disco con cache por `fingerprint`, y enriquecimiento del texto con `doc_type` y `tags`.
5. Enricher con filtros estructurales (`doc_types`, `min_status`, `tags_required`, `vault_scope`) y boost por relevancia de tipo a la query.
6. Telemetria in-vault (`cortex_telemetry` en frontmatter de session) que registra hit rate, items usados, estrategias efectivas y distribucion por tipo.
7. Presenter agrupa items recuperados por `doc_type` para reduccion de ruido cognitivo.
8. Webgraph muestra nodos coloreados por `doc_type` y aristas tipadas.

### 2.2 Objetivos arquitectonicos

1. El subagente `cortex-documenter` no decide carpetas; declara `doc_type` y el codigo rutea.
2. Templates viven en archivos `.md.j2` separados, editables sin tocar Python.
3. Validacion de schema falla loud: si un writer no respeta el contrato, falla con error claro.
4. Cada escritor sigue la misma secuencia: validar, resolver routing, renderizar, persistir, indexar incrementalmente, registrar audit trail si enterprise.
5. La vectorizacion soporta chunking sin romper la API publica de `VaultReader`.
6. Enterprise extensions son ortogonales: el mismo writer funciona en local y enterprise segun `vault_scope`.

### 2.3 Objetivos de calidad

1. **DocType coverage:** mas del 90% de docs nuevos tienen `doc_type` declarado tras migracion.
2. **Frontmatter drift:** 0% de notas falla validacion schema tras backfill.
3. **Context hit rate:** mas del 70% de sesiones tienen al menos un item del enricher citado por el agente.
4. **Embedding cold start:** menos de 100ms para vault de 1000 notas con cache valido.
5. **Chunk recall delta:** mejora de retrieval del 25% en notas mayores a 1000 palabras (medida por A/B test).
6. **Webgraph density:** al menos 2 wiki-links promedio por nota tras backfill.

---

## 3. No Objetivos

Esta propuesta no debe:

1. Reescribir el motor de busqueda hibrido (`HybridSearch`, RRF, intent detection). Solo le agregamos filtros estructurales.
2. Cambiar el modelo de embedding (`all-MiniLM-L6-v2`, 384 dims). Solo cambiamos como se aplica (chunking, persistencia).
3. Reemplazar `VaultReader`. Extender, no romper su API publica.
4. Implementar storage Git-like nativo del vault enterprise (eso es Fase 2-4 del Proposal Enterprise, fuera de scope).
5. Implementar GPG signing, rollback de promociones ni branches de conocimiento.
6. Romper CLI ni MCP server existentes. Solo agregar tools/flags nuevos.
7. Forzar migracion destructiva: el backfill es idempotente y reversible.
8. Inventar nuevos `DocType` ad-hoc. La lista de 12 tipos es cerrada en MVP; extension futura requiere ADR.
9. Tocar memoria episodica salvo lo necesario para que el enricher acepte filtros estructurales.
10. Documentar todo. El principio "Reference > Duplicate" del documenter sigue vigente.

---

## 4. Filosofia de Diseno

### 4.1 Cada tipo de documento es un contrato

Un `DocType` no es una carpeta. Es un contrato completo:

```
DocType.ADR := (
    model = ADRData (campos tipados),
    schema = frontmatter validado pydantic,
    template = adr.md.j2,
    writer = write_adr_note,
    subfolder = "decisions",
    filename = "ADR-{number:03d}-{slug}.md",
    indexer = "auto" (index_file inmediato),
    promotable = True,
    enterprise_subfolder = "decisions/{project_id}",
    retrieval_boost_per_intent = {
        "decision": 2.0,
        "architecture": 1.5,
        "history": 1.2,
    }
)
```

El contrato vive en codigo Python y se propaga a templates, validadores, retrieval y webgraph. No hay convenciones implicitas.

### 4.2 La carpeta es consecuencia, no causa

Hoy la carpeta es decision arbitraria del autor o del setup. Despues de este rediseno, la carpeta es output del routing table. Si cambiamos politica de carpetas, una sola tabla. Si el documenter declara `doc_type=ADR`, va a `vault/decisions/`; si fuese enterprise con `project_id=mi-proyecto`, va a `vault-enterprise/decisions/mi-proyecto/`.

### 4.3 El frontmatter es la API estructurada del vault

Todo lo que el motor pueda razonar sobre una nota debe estar en frontmatter. Contenido es para humanos y embeddings; frontmatter es para queries, filtros y webgraph.

### 4.4 Vectorizacion fina, recuperacion granular, presentacion agrupada

- **Indexacion fina:** una nota larga se splittea en chunks; cada chunk es un sub-doc indexable.
- **Recuperacion granular:** top-k busca chunks, score del doc = max(scores de chunks).
- **Presentacion agrupada:** el presenter agrupa por doc padre y por `doc_type` para reducir ruido.

### 4.5 Telemetria primero, optimizacion despues

Antes de optimizar el enricher, primero medir si rinde. La telemetria in-vault (Mecanismo 1) es prerrequisito para cualquier ajuste posterior.

### 4.6 Enterprise es extension, no fork

Las extensiones enterprise (governance fields, namespacing, audit trail) se aplican sobre el mismo writer/schema/template, solo cambiando ramas condicionales por `vault_scope`. No hay codigo duplicado.

### 4.7 Migracion idempotente y reversible

El backfill de notas existentes infiere `doc_type` por carpeta actual, escribe frontmatter nuevo sin borrar campos legacy, y produce un reporte de cambios. Re-ejecutar no rompe.

### 4.8 Fail loud, no degradacion silenciosa

Si una nota no valida schema, el writer falla con mensaje claro. Si un `doc_type` no esta en routing table, falla. Sin defaults silenciosos.

---

## 5. Diagnostico del Estado Actual

Diagnostico completo en [`gap-analysis.md`](gap-analysis.md). Resumen:

### 5.1 Carpetas declaradas vs usadas

| Carpeta | Setup crea | Tiene escritor `write_*` | Estado real |
|---|---|---|---|
| `sessions/` | si | si (`write_session_note`) | ACTIVA - 13 archivos |
| `specs/` | si | si (`write_spec_note`) | vacia |
| `hu/` | si | si (`write_tracked_item_note`) | vacia |
| `decisions/` | si | no | 1 archivo |
| `runbooks/` | si | no | vacia |
| `incidents/` | si | no | 1 archivo |
| `architecture/` | no (implicito) | no | 1 archivo |
| `changelog/` | no (fantasma) | no | vacia |

### 5.2 Funciones write_* existentes vs faltantes

Existentes (`cortex/documentation.py`):
- `write_session_note()` - usado activamente
- `write_spec_note()` - codigo existe, carpeta vacia
- `write_tracked_item_note()` - codigo existe, carpeta vacia

Faltantes (objetivo de Fase 03):
- `write_adr_note()` (DECISION + criterios Tripartita)
- `write_incident_note()`
- `write_runbook_note()`
- `write_decision_note()` (decisiones que no son ADR pero merecen registro)
- `write_architecture_note()`
- `write_postmortem_note()`
- `write_changelog_note()`
- `write_handoff_note()` (separar de session por contrato distinto)
- `write_glossary_entry()` (CONTEXT.md como entradas estructuradas)

### 5.3 Vectorizacion: gaps identificados

| Gap | Estado actual | Objetivo |
|---|---|---|
| Chunking | No existe (truncacion silenciosa a 512 tokens) | Splitting por H2/H3, agregacion top-k |
| Persistencia vectores | Recalculo en cada arranque | Cache en disco por `fingerprint`, invalidacion por mtime |
| Texto embedeado | `title + content` | `title + tags + doc_type + content_chunk` |
| Sync local <-> enterprise | No existe | Cache compartido por `fingerprint` |

### 5.4 Retrieval: gaps identificados

| Gap | Estado actual | Objetivo |
|---|---|---|
| Filtro por tipo | No existe (motor ciego a metadata) | `doc_types: list[DocType]` en `WorkContext` y API |
| Filtro por status | No existe | `min_status, exclude_status` |
| Filtro por scope | Existe en enterprise (`local/enterprise/all`) | Conservar y extender a filtros por tag |
| Boost por intent | Existe para episodic vs semantic | Extender a boost por DocType segun intent |
| Presenter agrupado | Items en lista plana | Agrupacion por DocType en output |
| Telemetria persistida | Solo stderr | `cortex_telemetry` en frontmatter session |

### 5.5 Enterprise: gaps identificados

| Gap | Estado actual | Objetivo |
|---|---|---|
| `owner, team` | No existe en frontmatter | Obligatorio si `vault_scope=enterprise` |
| `classification` | No existe | `public/internal/confidential` |
| `retention_days` | No existe | Opcional, con politica configurable |
| `audit_trail` | Solo en `records.jsonl` separado | Embebido en frontmatter |
| Promotion DocType-aware | Uniforme | Diferenciada por tipo (ADR completo, SESSION resumida, etc) |
| Namespacing por proyecto | No en routing | `{project_id}` en `enterprise_subfolder` |

---

## 6. Arquitectura Objetivo - Vista General

Detalle completo en [`architecture.md`](architecture.md).

Las seis capas:

```text
+---------------------------------------------------------+
| Capa 6: Recuperacion consciente del schema + telemetria |
|  filtros doc_type/status/tags · boost por intent ·       |
|  presenter agrupado · cortex_telemetry in-vault          |
+---------------------------------------------------------+
                            ^
+---------------------------------------------------------+
| Capa 5: Vectorizacion inteligente                        |
|  chunking H2/H3 · embedding con frontmatter · cache en   |
|  disco · sync por fingerprint · boost por tipo           |
+---------------------------------------------------------+
                            ^
+---------------------------------------------------------+
| Capa 4: Writers canonicos write_*_note                   |
|  firma simetrica · validacion · index incremental · audit|
|  trail enterprise                                        |
+---------------------------------------------------------+
                            ^
+---------------------------------------------------------+
| Capa 3: Routing canonico DOC_TYPE_ROUTING                |
|  subfolder · filename · template · writer · indexer ·    |
|  promotable · enterprise_subfolder                       |
+---------------------------------------------------------+
                            ^
+---------------------------------------------------------+
| Capa 2: Schema de frontmatter unificado                  |
|  obligatorios · opcionales · por tipo · enterprise       |
|  pydantic validator · schema_version                     |
+---------------------------------------------------------+
                            ^
+---------------------------------------------------------+
| Capa 1: DocType + dataclasses canonicas                  |
|  Enum cerrado · 12 tipos MVP · campos tipados            |
+---------------------------------------------------------+
```

Detalle de cada capa en `architecture.md`.

---

## 7. DocType - Lista Cerrada MVP

12 tipos. La lista es cerrada para MVP; cualquier extension requiere ADR.

| DocType | Carpeta | Naming | Indexador | Promotable |
|---|---|---|---|---|
| `SESSION` | `sessions/` | `YYYY-MM-DD_{session_id}_{slug}.md` | auto | parcial (resumen) |
| `HANDOFF` | `handoffs/` | `YYYY-MM-DD_{slug}.md` | auto | no |
| `SPEC` | `specs/` | `YYYY-MM-DD_{slug}.md` | auto | si |
| `ADR` | `decisions/` | `ADR-{number:03d}-{slug}.md` | auto | si (completo) |
| `DECISION` | `decisions/` | `DEC-{date}-{slug}.md` | auto | si |
| `INCIDENT` | `incidents/` | `INC-{number:03d}-{date}-{slug}.md` | auto | si si severity >= medium |
| `POSTMORTEM` | `postmortems/` | `PM-{incident_number}-{slug}.md` | auto | si (siempre) |
| `RUNBOOK` | `runbooks/` | `RB-{slug}.md` | auto | si con review |
| `ARCHITECTURE` | `architecture/` | `{slug}.md` | auto | si |
| `CHANGELOG` | `changelog/` | `{version}.md` | auto | si |
| `HU` | `hu/` | `HU-{external_id}.md` | auto | no |
| `GLOSSARY` | `glossary/` | `{term-slug}.md` | auto | si |

Notas:
- `decisions/` aloja tanto ADR como DECISION (mismo subfolder, distinto prefijo).
- `CHANGELOG` con un archivo por release (`v1.2.3.md`), no un archivo monolitico.
- `GLOSSARY` reemplaza `CONTEXT.md` monolitico por entradas atomicas (cada termino una nota).
- `HANDOFF` se separa de `SESSION` porque su contrato es distinto (no cierra trabajo, abre el proximo).

---

## 8. Schema de Frontmatter - Resumen

Detalle completo en [`frontmatter-schema.md`](frontmatter-schema.md).

### 8.1 Campos comunes a todos los tipos

```yaml
schema_version: 1
doc_type: <DocType>                # OBLIGATORIO - clave de routing
title: <str>
created_at: <ISO datetime>
updated_at: <ISO datetime>
tags: [<str>...]
status: <status valido por tipo>
links: [<wiki-link>...]            # explicitos, no inferidos
vault_scope: local | enterprise
fingerprint: <sha256 contenido>    # para sync y dedup
```

### 8.2 Campos enterprise (obligatorios si `vault_scope=enterprise`)

```yaml
owner: <email>
team: <slug>
classification: public | internal | confidential
retention_days: <int>              # 0 = sin retencion
audit_trail:
  - { actor, action, timestamp, reason }
```

### 8.3 Campos por tipo (ejemplos)

```yaml
# ADR
adr_number: 7
supersedes: [ADR-003]
superseded_by: null
alternatives_considered: [opcion-a, opcion-b]
acceptance_criteria_met: true

# INCIDENT
severity: low | medium | high | critical
opened_at: <ISO>
closed_at: <ISO> | null
root_cause_id: <postmortem-path> | null
affected_services: [auth, billing]

# RUNBOOK
runbook_kind: deploy | rollback | incident-response | data-migration
last_verified_at: <ISO>
applies_to: [service-a, service-b]
estimated_duration_minutes: <int>

# SESSION
pr: <url>
branch: <str>
commit: <sha>
cortex_telemetry: { ... }  # ver Capa 6
```

---

## 9. Plan por Fases

13 fases ordenadas por dependencia y riesgo. Cada fase tiene un README propio en `fase-NN-tema/`.

| # | Fase | Riesgo | Esfuerzo | Depende de |
|---|---|---|---|---|
| 00 | [Preparacion](fase-00-preparacion/README.md) | bajo | 0.5 dia | - |
| 01 | [DocType y Schema](fase-01-doctype-y-schema/README.md) | bajo | 1.5 dias | 00 |
| 02 | [Routing Table](fase-02-routing-table/README.md) | bajo | 0.5 dia | 01 |
| 03 | [Writers Canonicos Nuevos](fase-03-writers-canonicos/README.md) | medio | 2.5 dias | 01, 02 |
| 04 | [Migrar Writers Existentes](fase-04-migrar-writers-existentes/README.md) | medio | 1.5 dias | 01, 02, 03 |
| 05 | [Telemetria In-Vault](fase-05-telemetria-in-vault/README.md) | bajo | 1 dia | 04 |
| 06 | [Vector Persistence](fase-06-vector-persistence/README.md) | medio | 1.5 dias | - |
| 07 | [Chunking](fase-07-chunking/README.md) | alto | 2.5 dias | 06 |
| 08 | [Retrieval Filters](fase-08-retrieval-filters/README.md) | medio | 2 dias | 01, 07 |
| 09 | [Webgraph Update](fase-09-webgraph-update/README.md) | medio | 1 dia | 01, 02 |
| 10 | [Enterprise Extensions](fase-10-enterprise-extensions/README.md) | alto | 2 dias | 01-08 |
| 11 | [Migration y Backfill](fase-11-migration-y-backfill/README.md) | alto | 1.5 dias | 01-04 |
| 12 | [Cleanup](fase-12-cleanup/README.md) | bajo | 0.5 dia | 11 |

**Total estimado:** ~18 dias persona. Ejecutable secuencialmente o por bloques paralelos (00-04 son secuenciales; 05-07 pueden paralelizar; 08-09 dependen de 07; 10-12 al final).

---

## 10. Documentos Transversales

| Documento | Proposito |
|---|---|
| [`architecture.md`](architecture.md) | Las 6 capas en detalle con diagramas |
| [`gap-analysis.md`](gap-analysis.md) | Estado actual con paths/lineas vs objetivo |
| [`data-model.md`](data-model.md) | Enum DocType, dataclasses, pydantic models |
| [`frontmatter-schema.md`](frontmatter-schema.md) | Schema completo con todos los campos |
| [`routing-table.md`](routing-table.md) | DOC_TYPE_ROUTING completa |
| [`templates-reference.md`](templates-reference.md) | Templates Jinja por DocType |
| [`vectorization-design.md`](vectorization-design.md) | Chunking, persistencia, embedding strategy |
| [`retrieval-design.md`](retrieval-design.md) | Filtros estructurales, boost, presenter |
| [`enterprise-extensions.md`](enterprise-extensions.md) | Como enterprise consume cada capa |
| [`metrics.md`](metrics.md) | Metricas de excelencia |
| [`testing-strategy.md`](testing-strategy.md) | Estrategia de tests por capa |
| [`migration-guide.md`](migration-guide.md) | Plan de migracion del vault actual |

---

## 11. Riesgos y Mitigaciones

| Riesgo | Impacto | Mitigacion |
|---|---|---|
| Cambio del frontmatter rompe notas existentes | alto | Backfill idempotente (Fase 11), schema_version permite coexistir |
| Chunking degrada precision para notas cortas | medio | Skip chunking si nota < 500 palabras |
| Cache de vectores se corrompe | medio | Fallback a recalculo; checksum del cache |
| Filtros en enricher reducen coverage | medio | Filtros opt-in con default `None` |
| DocType cerrado no contempla casos | medio | Lista revisable por ADR; HU general como escape valve |
| Templates Jinja agregan dependencia | bajo | Jinja2 ya esta en deps transitivas (chromadb) |
| Migracion del vault destruye campos | alto | Backfill preserva campos legacy; reporte de cambios |
| Tests existentes rompen por nuevo schema | alto | Migracion incremental; tests existentes se actualizan en mismo PR |
| Enterprise extensions exigen owner/team que no hay | alto | Default a `unknown`; warning en setup enterprise |
| Performance de vault sync con chunking | medio | Batch embedding; chunking solo si nota > threshold |
| Doble version del documenter persiste | medio | Fase 12 elimina legacy |
| Webgraph rompe por nodos sin doc_type | medio | Fallback a `UNKNOWN` con color gris |

---

## 12. Decisiones Iniciales

1. **DocType es Enum cerrado, lista de 12 en MVP.** Cualquier extension requiere ADR.
2. **Templates en `cortex/documentation/templates/*.md.j2`.** Jinja2 como engine.
3. **Schemas con pydantic v2.** Misma libreria que el resto del proyecto.
4. **Cache de vectores en `.cortex/vectors/`.** Un archivo por hash de contenido o un binario unico (ver `vectorization-design.md`).
5. **Chunking por H2/H3 con overlap configurable.** Default: H2 boundaries, sin overlap, skip si nota < 500 palabras.
6. **Telemetria in-vault opt-in con default ON para vault local.** Default OFF para enterprise (privacidad).
7. **No introducir nuevas dependencias.** Todo construido sobre pydantic + Jinja2 (ya en deps).
8. **Backfill idempotente con dry-run.** Comando `cortex docs migrate --dry-run` muestra diffs sin escribir.
9. **Legacy documenter se elimina en Fase 12, no antes.** Coexistencia durante migracion.
10. **Test coverage por fase >= 90% del codigo nuevo.** Sin merge si no.

---

## 13. Gate Global de Salida

La iniciativa completa esta cerrada cuando:

1. `pytest tests/unit/documentation tests/unit/context_enricher tests/unit/semantic tests/unit/enterprise tests/integration/documentation` pasa al 100%.
2. `cortex docs validate` (nuevo comando, Fase 11) reporta 0 notas con drift de schema en el vault local de Cortex.
3. `cortex memory-report` muestra `cortex_telemetry` poblado en >= 5 sesiones reales tras migracion.
4. Carpetas muertas eliminadas o pobladas con al menos un documento real (no stub).
5. Webgraph muestra nodos coloreados por `doc_type` con leyenda visible.
6. Setup enterprise con preset `regulated-organization` valida que toda nota nueva tenga `owner, team, classification, retention_days`.
7. Documento `REALIZACION.md` en cada subcarpeta de fase con decisiones, archivos modificados, tests ejecutados y desviaciones.
8. Eliminacion de la version legacy del documenter (`cortex-pi/.pi/agents/cortex-documenter.md`).

---

## 14. Nota Final para Agentes Implementadores

Si sos un agente IA leyendo este plan para implementar:

1. **No improvises.** Usa los modelos exactos definidos en `data-model.md` y `frontmatter-schema.md`. No inventes campos.
2. **No saltees tests.** Cada fase tiene gate de salida con tests; sin tests pasando, la fase no esta completa.
3. **No toques `VaultReader.create_note()` ni `VaultReader.update_note()`** salvo lo necesario para chunking (Fase 7). Mantene la API publica.
4. **No toques el motor de busqueda** (`HybridSearch`, RRF, intent detector). Solo agrega filtros como argumentos opcionales.
5. **Usa `WorkspaceLayout`** para resolver paths. No hardcodees `vault/`, `.cortex/`, `.memory/`.
6. **Cada archivo nuevo debe tener test unitario correspondiente.**
7. **Schema es ley.** Si no valida, falla. Sin defaults silenciosos.
8. **Templates van en `.md.j2`,** no inline en Python.
9. **Migracion es idempotente y con dry-run obligatorio.** Re-ejecutar no rompe.
10. **Si algo no esta claro, pregunta antes de asumir.** Documentar bien define si Cortex sirve o es ruido.

---

## 15. Referencias Cruzadas

- **Plan original que origina esta iniciativa:** conversacion 2026-05-14 sobre carpetas muertas y telemetria sync_ticket.
- **Propuesta Enterprise relacionada:** `docs/enterprise/arch/PROPOSAL-Git-Like-Distributed-Vault-Enterprise.md` (alineamos Fase 1 pero no implementamos Fases 2-4).
- **BusinessSignal:** `docs/BusinessSignal/plan/README.md` (telemetria in-vault de Fase 05 alimenta a BusinessSignal Fase 02).
- **Autopilot:** `docs/autopilot/README.md` (writers canonicos consumidos por autopilot session writer).
- **Manifiesto Enterprise:** `docs/enterprise/MANIFIESTO-CORTEX-ENTERPRISE.md` (campos de gobierno alineados).
