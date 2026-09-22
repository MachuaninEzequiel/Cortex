# Estructura — `cortex/retrieval`

## Para qué existe esta carpeta

(sin docstring de paquete; reexportes)

## Árbol interno (código, sin `__pycache__`)

```
retrieval/
├── __init__.py
├── hybrid_search.py
└── intent.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/retrieval/__init__.py` | 10 | reexportes / marcador de paquete |
| `cortex/retrieval/hybrid_search.py` | 253 | cortex.retrieval.hybrid_search ------------------------------- Combines episodic memory search and semantic vault search using **true cross-source Reciprocal Rank Fusion (RRF)** to produce a single, unified, ranked context list. |
| `cortex/retrieval/intent.py` | 175 | cortex.retrieval.intent ------------------------ Query intent detector for adaptive RRF weight computation. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.models`
- `cortex.retrieval.hybrid_search`
- `cortex.retrieval.intent`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.__init__`
- `cortex.core`
- `cortex.retrieval`
- `cortex.retrieval.hybrid_search`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
