# cortex/context_enricher/co_occurrence.py

## Qué tiene adentro

- **Ruta de código:** `cortex/context_enricher/co_occurrence.py` (323 líneas).
- **Módulo Python:** `cortex.context_enricher.co_occurrence`.
- **Docstring del módulo:** cortex.context_enricher.co_occurrence --------------------------------- Typed Co-occurrence Graph for semantic file relationships.
- **Clases definidas:**
  - `RelationshipType`
    - Semantic relationship types between files.
  - `FileNode`
    - Represents a file in the co-occurrence graph.
  - `Relationship`
    - A typed relationship between two files.
  - `TypedCooccurrenceGraph`
    - Typed co-occurrence graph with semantic relationships.
    - Métodos públicos/especiales: `__init__`, `build_from_memories`, `get_strongest_relationship`, `calculate_relationship_score`, `clear`
    - Métodos internos: `_add_node`, `_add_relationship`, `_infer_relationship`, `_detect_language`, `__len__`, `__repr__`
- **Constantes / símbolos de módulo:** `RELATIONSHIP_WEIGHTS`

## Para qué sirve

cortex.context_enricher.co_occurrence
---------------------------------
Typed Co-occurrence Graph for semantic file relationships.

Replaces naive co-occurrence (file_a → {file_b: count}) with 
a typed graph that captures semantic relationships:
  - imported_by: file imports from another
  - tested_by: test file tests source file
  - extends/implements: class inheritance
  - uses_util: file uses utility function
  - references: general reference/link

Uses AST parsing to extract relationships from code.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `logging`, `__future__`, `collections`, `dataclasses`, `pathlib`, `typing`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 323.
Docstrings de símbolos públicos:
- `TypedCooccurrenceGraph.build_from_memories`: Build the graph from episodic memories.
- `TypedCooccurrenceGraph.get_strongest_relationship`: Get the strongest relationship between two files.
- `TypedCooccurrenceGraph.calculate_relationship_score`: Calculate co-occurrence score using typed relationships.
- `TypedCooccurrenceGraph.clear`: Clear all graph data.

---
Fuente: código de `cortex/context_enricher/co_occurrence.py` (AST + grafo de imports internos). No se usó documentación previa.
