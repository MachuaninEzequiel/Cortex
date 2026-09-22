# cortex/webgraph/contracts.py

## Qué tiene adentro

- **Ruta de código:** `cortex/webgraph/contracts.py` (95 líneas).
- **Módulo Python:** `cortex.webgraph.contracts`.
- **Clases definidas:**
  - `WebGraphCapabilities` (BaseModel)
  - `WebGraphStats` (BaseModel)
  - `WebGraphNode` (BaseModel)
  - `WebGraphEdge` (BaseModel)
  - `WebGraphSnapshot` (BaseModel)
  - `WebGraphNodeDetail` (BaseModel)
  - `SemanticRecord` (BaseModel)
  - `EpisodicRecord` (BaseModel)

## Para qué sirve

Define WebGraphCapabilities, WebGraphStats, WebGraphNode, WebGraphEdge, WebGraphSnapshot, WebGraphNodeDetail, SemanticRecord, EpisodicRecord. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`, `datetime`, `typing`, `pydantic`

### Envía a

- `cortex.webgraph.cache`
- `cortex.webgraph.config`
- `cortex.webgraph.episodic_source`
- `cortex.webgraph.federation`
- `cortex.webgraph.graph_builder`
- `cortex.webgraph.relation_builder`
- `cortex.webgraph.semantic_source`
- `cortex.webgraph.server`
- `cortex.webgraph.service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 95.

---
Fuente: código de `cortex/webgraph/contracts.py` (AST + grafo de imports internos). No se usó documentación previa.
