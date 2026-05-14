# Frontmatter Schema - Especificacion Completa

**Documento:** schema canonico de frontmatter YAML para todos los tipos de documento
**Audiencia:** implementadores, autores de notas, agentes
**Estado:** especificacion normativa

---

## 1. Principios

1. **Todo frontmatter debe declarar `doc_type`.** Sin excepciones. Sin este campo, la nota no se persiste.
2. **`schema_version: 1` siempre.** Permite migracion futura sin romper notas viejas.
3. **`fingerprint` es derivado.** El writer lo genera; el autor no lo escribe.
4. **`updated_at >= created_at`.** Validacion al guardar.
5. **`vault_scope` es ortogonal al `doc_type`.** Cualquier tipo puede ser local o enterprise.
6. **Campos especificos por tipo en posicion fija.** No mezclar; van despues de los comunes.
7. **Listas vacias se escriben como `[]`,** no se omiten. Esto evita ambiguidad en YAML.

---

## 2. Campos comunes (todos los tipos)

```yaml
---
schema_version: 1                    # int, obligatorio
doc_type: <session|handoff|...>      # DocType, obligatorio
title: <string>                       # obligatorio
created_at: 2026-05-14T10:23:45Z      # ISO 8601 con TZ
updated_at: 2026-05-14T11:45:12Z      # ISO 8601 con TZ
tags: [tag-a, tag-b]                  # lista, puede ser []
status: <status valido por tipo>      # string, obligatorio
links: ["[[other-note]]", "[[ADR-003]]"]   # lista de wiki-links
vault_scope: local                    # "local" | "enterprise"
fingerprint: 7a8f9c...               # sha256 hex del body
---
```

### Reglas

| Campo | Tipo | Obligatorio | Default | Validacion |
|---|---|---|---|---|
| `schema_version` | int | si | 1 | == 1 (otros valores reservados) |
| `doc_type` | str (DocType) | si | - | Debe estar en `DocType` enum |
| `title` | str | si | - | `len > 0` |
| `created_at` | datetime ISO | si | now() | Con timezone |
| `updated_at` | datetime ISO | si | now() | `>= created_at` |
| `tags` | list[str] | no | `[]` | Cada tag es slug lowercase |
| `status` | str | si | - | Debe estar en `VALID_STATUSES[doc_type]` |
| `links` | list[str] | no | `[]` | Cada link tiene formato `[[<name>]]` |
| `vault_scope` | str | si | `"local"` | `"local"` o `"enterprise"` |
| `fingerprint` | str | si | derivado | sha256 hex (64 chars) |

---

## 3. Campos enterprise (obligatorios si `vault_scope=enterprise`)

```yaml
owner: ezequiel@cortex.ai             # email
team: cortex-core                      # slug
classification: internal               # public | internal | confidential
retention_days: 365                    # int, 0 = sin retencion
audit_trail:
  - actor: ezequiel@cortex.ai
    action: created
    timestamp: 2026-05-14T10:23:45Z
    reason: null
  - actor: review-bot
    action: reviewed
    timestamp: 2026-05-14T11:00:00Z
    reason: "Approved by team-lead"
```

### Reglas

| Campo | Tipo | Validacion |
|---|---|---|
| `owner` | str email | Regex email valido |
| `team` | str slug | Solo `[a-z0-9-]` |
| `classification` | str | uno de los 3 valores |
| `retention_days` | int | `>= 0` |
| `audit_trail` | list[AuditEvent] | append-only, jamas se borra |

### AuditEvent

```yaml
- actor: <email o agent-id>
  action: created | updated | promoted | reviewed | rejected | classified | retention-updated
  timestamp: <ISO con TZ>
  reason: <string opcional>
```

---

## 4. Campos por DocType

### 4.1 SESSION

```yaml
session_id: a1b2c3d4e5f6              # 12 hex chars, generado al inicio
pr: "https://github.com/.../pull/42"  # url o null
branch: feat/canonical-docs           # nombre rama
commit: a1b2c3d                        # SHA corto

cortex_telemetry:                     # opcional, llenado al cierre
  enricher_run_id: uuid
  context_items_offered: 8
  context_items_used: 3
  context_hit_rate: 0.375
  context_by_type:
    adr: 1
    runbook: 1
    session: 1
  context_by_strategy:
    topic_search: 2
    entity_search: 1
  context_by_scope:
    local: 3
    enterprise: 0
  enriched_score_p50: 0.42
  enriched_score_p95: 0.71
  enricher_latency_ms: 187
  filters_applied:
    doc_types: ["adr", "runbook"]
    vault_scope: "local"
```

Status validos: `draft | completed | handoff | fallback | auto-draft`.

