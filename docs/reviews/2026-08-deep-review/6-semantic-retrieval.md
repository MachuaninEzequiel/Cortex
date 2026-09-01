# Revisión: Semantic / Retrieval / Embedders / Episodic / Security (Cortex)

Revisor: rev-semantic-retrieval · Scope: `cortex/semantic/**`, `cortex/retrieval/**`, `cortex/embedders/**`, `cortex/episodic/**`, `cortex/security/**` (~3.260 LOC). Solo lectura.

---

## 1. Propósito y arquitectura interna

### cortex/semantic — indexación y búsqueda vectorial del vault markdown

- **`chunker.py`** (288 l): `chunk_document()` divide contenido en `Chunk` (dataclass congelado) por boundary `"h2"` / `"h3"` / `"paragraph"`, con `min_words` (default 500) y `overlap_words`. Docs cortos o vacíos → un único chunk con `chunk_id == rel_path` (`_single_chunk`, L152-168). `Chunk.embedding_text` (L63-76) inyecta señal estructural: `"<doc_type> <tags> <section_title> <text>"`.
- **`markdown_parser.py`** (79 l): `MarkdownParser.parse()` → `SemanticDocument`: separa frontmatter YAML (regex `_FRONTMATTER_RE`, tolerante a YAMLError), extrae wiki-links Obsidian y hashtags inline, deduplica tags preservando orden.
- **`vault_reader.py`** (657 l): clase central `VaultReader`. Responsabilidades:
  - `sync()` (L86): re-indexa todo el vault; parsea, chunkifica según routing (`_chunks_for_doc` → `RouteSpec.chunking_*`), embebe en batch con cache, precomputa BM25 (IDF + avgdl).
  - `search()` (L151): búsqueda vectorial a nivel chunk con coseno puro-Python, agrega al doc padre por max-score, adjunta `matched_chunk_id` / `matched_section_title`; fallback BM25 si `use_embeddings=False`.
  - Escritura: `index_file()` (L502), `create_note()` (L565), `update_note()` (L625) — todas chunk-aware y cache-aware, con invalidación granular de cache (Item #4).
  - Helpers: `_embed_batch_with_cache()` (L282), `_purge_chunks_for_parent()` (L371), `_resolve_doc_type()` (L383, mapping duplicado de subcarpetas→DocType).
- **`vector_cache.py`** (442 l): `VectorCache` — cache persistente de vectores: `chunks.bin` (float32 contiguo) + `index.json` ({fingerprint SHA-256 del embedding_text → CacheEntry(offset,dim)}). Thread-safe por RLock (single-proceso). Invalidación por fingerprint, schema bump, `invalidate_chunks()`, `invalidate_by_chunk_id()`; auto-compacción por umbral (30%) y `compact()` atómico (tmp+rename).

### cortex/retrieval — fusión híbrida

- **`hybrid_search.py`** (252 l): `HybridSearch.search()` consulta episodic + semantic con over-fetching (`fetch_k = k*3`), y fusiona con RRF cross-source real: `score += w_source / (60 + rank)`. Con `adaptive_weights=True` (default) escala los pesos base por los multiplicadores del detector de intención. Devuelve `RetrievalResult` (hits por fuente + `unified_hits` fusionados).
- **`intent.py`** (174 l): `QueryIntentDetector` clasifica query en EPISODIC/SEMANTIC/MIXED con léxicos regex (6 señales episódicas, 5 semánticas). Pesos preset: EPISODIC (2.0, 0.6), SEMANTIC (0.6, 2.0), MIXED (1.0, 1.0). Singleton a nivel módulo en hybrid_search.py:491.

### cortex/embedders — backends de embedding (Strategy + Factory)

- **`base.py`**: `EmbedderProtocol` (`typing.Protocol`, runtime_checkable): `model_name`, `backend`, `embed`, `embed_batch`. `EmbeddingBackend = Literal["onnx","local","openai"]`.
- **`factory.py`**: `EmbedderFactory` con registry lazy (`module.Class` strings) → import diferido de dependencias pesadas. `UnsupportedBackendError` para backend desconocido.
- **`onnx.py`**: default. Envuelve `chromadb.ONNXMiniLM_L6_V2` con singleton class-level + double-checked locking (`_get_onnx_fn`, L152-173) — una sola carga por proceso. **`model_name` es ignorado** (informativo).
- **`local.py`**: sentence-transformers/PyTorch vía `lru_cache(maxsize=1)` por instancia. **`openai.py`**: API de embeddings; batch nativo; sin retry/rate-limit handling.

### cortex/episodic

- **`memory_store.py`** (471 l): `EpisodicMemoryStore` sobre ChromaDB persistente (HNSW cosine). CRUD + búsqueda vectorial (distancia coseno → score `1-d`) o keyword substring vía `where_document $contains`. Extracción de entidades por regex (`_extract_entities`, L112) que se serializa como campos booleanos `entity_<tipo>_<valor>` en metadata ChromaDB para filtrado directo (`_search_by_entity_where`) con fallback legacy a índice en memoria (`_entity_index`). Caches internos invalidados por `_cache_token`.
- **`embedder.py`** (171 l): wrapper legacy `Embedder` que delega ONNX a `OnnxEmbedder._get_onnx_fn()` (comparte singleton, bien) pero duplica la lógica local/openai.
- **`summarizer.py`** (114 l): compresión de logs a resumen vía OpenAI/Anthropic/Ollama; fallback a truncado de 300 chars si provider="none" o ante cualquier excepción.

### cortex/security

- **`paths.py`** (63 l): `resolve_safe(root, rel)` (rechaza absolutos, valida contención post-resolve → cubre `..` y symlinks) y `validate_under_root(path, root)`. `PathSecurityError(ValueError)`.

---

## 2. Flujo de datos / puntos de entrada y salida

Entradas principales al subsistema:

- **`cortex/core.py`** construye `EpisodicMemoryStore`, `VaultReader`, `Summarizer`, `HybridSearch` (core.py:255-274) e inyecta `semantic`/`episodic` en `SpecService`, `NoteService` (services/note_service.py llama `index_file` en note_service.py:183). `retrieve()` (core.py:399) delega a `HybridSearch.search()`; scope enterprise va por `EnterpriseRetrievalService` (envuelve MultiVaultReader sobre el mismo VaultReader).
- **`cortex/webgraph/semantic_source.py:73`** crea su propio `VaultReader` (proyección de docs a webgraph).
- **`cortex/cli/docs_vectorization.py:31`** instancia `VectorCache` directamente.

Salidas: `SemanticDocument`, `EpisodicHit`, `UnifiedHit`, `RetrievalResult` (todos en cortex/models.py); archivos: vault `.md`, `.cortex_index.json` (BM25 meta), `.cortex/vectors/{index.json,chunks.bin}`, directorio ChromaDB.

Dependencias externas dentro del scope: `cortex.documentation.{common,doc_type,inventory,routing}` (slugify, compute_fingerprint, classify_path, RouteSpec), `cortex.models`, `chromadb`, `numpy`.

---

## 3. Invariantes y decisiones de diseño

1. **Espacio vectorial único**: vault semántico usa el mismo embedder que episodic → RRF cross-source comparable (vault_reader.py:5-9).
2. **chunk_id estable**: `{rel_path}#{boundary_level}-{slug}`; single-chunk usa `rel_path` desnudo. La agregación chunk→padre es max-score (vault_reader.py:172-182).
3. **Cache key = fingerprint SHA-256 del embedding_text** — nunca del archivo completo: cambiar tags/título invalida solo lo afectado.
4. **BM25 queda a nivel documento** como fallback legacy ("legacy keyword fallback", vault_reader.py:117); no participa del ranking vectorial.
5. **VectorCache single-process, append-only + compactación**; atomicidad por tmp+rename en index.json y chunks.bin.
6. **ONNX model process-wide** (singleton class-level) — decisión explícita tras medir 5-8 cargas redundantes (episodic/embedder.py:102-114).
7. **Seguridad de paths centralizada**: toda escritura pasa por `resolve_safe`/`validate_under_root` (index_file:507, create_note:586/592, update_note:627).

---

## 4. Bugs potenciales (con evidencia)

1. **🔴 Colisión de chunk_id por slug duplicado**: dos secciones H2/H3 con mismo título slugeado producen el mismo `chunk_id` (chunker.py:181-182); en `sync()`/`index_file()` el dict `self._chunks[cid]`/`self._embeddings[cid]` sobrescribe el anterior (vault_reader.py:115, 538) → sección silenciosamente no indexada. Frecuente en docs con "## Decision"/"## Context" repetidos.
2. **🔴 VectorCache hardcodea VECTOR_DIM=384** (vector_cache.py:41) y `put()` lanza ValueError con otra forma (L226-229). Configurar backend openai (1536d) + vector_cache rompe. Peor aún: en `_embed_batch_with_cache` (vault_reader.py:308-317), si `put()` lanza a mitad del loop, el bloque `except` deja `results[idx]=None` para los índices restantes → se devuelven vectores `[]` → similitud coseno 0 → filtrados por `score <= 0` (vault_reader.py:177) → **búsqueda devuelve vacío sin ningún error logueado**.
3. **🟠 Cache sin identidad de modelo**: la clave es fingerprint del texto solamente; cambiar `embedding_model` reutiliza vectores obsoletos de otro modelo/dimensión (schema_version es manual, vector_cache.py:39). Contaminación silenciosa del ranking.
4. **🟠 `update_note` destruye el frontmatter** (vault_reader.py:630): escribe `new_content` crudo sobre todo el archivo → título/tags originales se pierden y el índice queda con doc re-parsed distinto al esperado. Además no llama `_save_index_meta()` (index_file sí, L559) → BM25 meta en disco desincronizada.
5. **🟠 Código muerto**: `max(len(self._index), 1)` sin asignar en `_bm25_search` (vault_reader.py:209); **`_load_index_meta()` (L454-466) nunca es llamada** en todo el repo — la persistencia de BM25 (`_save_index_meta`, L441) se escribe pero jamás se lee: I/O desperdiciado y feature muerta.
6. **🟠 Duplicación de yaml_dump_safe**: vault_reader.py:654 duplica `cortex.documentation.common.yaml_dump_safe` (common.py:65).
7. **🟡 `_resolve_doc_type` confuso/dead branch** (vault_reader.py:390-401): si `classify_path(..., Path(""))` retorna None, computa `parts` y no hace nada con ello; luego recalcula `parts` abajo. El mapping L406-423 duplica la tabla de inventory.classify_path → riesgo de drift.
8. **🟡 Overlap compuesto en chunks**: en `_split_with_pattern`/`_split_paragraphs`, el tail se toma de `chunks[-1].text`, que ya incluye su overlap heredado → el mismo texto puede repetirse >2 chunks (chunker.py:233-237, 269-272).
9. **🟡 Entidades episdicas: falsos positivos masivos y metadata explosiva**: patrón `(?:app\.)?(?:get|post|...)\(` (memory_store.py:133-135) matchea cualquier dict-access tipo `config.get("x")`; patrones `variable`/`constant` capturan casi todo. Cada entidad genera un campo booleano en metadata ChromaDB (`entity_<t>_<v>`, L309) → claves ilimitadas, colisiones tras normalización (`_entity_filter_key` colapsa valores distintos), y documentos con cientos de campos.
10. **🟡 Keyword search episódica débil**: `where_document $contains` es substring case-sensitive y score plano 1.0 (memory_store.py:195-208) → en RRF todos los hits keyword empatan en rank-quality.
11. **🟡 Búsqueda semántica O(N·384) en Python puro**: `_cosine_similarity` con listas (vault_reader.py:247-255) por cada chunk en cada query; los vectores viven como listas Python aunque el cache los tenga float32. Para vaults grandes esto domina la latencia.
12. **🟡 `delete_note` inexistente**: borrar un .md del vault deja entradas stale en `_index`/`_embeddings` hasta el próximo `sync()`; no hay API de remoción incremental.
13. **🟡 Summarizer**: `os.environ["OPENAI_API_KEY"]` → KeyError crudo (summarizer.py:74) vs mensaje amable en openai.py:282-287; URL Ollama hardcodeada localhost:11434 (L98).
14. **🟡 create_note edge cases**: title `"!!!"` → slug vacío → archivo `.md` (vault_reader.py:591); slug repetido sobrescribe nota existente silenciosamente (`write_text`).
15. **🟡 Intent detector inglés-only y threshold=1** (intent.py:122-123): una palabra ("api", "error") dispara pesos extremos 2.0/0.6; `confidence = ep/max(total,1)` es proporción bruta de señales, no probabilidad calibrada.
16. **🟡 `RetrievalResult.intent: object | None` con `exclude=True`** (models.py) — la intención detectada se excluye de la serialización; la promesa de observabilidad de hybrid_search.py:552 no se cumple fuera del objeto vivo.

## 5. Deudas y refactor

- **Doble stack de embedders**: `cortex/episodic/embedder.py::Embedder` duplica Onnx/Local/OpenAI ya existentes en `cortex/embedders/*`, define su propio `EmbeddingBackend` Literal (embedder.py:36 vs base.py:16), y su path OpenAI hace **un request HTTP por texto** en `embed_batch` (embedder.py:79 `[self._embed_openai(t) for t in texts]`) mientras `OpenAIEmbedder.embed_batch` usa batching nativo (openai.py:268). Consolidar: `Embedder` debería delegar 100% en `EmbedderFactory.create()`.
- **`VaultReader` hace demasiado** (657 l: parse+chunk+embed+cache+BM25+CRUD+persistencia). Extraer BM25 a un módulo propio y la capa de escritura a un `VaultWriter`; eliminar `_load_index_meta` o implementar su carga en cold-start.
- **Singletons ocultos**: `_intent_detector` module-level (hybrid_search.py:491) impide inyectar thresholds/config; `OnnxEmbedder._onnx_fn` class-level está bien documentado pero acopla tests.
- **VectorCache.put persiste index.json entero por vector** (L251) y `batch_put` llama put N veces → O(N²) en cold-start grande. Compact() abre el bin por vector (`_read_vector_at` por entry, L347-354) → O(N) file-opens.
- **Tokenización BM25 naive** (split por whitespace con puntuación pegada, vault_reader.py:239-242): "(error)" ≠ "error".

## 6. Preparación para un cambio grande — qué tocaría primero

1. **Antes de tocar nada**: corregir (2) — el fallo silencioso de dimensión/cache que devuelve resultados vacíos — y (1) chunk_id collision (agregar sufijo de posición: `#h2-slug-2`). Son los únicos bugs que corrompen resultados sin ruido.
2. **Fragilidad #1**: `VectorCache` asume MiniLM 384 y modelo fijo. Cualquier cambio de modelo/dimensión requiere: fingerprint salado con `model_name`, validación de dim en lectura, y schema_version derivada del modelo. Es el punto más frágil para migrar de all-MiniLM-L6-v2.
3. **Fragilidad #2**: consolidar embedders (borrar duplicación episodic/embedder.py) ANTES de agregar cualquier backend nuevo; hoy hay que mantener la lógica en dos lugares.
4. **Fragilidad #3**: `VaultReader` mezcla lectura/escritura/cache/BM25 — un cambio grande de retrieval (p.ej. reemplazar coseno-Python por numpy/FAISS, o subir BM25 a chunk-level) toca las 4 preocupaciones a la vez. Extraer `Bm25Index` primero.
5. Los tests existen y son buenos (unit+integration por fase: test_vector_cache_*, test_vault_reader_chunking, test_adaptive_rrf) — apoyarse en ellos; pero no cubren los bugs 1, 2, 4 ni el caso multi-modelo.
6. `security/paths.py` está sano y bien usado; no tocar salvo para sumar TOCTOU-hardening si aparece escritura concurrente.

## 7. Salud general

**7/10.** MVP funcional, decisiones documentadas en-linea, buena cobertura de tests y seguridad de paths correcta. Los problemas serios son de **corrección silenciosa** (dimensión de cache, colisión de chunk_id, update_note destructivo) y **duplicación estructural** (embedders x2, tablas de clasificación x2), no de diseño fundamental. El subsistema soporta un cambio grande de modelo de embeddings solo después de endurecer VectorCache.
