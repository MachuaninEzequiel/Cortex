# cortex/embedders/fastembedder.py

## Qué tiene adentro

- **Ruta de código:** `cortex/embedders/fastembedder.py` (104 líneas).
- **Módulo Python:** `cortex.embedders.fastembedder`.
- **Docstring del módulo:** cortex.embedders.fastembedder -------------------------------- Generic ONNX embedding backend powered by `fastembed` (Qdrant).
- **Clases definidas:**
  - `FastEmbedder`
    - Embedding backend wrapping fastembed's ONNX models.
    - Métodos públicos/especiales: `__init__`, `model_name`, `backend`, `embed`, `embed_batch`
    - Métodos internos: `_prefix`, `_model`
- **Funciones de módulo:**
  - `cortex_fastembed_cache()` — Cache persistente de modelos fastembed para Cortex.

## Para qué sirve

cortex.embedders.fastembedder
--------------------------------
Generic ONNX embedding backend powered by `fastembed` (Qdrant).

Unlocks ANY of fastembed's supported models (multilingual-e5,
paraphrase-multilingual-*, arctic, etc.) without PyTorch — pure ONNX
Runtime, consistent with Cortex's battery-efficiency goals.

Optional dependency: ``pip install cortex-memory[fastembed]`` or
``uv pip install fastembed``.

Obra 04 Fase B/D — model evaluation + language-aware config.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `os`, `threading`, `__future__`, `pathlib`, `typing`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 104.
Docstrings de símbolos públicos:
- `FastEmbedder.embed`: Embed a single string (treated as a query).
- `FastEmbedder.embed_batch`: Embed multiple strings (treated as passages/documents).
- `cortex_fastembed_cache`: Cache persistente de modelos fastembed para Cortex.

---
Fuente: código de `cortex/embedders/fastembedder.py` (AST + grafo de imports internos). No se usó documentación previa.