### 4.2 HANDOFF

```yaml
parent_session_id: a1b2c3d4e5f6       # session que origino el handoff
```

Status validos: `open | consumed | stale`.

### 4.3 SPEC

```yaml
# Sin campos extra obligatorios; body lleva goal/requirements/etc
```

Status validos: `draft | approved | implementing | done | abandoned`.

### 4.4 ADR

```yaml
adr_number: 7                         # int, asignado al guardar
supersedes: [ADR-003]                 # lista de filenames (sin .md)
superseded_by: null                   # filename o null
alternatives_considered: ["opcion-a", "opcion-b"]
acceptance_criteria_met: true
```

Status validos: `proposed | accepted | superseded | rejected`.

### 4.5 DECISION

```yaml
# Sin campos extra obligatorios; body lleva context/decision/alternativa/razon
reversible_within_days: 7              # int, 0 = irreversible
```

Status validos: `active | reverted`.

### 4.6 INCIDENT

```yaml
incident_number: 12                    # int, asignado al guardar
severity: high                         # low | medium | high | critical
opened_at: 2026-05-14T08:00:00Z
closed_at: 2026-05-14T10:30:00Z       # null si abierto
affected_services: [auth, billing]
root_cause_postmortem: postmortems/PM-012-auth-token-expiry.md  # null si pendiente
```

Status validos: `open | mitigated | closed`.

### 4.7 POSTMORTEM

```yaml
incident_number: 12
incident_path: incidents/INC-012-2026-05-14-auth-down.md
severity: high                         # heredado del incidente
```

Status validos: `draft | published | actions-tracked | complete`.

### 4.8 RUNBOOK

```yaml
runbook_kind: deploy                   # deploy | rollback | incident-response | data-migration | operational
applies_to: [auth-service, api-gateway]
estimated_duration_minutes: 30
last_verified_at: 2026-04-30T15:00:00Z
```

Status validos: `draft | verified | deprecated`.

### 4.9 ARCHITECTURE

```yaml
related_adrs: [ADR-001, ADR-007]      # ADRs que justifican este diseno
```

Status validos: `draft | current | deprecated`.

### 4.10 CHANGELOG

```yaml
version: v1.2.3                        # semver
release_date: 2026-05-14T00:00:00Z
```

Status validos: `unreleased | released`.

### 4.11 HU

```yaml
external_id: PROJ-1234                # ID en sistema externo
source: linear                         # jira | linear | github | etc
kind: story                            # story | task | bug | epic
assignee: ezequiel@cortex.ai
external_url: https://linear.app/...
synced_at: 2026-05-14T10:00:00Z
```

Status validos: `backlog | in-progress | done | cancelled`.

### 4.12 GLOSSARY

```yaml
term: "Ubiquitous Language"            # canonical name
domain: ddd                            # opcional
related_terms: ["Bounded Context", "Aggregate"]
```

Status validos: `draft | canonical | deprecated`.

---

## 5. Ejemplos completos

### 5.1 ADR local

```yaml
---
schema_version: 1
doc_type: adr
title: "ADR-007: Use ONNX backend for embeddings"
created_at: 2026-05-14T10:23:45Z
updated_at: 2026-05-14T10:23:45Z
tags: [embedding, performance, onnx]
status: accepted
links: ["[[architecture-retrieval]]", "[[ADR-001]]"]
vault_scope: local
fingerprint: 7a8f9c1234567890abcdef1234567890abcdef1234567890abcdef1234567890
adr_number: 7
supersedes: []
superseded_by: null
alternatives_considered: ["sentence-transformers nativo", "openai embeddings api"]
acceptance_criteria_met: true
---

## Context

...
```

### 5.2 ADR enterprise (con governance)

```yaml
---
schema_version: 1
doc_type: adr
title: "ADR-012: Adoptar GraphQL para API publica"
created_at: 2026-05-14T10:23:45Z
updated_at: 2026-05-14T11:00:00Z
tags: [api, graphql, public]
status: accepted
links: ["[[architecture-api-publica]]"]
vault_scope: enterprise
fingerprint: 9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c
owner: ezequiel@cortex.ai
team: api-team
classification: internal
retention_days: 2555  # 7 anios
audit_trail:
  - actor: ezequiel@cortex.ai
    action: created
    timestamp: 2026-05-14T10:23:45Z
    reason: null
  - actor: cto@cortex.ai
    action: reviewed
    timestamp: 2026-05-14T11:00:00Z
    reason: "Approved by CTO and API team lead"
adr_number: 12
supersedes: []
superseded_by: null
alternatives_considered: ["REST tradicional", "gRPC", "JSON-RPC"]
acceptance_criteria_met: true
---

## Context

...
```

