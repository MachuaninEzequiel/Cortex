# cortex/services/spec_service.py

## Qué tiene adentro

- **Ruta de código:** `cortex/services/spec_service.py` (298 líneas).
- **Módulo Python:** `cortex.services.spec_service`.
- **Docstring del módulo:** cortex.services.spec_service ----------------------------- Domain service for creating and persisting implementation specifications.
- **Clases definidas:**
  - `SpecCreationResult`
    - Outcome of :meth:`SpecService.create`.
  - `_PathOnlyVault`
    - Minimal VaultLike that wraps a bare path for canonical writers.
    - Métodos públicos/especiales: `__init__`, `path`, `index_file`
  - `SpecService`
    - Creates and persists implementation specifications.
    - Métodos públicos/especiales: `__init__`, `create`
    - Métodos internos: `_normalize_hooks`, `_store_episodic`

## Para qué sirve

cortex.services.spec_service
-----------------------------
Domain service for creating and persisting implementation specifications.

Extracted from ``AgentMemory`` to satisfy the Single Responsibility
Principle. This service owns the entire lifecycle of a Specification:
validation, vault persistence, selective indexing, and episodic storage.

Depends on:
- ``cortex.documentation.write_spec_note_canonical``  (persistence)
- ``cortex.semantic.vault_reader.VaultReader``   (semantic indexing)
- ``cortex.episodic.memory_store.EpisodicMemoryStore`` (episodic memory)

## Relaciones

### Recibe de

- `cortex.documentation` (write_spec_note_canonical)
- `cortex.documentation.data` (SpecData)
- `cortex.documentation.writers` (VaultLike)
- `cortex.models` (MemoryEntry)
- `cortex.session.models` (SessionRecord, VerificationHook)
- Dependencias externas/stdlib: `logging`, `__future__`, `dataclasses`, `pathlib`, `typing`

### Envía a

- `cortex.core`
- `cortex.services`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 298.
Docstrings de símbolos públicos:
- `SpecService.create`: Create a specification note and persist it to the vault.

---
Fuente: código de `cortex/services/spec_service.py` (AST + grafo de imports internos). No se usó documentación previa.
