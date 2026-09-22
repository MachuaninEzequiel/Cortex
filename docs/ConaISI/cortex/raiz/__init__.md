# cortex/__init__.py

## Qué tiene adentro

- Docstring de paquete: memoria híbrida episódica + semántica; v2.4 pipeline/services.
- `__version__ = "0.7.0"`, `__author__ = "cortex contributors"`.
- Reexporta: `AgentMemory`, `EpisodicMemoryStore`, `VaultReader`, `HybridSearch`, `SpecService`, `NoteService`, `SessionService` (alias deprecado de NoteService), `PRService`, `EmbedderFactory`, `EmbeddingConfig`, tipos de pipeline, modelos (`UnifiedHit`, `PRContext`, `GeneratedDoc`, `WorkContext`, `EnrichedItem`, `EnrichedContext`).

## Para qué sirve

API de importación `from cortex import AgentMemory`.

## Relaciones

### Recibe de

- `core`, `embedders`, `episodic.memory_store`, `models`, `pipeline`, `retrieval.hybrid_search`, `semantic.vault_reader`, `services`.

### Envía a

- Cualquier consumidor externo del paquete `cortex-memory`.
- CLI version callback.

---
Fuente: lectura completa de `cortex/__init__.py`. No se usó documentación previa.
