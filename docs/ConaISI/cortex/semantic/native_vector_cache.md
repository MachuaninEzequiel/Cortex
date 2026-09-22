# cortex/semantic/native_vector_cache.py

## Qué tiene adentro

- **Ruta de código:** `cortex/semantic/native_vector_cache.py` (208 líneas).
- **Módulo Python:** `cortex.semantic.native_vector_cache`.
- **Docstring del módulo:** NativeVectorCache — store vectorial Rust (schema v3) con la API de VectorCache.
- **Clases definidas:**
  - `NativeVectorCache`
    - Cache persistente de embeddings respaldado por el store binario Rust.
    - Métodos públicos/especiales: `__init__`, `get`, `batch_get`, `put`, `batch_put`, `invalidate`, `invalidate_chunks`, `invalidate_by_chunk_id`, `get_chunk_fingerprints`, `compact`, `clear`, `stats`
    - Métodos internos: `__len__`, `__contains__`, `_all_fps`
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

NativeVectorCache — store vectorial Rust (schema v3) con la API de VectorCache.

Reemplazo drop-in del ``VectorCache`` Python para el flag ``CORTEX_NATIVE=1``
(Obra 03, Gate G2). Delega el almacenamiento en ``cortex_core._native
.NativeVectorStore``: log append-only de UN archivo (``vectors.v3.bin``) que
elimina las dos patologías del esquema anterior:

- carga O(N) syscalls → UNA lectura secuencial;
- re-serialización JSON del índice por put/invalidate (O(N²) de ingesta)
  → append puro amortizado O(1).

Paridad garantizada:
- fingerprints: mismos que el cache Python (``cache_fingerprint`` no cambia);
- dim paramétrica: inferida del primer vector, validada después, mismatch
  ruidoso (lección vector_cache.py:41 / Fix A1);
- modelo distinto ⇒ reset del store (Fix A3);
- batch_put transaccional todo-o-nada (Fix A2);
- invalidaciones idempotentes + leak hasta compact() (mismas semánticas);
- store vacío ⇒ todo miss sin error.

## Relaciones

### Recibe de

- `cortex.semantic.vector_cache` (CacheStats, VECTOR_DTYPE)
- Dependencias externas/stdlib: `logging`, `threading`, `numpy`, `__future__`, `pathlib`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 208.
Docstrings de símbolos públicos:
- `NativeVectorCache.get`: Vector para ``fingerprint`` o ``None`` en miss/invalidado.
- `NativeVectorCache.batch_get`: Bulk get (UNA llamada FFI). Devuelve solo hits.
- `NativeVectorCache.batch_put`: Bulk put transaccional: validación previa, todo-o-nada (Fix A2).
- `NativeVectorCache.invalidate`: Marca una entrada inválida. True si existía (idempotente).
- `NativeVectorCache.invalidate_chunks`: Invalida por chunk_id exacto. Devuelve cuántas fueron nuevas.
- `NativeVectorCache.invalidate_by_chunk_id`: Invalida cada entrada cuyo chunk_id empieza con el prefijo.
- `NativeVectorCache.get_chunk_fingerprints`: {chunk_id: fp} de chunks vivos bajo ``parent_path`` (prefijo '#').
- `NativeVectorCache.compact`: Reescribe el archivo solo con entradas vivas (atómico).
- `NativeVectorCache.clear`: Elimina todas las entradas (borra el archivo del log).

---
Fuente: código de `cortex/semantic/native_vector_cache.py` (AST + grafo de imports internos). No se usó documentación previa.
