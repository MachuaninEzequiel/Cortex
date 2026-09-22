# cortex/webgraph/relation_builder.py

## Qué tiene adentro

- **Ruta de código:** `cortex/webgraph/relation_builder.py` (489 líneas).
- **Módulo Python:** `cortex.webgraph.relation_builder`.
- **Clases definidas:**
  - `RelationBuilder`
    - Builds explainable relationships for the hybrid webgraph.
    - Métodos públicos/especiales: `__init__`, `build_edges`
    - Métodos internos: `_add_edge`, `_add_semantic_wikilinks`, `_add_semantic_spec_links`, `_add_supersedes_edges`, `_add_cross_source_edges`, `_add_semantic_neighbors`, `_native_neighbor_pairs`, `_native_cross_source_edges`, `_entities_from_metadata`
- **Funciones de módulo:**
  - `_slug(text)`
  - `_tokenize(text)`
  - `_identifier_tokens(text)`
  - `_cosine_similarity(a, b)`
- **Constantes / símbolos de módulo:** `_GENERIC_TAGS`, `_CROSS_SOURCE_NATIVE_MIN_PAIRS`, `_EDGE_LIST_ADAPTER`

## Para qué sirve

Define RelationBuilder. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- `cortex.webgraph.config` (WebGraphConfig)
- `cortex.webgraph.contracts` (EpisodicRecord, SemanticRecord, WebGraphEdge)
- Dependencias externas/stdlib: `math`, `re`, `__future__`, `collections`, `pydantic`

### Envía a

- `cortex.webgraph.graph_builder`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 489.

---
Fuente: código de `cortex/webgraph/relation_builder.py` (AST + grafo de imports internos). No se usó documentación previa.
