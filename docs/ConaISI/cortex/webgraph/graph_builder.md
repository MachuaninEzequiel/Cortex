# cortex/webgraph/graph_builder.py

## Qué tiene adentro

- **Ruta de código:** `cortex/webgraph/graph_builder.py` (109 líneas).
- **Módulo Python:** `cortex.webgraph.graph_builder`.
- **Clases definidas:**
  - `GraphBuilder`
    - Assemble the hybrid Cortex graph from semantic and episodic records.
    - Métodos públicos/especiales: `__init__`, `build_snapshot`
    - Métodos internos: `_build_nodes`

## Para qué sirve

Define GraphBuilder. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- `cortex.webgraph.config` (WebGraphConfig)
- `cortex.webgraph.contracts` (EpisodicRecord, SemanticRecord, WebGraphEdge, WebGraphNode, WebGraphSnapshot, WebGraphStats)
- `cortex.webgraph.relation_builder` (RelationBuilder)
- Dependencias externas/stdlib: `__future__`, `collections`

### Envía a

- `cortex.webgraph.service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 109.

---
Fuente: código de `cortex/webgraph/graph_builder.py` (AST + grafo de imports internos). No se usó documentación previa.
