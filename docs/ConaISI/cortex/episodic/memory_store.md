# cortex/episodic/memory_store.py

## Qué tiene adentro

- `EpisodicMemoryStore`: ChromaDB `PersistentClient` + colección cosine (`hnsw:space=cosine`).
- `Embedder` inyectado (model/backend).
- `add`: extrae entidades por regex (function/class/endpoint/error/config_key/dependency/variable/constant, cap 15), arma `MemoryEntry`, embebe, `collection.add`.
- `search`: vector (default) o keyword `$contains` local si `use_embeddings=False` (comentario: Chroma moderno exige embeddings en `.query()`).
- Caches de entries / entity index con token de invalidación.
- `delete`, `count`, serialización de metadata (listas→JSON strings para Chroma).

## Para qué sirve

Memoria episódica: experiencias, sesiones, PRs, conversaciones. Vive en un directorio persistente (p.ej. `.cortex/memory` o `.memory/chroma`).

## Relaciones

### Recibe de

- `chromadb` + `Embedder`.
- `MemoryEntry` / `EpisodicHit`.
- Directorio `persist_dir` resuelto por `runtime_context.resolve_episodic_persist_dir`.

### Envía a

- `AgentMemory.episodic`, `HybridSearch`.
- `enterprise.sources`, `webgraph.episodic_source`.
- Servicios note/spec/pr (recuerdan al persistir).

### Notas de implementación observadas en el código

- Telemetría Chroma desactivada (`anonymized_telemetry=False`).
- Backend default del docstring de `__init__` dice local/openai pero el parámetro default real es `"onnx"`.

---
Fuente: lectura de `cortex/episodic/memory_store.py`. No se usó documentación previa.
