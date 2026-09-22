# Estructura — `cortex/semantic`

## Para qué existe esta carpeta

(sin docstring de paquete; reexportes)

## Árbol interno (código, sin `__pycache__`)

```
semantic/
├── __init__.py
├── chunker.py
├── markdown_parser.py
├── native_vector_cache.py
├── vault_reader.py
└── vector_cache.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/semantic/__init__.py` | 5 | reexportes / marcador de paquete |
| `cortex/semantic/chunker.py` | 306 | cortex.semantic.chunker - Split markdown documents into embedding-sized chunks. |
| `cortex/semantic/markdown_parser.py` | 80 | cortex.semantic.markdown_parser -------------------------------- Parses individual markdown files into SemanticDocument objects. |
| `cortex/semantic/native_vector_cache.py` | 208 | NativeVectorCache — store vectorial Rust (schema v3) con la API de VectorCache. |
| `cortex/semantic/vault_reader.py` | 917 | cortex.semantic.vault_reader ---------------------------- Reads, indexes and manages a markdown knowledge base (Obsidian vault). Supports wiki-links ([[note]]), frontmatter tags and **semantic vector search**. |
| `cortex/semantic/vector_cache.py` | 502 | cortex.semantic.vector_cache - Persistent cache for embedding vectors. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.documentation.common`
- `cortex.documentation.doc_type`
- `cortex.documentation.inventory`
- `cortex.episodic.embedder`
- `cortex.models`
- `cortex.security.paths`
- `cortex.semantic.chunker`
- `cortex.semantic.markdown_parser`
- `cortex.semantic.vault_reader`
- `cortex.semantic.vector_cache`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.__init__`
- `cortex.cli.docs_vectorization`
- `cortex.core`
- `cortex.enterprise.sources`
- `cortex.semantic`
- `cortex.semantic.native_vector_cache`
- `cortex.semantic.vault_reader`
- `cortex.webgraph.semantic_source`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
