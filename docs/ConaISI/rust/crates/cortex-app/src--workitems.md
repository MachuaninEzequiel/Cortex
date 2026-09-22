# src/workitems.rs

## Qué tiene adentro

Puerto workitems (P12A-2).

`WorkItemSource::Jira` only. `WorkItemKind`: story/task/bug/epic/incident/other (`parse` fallback other).

`TrackedItem`. Traits: `WorkItemProvider`, `SemanticIndexer`, `EpisodicSink`. `EpisodicMemoryRequest`. `LiveSemanticIndexer` (sobre `SemanticIndex`), `LiveEpisodicSink` (sobre `NativeEpisodicStore`).

`WorkItemService`: import/get/list/has_provider. Writer `cortex_setup::writers::build_note("hu")`. Filename canónico `HU-{external_id}.md`, fallback slug legacy. Idempotencia por fingerprint; contenido distinto → mensaje `DuplicateDocumentError`. Reloj `now` explícito. `resolve_safe` para paths.

Errores `Result<String>` con textos Python como contrato.

## Para qué sirve

Importar tickets (Jira) al vault como notas HU e indexarlas.

## Relaciones

### Recibe de

- Provider Jira (trait), `cortex-setup::build_note`, vault path, episodic/semantic live adapters.

### Envía a

- Archivos `vault/hu/HU-*.md`, índice semántico, store episódico; example `p12a2_check`.

### Notas de implementación observadas en el código

Solo fuente Jira read-only hoy.
