# cortex/embedders/local.py

## Qué tiene adentro

- **Ruta de código:** `cortex/embedders/local.py` (78 líneas).
- **Módulo Python:** `cortex.embedders.local`.
- **Docstring del módulo:** cortex.embedders.local ---------------------- Local backend — sentence-transformers + PyTorch.
- **Clases definidas:**
  - `LocalEmbedder`
    - Embedding backend powered by sentence-transformers (PyTorch).
    - Métodos públicos/especiales: `__init__`, `model_name`, `backend`, `embed`, `embed_batch`
    - Métodos internos: `_get_model`

## Para qué sirve

cortex.embedders.local
----------------------
Local backend — sentence-transformers + PyTorch.

BACKUP option for when you need to use a custom HuggingFace model
that isn't available as ONNX. Requires a large PyTorch download
(~2.5 GB). Enable with:

    episodic:
      embedding_backend: local

Install the extra: pip install cortex-memory[local]

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `logging`, `__future__`, `functools`, `typing`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 78.
Docstrings de símbolos públicos:
- `LocalEmbedder.embed`: Embed a single string using sentence-transformers.
- `LocalEmbedder.embed_batch`: Embed multiple strings in an efficient batched call.

---
Fuente: código de `cortex/embedders/local.py` (AST + grafo de imports internos). No se usó documentación previa.
