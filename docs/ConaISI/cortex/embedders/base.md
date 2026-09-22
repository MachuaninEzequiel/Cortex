# cortex/embedders/base.py

## Qué tiene adentro

- **Ruta de código:** `cortex/embedders/base.py` (66 líneas).
- **Módulo Python:** `cortex.embedders.base`.
- **Docstring del módulo:** cortex.embedders.base --------------------- The Embedder Protocol — the single interface that ALL embedding backends must satisfy. Using ``typing.Protocol`` (structural subtyping) means:
- **Clases definidas:**
  - `EmbedderProtocol` (Protocol)
    - Structural protocol for all embedding backends.
    - Métodos públicos/especiales: `model_name`, `backend`, `embed`, `embed_batch`

## Para qué sirve

cortex.embedders.base
---------------------
The Embedder Protocol — the single interface that ALL embedding backends
must satisfy. Using ``typing.Protocol`` (structural subtyping) means:

1. Backends don't need to inherit from a base class.
2. Any class with the right shape automatically satisfies the contract.
3. ``runtime_checkable`` enables isinstance() checks at startup.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`, `typing`

### Envía a

- `cortex.embedders`
- `cortex.embedders.factory`
- `cortex.episodic.embedder`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 66.
Docstrings de símbolos públicos:
- `EmbedderProtocol.model_name`: Name of the underlying embedding model.
- `EmbedderProtocol.backend`: Which backend this embedder uses.
- `EmbedderProtocol.embed`: Compute the dense vector for a single text string.
- `EmbedderProtocol.embed_batch`: Compute dense vectors for multiple texts efficiently.

---
Fuente: código de `cortex/embedders/base.py` (AST + grafo de imports internos). No se usó documentación previa.
