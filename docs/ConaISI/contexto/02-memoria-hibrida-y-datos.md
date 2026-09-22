# Contexto: memoria híbrida y flujo de datos

## Las dos memorias

### Episódica

Python: `EpisodicMemoryStore` (`cortex/episodic/memory_store.py`) sobre Chroma. Modelo `MemoryEntry` (`cortex/models.py`): `id`, `content`, `memory_type`, `tags`, `files`, `timestamp`, `metadata`, `confidence` ∈ {verified, asserted, contradicted, None}.

Rust: `cortex-app/src/episodic/` persiste JSONL. `AgentMemory.remember()` (Python) y `cortex remember` (ambos CLIs) son las entradas de escritura. Metadata de runtime (`project_id`, `branch`, `repo`, org si hay enterprise) se mezcla en cada alta (`core.py`).

Tipos de memoria en el enum `MemoryType`: general, session, hu, adr, incident, changelog, security, pr_summary, ci_failure, conversation.

### Semántica

Markdown tipo Obsidian. `VaultReader` parsea título, contenido, `[[wiki-links]]`, `#tags`, frontmatter. Chunking por sección (`semantic/chunker.py` / `cortex-app/src/semantic/chunker.rs`). El hit semántico puede traer `matched_chunk_id` y `matched_section_title`.

El vault vive en `semantic.vault_path` resuelto contra `workspace_root`. En layout nuevo eso es `.cortex/vault/`.

Tipos de documento (MCP `DOC_TYPES_SORTED` y schemas Python): adr, architecture, changelog, decision, design, glossary, handoff, hu, incident, postmortem, runbook, session, spec, …

### Fusión (RRF)

`HybridSearch.search()`:

1. Rankea cada fuente por separado (embeddings o keyword).
2. Score fusionado: `Σ weight / (k + rank)` con `_RRF_K = 60`.
3. Una lista `unified_hits`.

Si `adaptive_weights=True` (default), `QueryIntentDetector` clasifica la query:

- intent episódico → `episodic_weight ×2`, `semantic_weight ×0.6`
- intent semántico → al revés
- mixed → pesos base

`RetrievalResult.to_prompt()` serializa a texto inyectable en un LLM, truncado a `max_chars` (default 4000).

Rust porta esto en `cortex-app/src/context/hybrid.rs` + `intent.rs`. El CLI nativo `search`/`context` pasa por `cortex_cli::memory_cmds`.

## Embeddings

Config (`CortexConfig` + `config.yaml` de este repo):

- Legacy: `episodic.embedding_model` + `embedding_backend` (`onnx|local|openai|fastembed`).
- Nuevo bloque `embedding:` gana si está configurado (`is_configured()`). Warning si ambos están custom.
- `language_detection: heuristic` + `per_language`. En este `config.yaml`: EN → MiniLM onnx, ES → e5-large fastembed.

Factory Python: `cortex.embedders`. Nativo: `cortex-embed` (ONNX, max 256 tokens, mean-pool, L2). Store nativo: un archivo append-only `vectors.v3.bin` (PUT tag=1, TOMBSTONE tag=2, compact() recupera huecos). Fingerprints los calcula el caller; el store los trata como claves opacas.

## Context enricher

Capa encima del retriever (`cortex/context_enricher`, `cortex-app/src/context/`). Estrategias (config): topic, files, keywords, pr_title, graph_expansion. Presupuesto `max_items`/`max_chars`. Boosts: multi-match, co-occurrence. Observer + telemetry JSONL. Presenter arma el bloque que se inyecta.

`AgentMemory.enrich()` es la fachada Python. MCP `cortex_context` y CLI `cortex context` la disparan. Filtros estructurales (`doc_type`, `status`, `tag`, `max_age_days`, `strict`) desvían `cortex_search` del RRF crudo al enricher (mismo comentario en `tools_catalog.rs`).

## Webgraph

Grafo de notas + recuerdos.

Modos en `WEBGRAPH_MODES`: `"semantic" | "episodic" | "hybrid"`.

Construcción: `SemanticSource` / `EpisodicSource` → `RelationBuilder` (wiki-links, tags, vecinos coseno O(n²) con umbral y `max_edges_per_node`) → `GraphBuilder` → `WebGraphSnapshot` (nodos, edges, stats). Cache. Federación de varios proyectos vía `workspace.yaml`.

Python: Flask (`cortex/webgraph/server.py`) + template/static. Rust: axum (`cortex-webgraph-server/src/server.rs`). CLI: `cortex webgraph serve|export|doctor`. Brain tool `webgraph.serve` es SAFE_ACTION (spawn detached).

Vecinos semánticos nativos: `cortex_core::webgraph::semantic_neighbor_pairs` (rayon, orden de emisión igual al Python).

## Enterprise overlay

Si existe org config, `AgentMemory.retrieve` puede cambiar el scope default (`local|enterprise|all`). `EnterpriseRetrievalService` une vault local + enterprise + episódica con governance de clasificación. Promoción: drafts → review → vault-enterprise. Doctor y `memory-report` leen ese estado.