### 5.3 Session con telemetria

```yaml
---
schema_version: 1
doc_type: session
title: "feat: implement write_adr_note canonical"
created_at: 2026-05-14T10:23:45Z
updated_at: 2026-05-14T12:30:00Z
tags: [documentation, writers, fase-03]
status: completed
links: ["[[ADR-007]]", "[[runbook-deploy-vault]]"]
vault_scope: local
fingerprint: 1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7a8b9c0d1e2f
session_id: c0ffee123456
pr: "https://github.com/cortex/cortex/pull/42"
branch: feature/canonical-docs
commit: a1b2c3d
cortex_telemetry:
  enricher_run_id: e7f8a9b0c1d2
  context_items_offered: 8
  context_items_used: 3
  context_hit_rate: 0.375
  context_by_type:
    adr: 1
    runbook: 1
    session: 1
  context_by_strategy:
    topic_search: 2
    entity_search: 1
  context_by_scope:
    local: 3
    enterprise: 0
  enriched_score_p50: 0.42
  enriched_score_p95: 0.71
  enricher_latency_ms: 187
  filters_applied:
    doc_types: ["adr", "runbook"]
    vault_scope: "local"
---

## Changes Made

...
```

---

## 6. Validacion: que rechaza el schema

| Caso | Resultado |
|---|---|
| Falta `doc_type` | SchemaValidationError("doc_type required") |
| `doc_type: "invalid"` | SchemaValidationError("unknown doc_type") |
| `vault_scope: enterprise` sin `owner` | SchemaValidationError("owner required for enterprise") |
| `status: "wrong-status"` | SchemaValidationError("invalid status for doc_type X") |
| `created_at` sin timezone | SchemaValidationError("created_at must have timezone") |
| `updated_at < created_at` | SchemaValidationError("updated_at must be >= created_at") |
| `fingerprint` con != 64 chars hex | SchemaValidationError("invalid fingerprint format") |
| Campo `doc_type` con tipo incorrecto | SchemaValidationError("doc_type must be string") |

---

## 7. Migracion de frontmatter legacy

Notas existentes con frontmatter heterogeneo necesitan backfill. Reglas:

1. **Inferir `doc_type` por carpeta:**
   - `sessions/` -> `SESSION`
   - `decisions/<file que empieza con ADR-*>` -> `ADR`
   - `decisions/<otro>` -> `DECISION`
   - `runbooks/` -> `RUNBOOK`
   - `incidents/` -> `INCIDENT`
   - `architecture/` y raiz con tag `architecture` -> `ARCHITECTURE`
   - `specs/` -> `SPEC`
   - `hu/` -> `HU`
   - `changelog/` -> `CHANGELOG`
   - Otros -> reportar warning, no migrar

2. **Mapear campos legacy:**
   - `date` -> `created_at` (con timezone UTC asumida).
   - Si no hay `updated_at`, copiar de `created_at`.
   - Si no hay `status`, default = primer status valido del tipo.
   - Si no hay `tags`, default = `[]`.
   - Si no hay `links`, parsear `[[wiki-links]]` del body y populate.

3. **Generar campos derivados:**
   - `fingerprint` = sha256 del body.
   - `schema_version` = 1.
   - `vault_scope` = `local` (enterprise requiere explicit migracion).

4. **Conservar campos legacy:**
   - Por compatibilidad, mantener campos viejos prefijados con `legacy_`:
     - `legacy_date: 2026-04-15`
     - `legacy_pr: "#42"` (si era el formato viejo)
   - Permite rollback sin perder datos.

Detalle de la utilidad de migracion en `migration-guide.md`.

---

## 8. Reglas de escritura del frontmatter

1. **YAML safe.** Usar `yaml.safe_dump` con `default_flow_style=False, allow_unicode=True`.
2. **Orden de campos:** comunes primero, enterprise despues, especificos por tipo al final.
3. **Sin comentarios YAML.** El frontmatter es maquina-legible; comentarios van en body.
4. **Indentacion 2 espacios.**
5. **Strings con ":" o caracteres especiales en quotes.**
6. **Datetime en ISO 8601 UTC.**

---

## 9. Discoverabilidad por agentes

El subagente documenter debe poder generar frontmatter valido. Para eso:

1. **`cortex docs schema <doc-type>`** imprime el schema completo del tipo.
2. **`cortex docs schema --all`** imprime todos los schemas.
3. **`cortex docs validate <path>`** valida un .md contra schema.
4. **`cortex docs scaffold <doc-type>`** crea un .md template con frontmatter pre-poblado.

Esto reduce friccion del documenter al escribir notas.
