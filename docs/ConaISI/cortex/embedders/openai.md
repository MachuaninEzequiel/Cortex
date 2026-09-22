# cortex/embedders/openai.py

## Qué tiene adentro

- **Ruta de código:** `cortex/embedders/openai.py` (101 líneas).
- **Módulo Python:** `cortex.embedders.openai`.
- **Docstring del módulo:** cortex.embedders.openai ----------------------- DEPRECATED (dueño, 2026-08-25 — doc 12 §4.3): backend remoto que contradice el principio "todo local, cero keys" de Cortex. Sin porte a Rust planificado; se elimina en la baja definitiva de Python. Migrar a `embedding.backend: onnx` (MiniLM/e5 nativos vía cortex-embed).
- **Clases definidas:**
  - `OpenAIEmbedder`
    - Embedding backend powered by the OpenAI Embeddings API.
    - Métodos públicos/especiales: `__init__`, `model_name`, `backend`, `embed`, `embed_batch`
    - Métodos internos: `_get_client`

## Para qué sirve

cortex.embedders.openai
-----------------------
DEPRECATED (dueño, 2026-08-25 — doc 12 §4.3): backend remoto que contradice
el principio "todo local, cero keys" de Cortex. Sin porte a Rust planificado;
se elimina en la baja definitiva de Python. Migrar a `embedding.backend: onnx`
(MiniLM/e5 nativos vía cortex-embed).

OpenAI backend — text-embedding-3-small via API.

Legacy enterprise option for teams that want cloud-hosted embeddings.
Requires an ``OPENAI_API_KEY`` environment variable and the
``openai`` package.

Enable with:

    episodic:
      embedding_backend: openai
      embedding_model: text-embedding-3-small

Install the extra: pip install cortex-memory[openai]

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `logging`, `os`, `warnings`, `__future__`, `typing`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 101.
Docstrings de símbolos públicos:
- `OpenAIEmbedder.embed`: Embed a single string via the OpenAI Embeddings API.
- `OpenAIEmbedder.embed_batch`: Embed multiple strings in a single API call.

---
Fuente: código de `cortex/embedders/openai.py` (AST + grafo de imports internos). No se usó documentación previa.
