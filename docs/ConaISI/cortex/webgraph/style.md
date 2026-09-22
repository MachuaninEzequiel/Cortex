# cortex/webgraph/style.py

## Qué tiene adentro

- **Ruta de código:** `cortex/webgraph/style.py` (171 líneas).
- **Módulo Python:** `cortex.webgraph.style`.
- **Docstring del módulo:** cortex.webgraph.style - Node and edge styling for the canonical webgraph.
- **Clases definidas:**
  - `NodeStyle`
    - Visual styling for a node in the webgraph.
- **Funciones de módulo:**
  - `style_for_doc_type(doc_type)` — Resolve a ``NodeStyle`` for a DocType.
  - `style_for_edge(edge_type)` — Resolve a style dict for an edge classification.
  - `build_legend()` — Build a legend payload suitable for embedding in a webgraph snapshot.
- **Constantes / símbolos de módulo:** `_DEFAULT_NODE_COLOR`, `_DEFAULT_NODE_SHAPE`, `_EXTRA_NODE_STYLES`, `EDGE_TYPES`, `__all__`

## Para qué sirve

cortex.webgraph.style - Node and edge styling for the canonical webgraph.

Maps ``DocType`` instances and edge classifications to colors and shapes so
the visualization layer can render the graph with semantic differentiation.

Colors come from each ``RouteSpec.webgraph_color`` and shapes from
``RouteSpec.webgraph_shape`` (defined in
``cortex.documentation.routing.DOC_TYPE_ROUTING``). This module exists so the
visualization layer doesn't need to know about the routing table directly —
it just calls ``style_for_doc_type(doc_type)`` and gets back a ``NodeStyle``.

## Relaciones

### Recibe de

- `cortex.documentation.doc_type` (DocType)
- Dependencias externas/stdlib: `__future__`, `dataclasses`

### Envía a

- `cortex.webgraph.server`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 171.
Docstrings de símbolos públicos:
- `style_for_doc_type`: Resolve a ``NodeStyle`` for a DocType.
- `style_for_edge`: Resolve a style dict for an edge classification.
- `build_legend`: Build a legend payload suitable for embedding in a webgraph snapshot.

---
Fuente: código de `cortex/webgraph/style.py` (AST + grafo de imports internos). No se usó documentación previa.
