# cortex/embedders/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/embedders/__init__.py` (33 líneas).
- **Módulo Python:** `cortex.embedders`.
- **Docstring del módulo:** cortex.embedders ---------------- Strategy-based embedding backends for Cortex.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.embedders
----------------
Strategy-based embedding backends for Cortex.

Provides a unified Embedder protocol and a factory for selecting
the correct backend at runtime based on configuration.

Supported backends
------------------
- ``onnx``   → ONNXMiniLM (default, lightweight, fast)
- ``local``  → sentence-transformers (backup, flexible)
- ``openai`` → OpenAI text-embedding-3-small (enterprise)

Usage
-----
    from cortex.embedders import EmbedderFactory, EmbeddingConfig

    config = EmbeddingConfig(backend="onnx", model_name="all-MiniLM-L6-v2")
    embedder = EmbedderFactory.create(config)
    vector = embedder.embed("Fix login refresh token bug")

## Relaciones

### Recibe de

- `cortex.embedders.base` (EmbedderProtocol, EmbeddingBackend)
- `cortex.embedders.factory` (EmbedderFactory, EmbeddingConfig)

### Envía a

- `cortex.__init__`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 33.
Reexportes observados:
- cortex.embedders.base: EmbedderProtocol, EmbeddingBackend
- cortex.embedders.factory: EmbedderFactory, EmbeddingConfig

---
Fuente: código de `cortex/embedders/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
