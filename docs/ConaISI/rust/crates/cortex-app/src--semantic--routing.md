# src/semantic/routing.rs

## Qué tiene adentro

`DocType` (13 valores: session, handoff, spec, adr, decision, incident, postmortem, runbook, architecture, changelog, hu, glossary, design) con `.value()`.

`Route { chunking_enabled, min_words, boundary_h3 }` — tabla corta de retrieval. Spec/ADR/incident/postmortem/runbook/architecture/changelog/design chunked; session/handoff/decision/hu/glossary no. ADR min_words 400, runbook 400, resto chunked 500. `boundary_h3` siempre false en esta tabla.

`doc_type_from_rel`: primer directorio + archivo. `decisions/ADR-*` → Adr. Raíz o dir desconocido → None (caller usa Glossary).

`RouteSpec` completo (subfolder, filename_template, template_path absoluto a `cortex/documentation/templates/{value}.md.j2` vía 3 ancestros de `CARGO_MANIFEST_DIR`, writer, indexer, promotable, promotion_mode, enterprise_subfolder, retrieval_boost_per_intent, chunking_*, webgraph color/shape, requires_review, auto_expire_days).

`route_spec`, `list_all_routes`, `parse_doc_type`, `DOC_TYPE_VALID_SLUGS`.

## Para qué sirve

Decidir chunking y metadatos canónicos por tipo de nota. CLI `cortex docs routing-table` (citado en el módulo) serializa `RouteSpec`.

## Relaciones

### Recibe de

- `rel` path del vault; enum DocType.

### Envía a

- `chunker`/`chunks_for_doc`; `doc_intent::retrieval_boost`; writers/CLI.

### Notas de implementación observadas en el código

`Route.min_words` de retrieval (Spec 500) y `RouteSpec.chunking_min_words` (Session 500 aunque chunking_enabled false) no son el mismo campo. `template_path` apunta al árbol Python `cortex/documentation/templates`.
