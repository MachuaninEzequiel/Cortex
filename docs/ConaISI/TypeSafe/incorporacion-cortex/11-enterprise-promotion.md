# Enterprise: promoción de conocimiento

Módulos: `cortex/enterprise/{knowledge_promotion,promotion_doctype,governance,retrieval_service}.py`, `cortex-enterprise`, CLI `promote-knowledge`, `review-knowledge`, Brain-app `org_memory.rs` + `OrgMemoryModal`.

MCP **no** expone promote (no está en `tools_catalog.rs`). Queda en CLI/UI. No agregar tool MCP en el primer corte.

## Qué es determinista y se queda

- `assert_can_promote` / `assert_can_review` / `ADMIN_TEAM` / `classification_visible_to`. ACL.
- `RouteSpec.promotion_mode`: `as-is` | `summarize` | `review-required` según DocType.
- Fingerprint markdown, frontmatter, dest path, `status: draft`.
- Retention scan / archive (`maintenance.py`): fechas → código, no Jev.
- `RetrievalScope` local|enterprise|all.

`summarize` de SESSION hoy: digest por split H2 (`_summarize_session`). Eso es generación ligera. Jev no la reemplaza. Si algún día se quiere mejor digest: summarizer LLM, no Jev.

## Hueco: ¿esto es conocimiento de org o ruido de una sesión?

`PromotionRulesEngine.is_promotable` y `discover_candidates` son estructurales (doc-type, path, reglas). No preguntan:

- ¿Es generalizable fuera del repo de origen?
- ¿Duplica un ADR/spec enterprise ya `accepted`?
- ¿La clasificación (internal/confidential) que lleva es coherente con el cuerpo?
- ¿El humano debería verlo sí o sí?

## Un call por candidato (candidatos ya descubiertos por código)

State:

```json
{
  "candidate": {"path": "...", "doc_type": "adr", "title": "...", "body": "<recortado>"},
  "org": {"name": "...", "existing_titles": ["ADR-12 ...", "Runbook deploy ..."]},
  "classification_claimed": "internal"
}
```

No mandar el enterprise vault entero. `existing_titles` es un índice. Si hay sospecha de duplicado, **segunda** call con el body del duplicado potencial (dependencia real: fetch).

Questions:

```text
Noul org_knowledge
  "Is this note reusable organizational knowledge (a decision, runbook, spec, incident lesson), not a session diary or a local how-to?"

Noul duplicate_of_listed
  "Does this note duplicate one of org.existing_titles rather than add a new decision?"

Choice classification
  public, internal, confidential
  (solo las allowed_classifications_for el actor — filtrar en código antes)

Score quality
  0: Fragment, personal scratch, or empty procedure
  1: Useful locally, thin as org knowledge
  2: Clear, scoped, and citable by another team

Choice disposition
  auto_promote, send_to_review, reject
```

Código (governance gana siempre):

```text
si el actor no puede promote → error ACL, sin Jev
si disposition.confidence < 0.6 o org_knowledge ∈ (0.4, 0.6) → send_to_review
si duplicate alto → send_to_review (no auto-merge; entity alignment cookbook: nivel "curator")
si classification.choice != claimed y confidence alta → override al más restrictivo y review
si auto_promote y org_knowledge >= 0.7 y quality.score >= 1.5 y mode != review-required → apply_promotion
si mode == review-required → draft, Jev no salta el modo
```

Entity alignment cookbook: tres niveles de Score = merge / unlinked / curator. Acá los tres dispositions son el mismo truco: **el nivel es la acción**, no un threshold escondido. Se puede hacer con Choice `disposition` (más limpio, no hay orden) y usar Score `quality` aparte.

## Review queue

`review-knowledge pending|approve|reject` se queda humano. TypeSafe puede **ordenar** la cola (quality × 1-duplicate × org_knowledge) para que el reviewer vea primero lo dudoso o lo valioso. No auto-reject en v1.

Brain-app approve/reject: igual. Jev no clickea Approve.

## Mejora

Hoy promote copia + inyecta frontmatter. El riesgo enterprise es **contaminar el vault org** con diarios de sesión. Un Noul `org_knowledge` + `review-required` por default cuando hay duda es exactamente confidence-gated routing de alta stakes (como `approve_transfer` > 0.9). El vault org es el store que alimenta a todos los equipos: suciedad acá es suciedad multiplicada por N proyectos (federación webgraph / `workspace.yaml`).
