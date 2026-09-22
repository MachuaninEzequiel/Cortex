# Estructura — `cortex/embedders`

## Para qué existe esta carpeta

cortex.embedders ---------------- Strategy-based embedding backends for Cortex.

## Árbol interno (código, sin `__pycache__`)

```
embedders/
├── __init__.py
├── base.py
├── factory.py
├── fastembedder.py
├── language.py
├── local.py
├── onnx.py
└── openai.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/embedders/__init__.py` | 33 | cortex.embedders ---------------- Strategy-based embedding backends for Cortex. |
| `cortex/embedders/base.py` | 66 | cortex.embedders.base --------------------- The Embedder Protocol — the single interface that ALL embedding backends must satisfy. Using ``typing.Protocol`` (structural subtyping) means: |
| `cortex/embedders/factory.py` | 149 | cortex.embedders.factory ------------------------ EmbedderFactory — centralized registry for embedding backend selection. |
| `cortex/embedders/fastembedder.py` | 104 | cortex.embedders.fastembedder -------------------------------- Generic ONNX embedding backend powered by `fastembed` (Qdrant). |
| `cortex/embedders/language.py` | 128 | cortex.embedders.language ---------------------------- Heuristic ES/EN language detection — pure functions, zero dependencies. |
| `cortex/embedders/local.py` | 78 | cortex.embedders.local ---------------------- Local backend — sentence-transformers + PyTorch. |
| `cortex/embedders/onnx.py` | 173 | cortex.embedders.onnx --------------------- ONNX backend — the default, recommended embedder. |
| `cortex/embedders/openai.py` | 101 | cortex.embedders.openai ----------------------- DEPRECATED (dueño, 2026-08-25 — doc 12 §4.3): backend remoto que contradice el principio "todo local, cero keys" de Cortex. Sin porte a Rust planificado; se elimina en la baja definitiva de Python. Migrar a `embedding.backend: onnx` (MiniLM/e5 nativos vía cortex-embed). |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.embedders.base`
- `cortex.embedders.factory`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.__init__`
- `cortex.embedders`
- `cortex.embedders.factory`
- `cortex.episodic.embedder`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
