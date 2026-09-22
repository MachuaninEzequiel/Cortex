# cortex/documentation/data.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/data.py` (223 líneas).
- **Módulo Python:** `cortex.documentation.data`.
- **Docstring del módulo:** cortex.documentation.data - Dataclasses for writer inputs.
- **Clases definidas:**
  - `CommonWriteData`
    - Fields common to every writer.
  - `SessionData` (CommonWriteData)
  - `HandoffData` (CommonWriteData)
  - `SpecData` (CommonWriteData)
  - `DesignDocData` (CommonWriteData)
    - Pluggable Middle Phase 09.B input for ``write_design_note``.
  - `ADRData` (CommonWriteData)
  - `DecisionData` (CommonWriteData)
  - `IncidentData` (CommonWriteData)
  - `PostmortemData` (CommonWriteData)
  - `RunbookData` (CommonWriteData)
  - `ArchitectureData` (CommonWriteData)
  - `ChangelogData` (CommonWriteData)
  - `HUData` (CommonWriteData)
  - `GlossaryEntryData` (CommonWriteData)

## Para qué sirve

cortex.documentation.data - Dataclasses for writer inputs.

Each ``write_X_note`` function accepts a typed ``XData`` dataclass.
These are *inputs*, not frontmatter schemas (those live in pydantic models
in ``cortex.documentation.schemas``).

Rationale: dataclasses are lighter for incremental construction by callers
(agents, services). Pydantic validation happens later when the writer
builds the frontmatter.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`, `dataclasses`, `datetime`, `typing`

### Envía a

- `cortex.documentation.writers`
- `cortex.documenter.persistence`
- `cortex.services.note_service`
- `cortex.services.spec_service`
- `cortex.workitems.service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 223.

---
Fuente: código de `cortex/documentation/data.py` (AST + grafo de imports internos). No se usó documentación previa.
