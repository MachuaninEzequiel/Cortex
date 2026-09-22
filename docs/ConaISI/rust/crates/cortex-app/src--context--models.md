# src/context/models.rs

## Qué tiene adentro

`WorkContext`: source (`git_diff|pr|manual`), changed/new/deleted files, keywords, imports, function/class names, domain + confidence, search_queries (hasta 4), pr_title/body/labels. Helper `manual(...)`.

`EnrichedItem`: source, source_id, title, content, score, enriched_score, matched_by, files_mentioned, date, tags, doc_type, status, vault_scope, origin_project_id, matched_chunk_*.

`EnrichedBundle`: work, items, total_searches/raw_hits/chars, `within_budget_override`. `to_json` emite objeto con orden de claves fijo vía `pyjson::dumps_ascii` (contrato P7).

## Para qué sirve

Contrato JSON del enricher (`--json`).

## Relaciones

### Recibe de

- Observer / callers que arman WorkContext; enricher que llena items.

### Envía a

- `presenter`, `telemetry`, CLI.

### Notas de implementación observadas en el código

Floats del JSON pasan por `Pj::F64` (repr CPython). `within_budget` usa override o `total_chars <= max_chars`.
