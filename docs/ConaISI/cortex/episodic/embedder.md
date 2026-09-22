# cortex/episodic/embedder.py

## Qué tiene adentro

- **Ruta de código:** `cortex/episodic/embedder.py` (87 líneas).
- **Módulo Python:** `cortex.episodic.embedder`.
- **Docstring del módulo:** cortex.episodic.embedder ------------------------ Thin compatibility wrapper around the consolidated embedding stack.
- **Clases definidas:**
  - `Embedder`
    - Produce dense vector embeddings for text.
    - Métodos públicos/especiales: `__init__`, `embed`, `embed_batch`
    - Métodos internos: `_get_onnx_fn`

## Para qué sirve

cortex.episodic.embedder
------------------------
Thin compatibility wrapper around the consolidated embedding stack.

Historia (A6)
-------------
Este módulo duplicaba Onnx/Local/OpenAI en paralelo a ``cortex/embedders/*``
y su path OpenAI hacía un request HTTP por texto. Desde la consolidación A6,
:class:`Embedder` delega 100% en :class:`cortex.embedders.factory.EmbedderFactory`
— un único punto donde "elegir modelo" existe.

Supported backends
------------------
- ``onnx``   → ONNXMiniLM via chromadb (DEFAULT — zero extra deps, fast)
- ``local``  → sentence-transformers (BACKUP — heavy ~2.5 GB PyTorch)
- ``openai`` → OpenAI Embeddings API (enterprise option)

To switch backends, set ``embedding_backend`` in your ``config.yaml``:

    episodic:
      embedding_backend: onnx    # default — recommended
      # embedding_backend: local # backup (requires sentence-transformers)
      # embedding_backend: openai

Deprecation note: importar backends concretos desde ``cortex.embedders``
es preferible; esta clase se mantiene para no romper imports existentes
(``cortex.episodic.memory_store``, ``cortex.semantic.vault_reader``,
``cortex.webgraph.*``, ``cortex.context_enricher.domain_detector``).

## Relaciones

### Recibe de

- `cortex.embedders.base` (EmbeddingBackend)
- `cortex.embedders.factory` (EmbedderFactory, EmbeddingConfig)
- Dependencias externas/stdlib: `logging`, `__future__`, `typing`

### Envía a

- `cortex.episodic`
- `cortex.episodic.memory_store`
- `cortex.semantic.vault_reader`
- `cortex.webgraph.episodic_source`
- `cortex.webgraph.semantic_source`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 87.
Docstrings de símbolos públicos:
- `Embedder.embed`: Return the embedding vector for a single text string.
- `Embedder.embed_batch`: Embed multiple texts efficiently (single call per backend).

---
Fuente: código de `cortex/episodic/embedder.py` (AST + grafo de imports internos). No se usó documentación previa.
