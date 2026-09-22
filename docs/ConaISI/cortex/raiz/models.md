# cortex/models.py

## Qué tiene adentro

- **407 líneas.** Modelos Pydantic compartidos por todo el paquete. Cero imports de otros módulos `cortex.*`.
- **Memoria:** `MemoryType` (enum de categorías episódicas), `MemoryEntry` (id `mem_<8 hex>`, content, tags, files, timestamp UTC, metadata, `confidence` tri-estado `verified|asserted|contradicted|None`).
- **Semántica:** `SemanticDocument` (path, title, content, wiki-links, tags, score, origen local/enterprise, chunk match).
- **Retrieval:** `EpisodicHit`, `UnifiedHit` (fuente episodic|semantic + score RRF + `display_title/content/path`), `RetrievalResult` (`to_prompt` hasta `max_chars`).
- **PR / docs:** `PRContext` (metadata de PR + `hu_references`, `has_db_changes`, `has_api_changes`, `has_adr_label`), `GeneratedDoc` (tipo → subfolder del vault).
- **Enricher:** `WorkContext`, `EnrichedItem`, `EnrichedContext` (`to_prompt_format` compact/full).

## Para qué sirve

Contrato de datos entre stores, retriever, enricher, servicios y CLI. Es el vocabulario compartido: nadie más define `UnifiedHit` / `MemoryEntry`.

## Relaciones

### Recibe de

- Solo stdlib + `pydantic`. No importa Cortex.

### Envía a

Importado por (AST): `cortex.__init__`, `core`, `episodic.memory_store`, `semantic.vault_reader`, `semantic.markdown_parser`, `retrieval.hybrid_search`, `enterprise.retrieval_service`, `enterprise.sources`, `services.note_service`, `services.pr_service`, `services.spec_service`, `workitems.service`, `mcp.tools.search`, `context_enricher.{enricher,async_enricher,filters}`, `doc_generator`, `pr_capture`.

### Notas de implementación observadas en el código

- `confidence` es opcional para recuerdos pre-0.5.0.
- `RetrievalResult.to_prompt` prefiere `unified_hits` (RRF); si está vacío cae a listas separadas.
- `PRContext.hu_references` usa regex Jira-like (`ABC-123`), `HU-n`, user story y `#n`.

---
Fuente: lectura de `cortex/models.py`. No se usó documentación previa.
