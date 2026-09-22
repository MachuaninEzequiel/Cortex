# Estructura — `cortex/episodic`

## Para qué existe esta carpeta

(sin docstring de paquete; reexportes)

## Árbol interno (código, sin `__pycache__`)

```
episodic/
├── __init__.py
├── embedder.py
├── memory_store.py
└── summarizer.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/episodic/__init__.py` | 6 | reexportes / marcador de paquete |
| `cortex/episodic/embedder.py` | 87 | cortex.episodic.embedder ------------------------ Thin compatibility wrapper around the consolidated embedding stack. |
| `cortex/episodic/memory_store.py` | 470 | cortex.episodic.memory_store ---------------------------- ChromaDB-backed episodic memory store with semantic search. |
| `cortex/episodic/summarizer.py` | 115 | cortex.episodic.summarizer -------------------------- Compresses verbose agent action logs into concise memory entries using an LLM backend (OpenAI, Anthropic, or local via Ollama). |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.embedders.base`
- `cortex.embedders.factory`
- `cortex.episodic.embedder`
- `cortex.episodic.memory_store`
- `cortex.episodic.summarizer`
- `cortex.models`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.__init__`
- `cortex.core`
- `cortex.enterprise.sources`
- `cortex.episodic`
- `cortex.episodic.memory_store`
- `cortex.semantic.vault_reader`
- `cortex.webgraph.episodic_source`
- `cortex.webgraph.semantic_source`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
