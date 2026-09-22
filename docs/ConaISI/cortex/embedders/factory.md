# cortex/embedders/factory.py

## Qué tiene adentro

- **Ruta de código:** `cortex/embedders/factory.py` (149 líneas).
- **Módulo Python:** `cortex.embedders.factory`.
- **Docstring del módulo:** cortex.embedders.factory ------------------------ EmbedderFactory — centralized registry for embedding backend selection.
- **Clases definidas:**
  - `EmbeddingConfig`
    - Configuration for selecting and initialising an embedding backend.
  - `UnsupportedBackendError` (ValueError)
    - Raised when an unknown embedding backend is requested.
  - `EmbedderFactory`
    - Registry-based factory for creating embedding backends.
    - Métodos públicos/especiales: `create`, `create_from_params`, `supported_backends`
    - Métodos internos: `_import_class`

## Para qué sirve

cortex.embedders.factory
------------------------
EmbedderFactory — centralized registry for embedding backend selection.

This is the single creation point for all embedders. It maps backend
names from config.yaml to their concrete implementation classes.

Adding a new backend
--------------------
1. Create ``cortex/embedders/my_backend.py`` with a class that satisfies
   ``EmbedderProtocol`` (structurally — no inheritance needed).
2. Register it in ``EmbedderFactory._REGISTRY``.
3. That's it. No changes needed anywhere else.

Usage
-----
    from cortex.embedders import EmbedderFactory, EmbeddingConfig

    config = EmbeddingConfig(backend="onnx")
    embedder = EmbedderFactory.create(config)
    vector = embedder.embed("session context text")

## Relaciones

### Recibe de

- `cortex.embedders.base` (EmbedderProtocol, EmbeddingBackend)
- Dependencias externas/stdlib: `__future__`, `dataclasses`, `typing`

### Envía a

- `cortex.embedders`
- `cortex.episodic.embedder`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 149.
Docstrings de símbolos públicos:
- `EmbedderFactory.create`: Instantiate the correct embedder for the given config.
- `EmbedderFactory.create_from_params`: Convenience method: create an embedder directly from params
- `EmbedderFactory.supported_backends`: Return the list of registered backend names.

---
Fuente: código de `cortex/embedders/factory.py` (AST + grafo de imports internos). No se usó documentación previa.
