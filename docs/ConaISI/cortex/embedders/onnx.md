# cortex/embedders/onnx.py

## Qué tiene adentro

- **Ruta de código:** `cortex/embedders/onnx.py` (173 líneas).
- **Módulo Python:** `cortex.embedders.onnx`.
- **Docstring del módulo:** cortex.embedders.onnx --------------------- ONNX backend — the default, recommended embedder.
- **Clases definidas:**
  - `OnnxEmbedder`
    - Embedding backend powered by chromadb's built-in ONNX runtime.
    - Métodos públicos/especiales: `__init__`, `model_name`, `backend`, `embed`, `embed_batch`
    - Métodos internos: `_get_native`, `_get_onnx_fn`, `_load_onnx_fn`

## Para qué sirve

cortex.embedders.onnx
---------------------
ONNX backend — the default, recommended embedder.

Wraps chromadb's bundled ``ONNXMiniLM_L6_V2`` embedding function.
Identical model quality to the ``local`` backend (all-MiniLM-L6-v2)
but runs on ONNX Runtime (~10 MB) instead of PyTorch (~2.5 GB).

No extra dependencies beyond chromadb, which is already required.

Fase 1 — Capa 4 del plan multi-IDE & MCP hardening:
La carga del modelo ONNX se protege con un lock class-level + doble-check
locking. Sin esto, dos requests concurrentes al MCP que disparen la primera
inferencia pueden iniciar dos cargas en paralelo (~10 MB cada una), con
race condition en la inicializacion interna de chromadb. El lock garantiza
que UNA sola carga ocurre.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `logging`, `threading`, `__future__`, `pathlib`, `typing`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 173.
Docstrings de símbolos públicos:
- `OnnxEmbedder.embed`: Embed a single string via ONNX runtime.
- `OnnxEmbedder.embed_batch`: Embed multiple strings efficiently (single ONNX session call).

---
Fuente: código de `cortex/embedders/onnx.py` (AST + grafo de imports internos). No se usó documentación previa.
