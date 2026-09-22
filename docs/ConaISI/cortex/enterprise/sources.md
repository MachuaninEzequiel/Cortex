# cortex/enterprise/sources.py

## Qué tiene adentro

- **Ruta de código:** `cortex/enterprise/sources.py` (115 líneas).
- **Módulo Python:** `cortex.enterprise.sources`.
- **Clases definidas:**
  - `VaultSource`
  - `EpisodicSource`
  - `MultiVaultReader`
    - Métodos públicos/especiales: `__init__`, `search`
    - Métodos internos: `_get_readers`
  - `MultiEpisodicReader`
    - Métodos públicos/especiales: `__init__`, `search`
    - Métodos internos: `_get_stores`

## Para qué sirve

Define VaultSource, EpisodicSource, MultiVaultReader, MultiEpisodicReader. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- `cortex.episodic.memory_store` (EpisodicMemoryStore)
- `cortex.models` (EpisodicHit, SemanticDocument)
- `cortex.semantic.vault_reader` (VaultReader)
- Dependencias externas/stdlib: `__future__`, `dataclasses`

### Envía a

- `cortex.enterprise.retrieval_service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 115.

---
Fuente: código de `cortex/enterprise/sources.py` (AST + grafo de imports internos). No se usó documentación previa.
