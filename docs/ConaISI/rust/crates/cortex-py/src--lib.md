# src/lib.rs

## Qué tiene adentro

Módulo PyO3 `#[pymodule] fn _native`.

Funciones:
- `core_version() -> &'static str` (`cortex_core::VERSION`).
- `cosine_scores(query ndarray1 f64, matrix ndarray2 f64 C-contigua) -> ndarray1`. Valida 2D no vacía; `dim = shape[1]`.
- `semantic_neighbor_pairs(...)` → `Vec<(usize,usize,f64)>`.
- `cross_source_build(...)` valida alineación de listas episódicas/semánticas; mapea `BuiltEdge` a tuplas `(id,source,target,edge_type,weight,evidence)`.

Clases (todas con `Mutex` interno):
- `NativeVectorStore`: `new(dir, model_name)`, getter `truncated_tail`, `dim`, `__len__`, `get_many` (store vacío → matriz `(n,0)` + todos False), `put_many`, `invalidate_many`, `fps_for_chunk_ids`, `fps_with_chunk_prefix`, `entries_export`, `compact`.
- `NativeBm25Index`: `set_stats`, `add_batch`, `remove_batch`, `clear`, `__len__`, `search` → numpy, `top_k`.
- `NativeEmbedder` (feature onnx): `new(model_dir, intra_threads=None)`, `dim`, `embed`, `embed_batch` (panic si el embedder falla).

Errores de dominio → `PyValueError`. Test smoke: `core_version() == cortex_core::VERSION`.

## Para qué sirve

Única frontera FFI. APIs batch/gruesas (regla citada R5.4): nunca loop-per-item desde Python.

## Relaciones

### Recibe de

- `cortex_core::{scoring, store::VectorStore, bm25::Bm25Index, webgraph}`.
- `cortex_embed::onnx::OnnxEmbedder` si feature onnx.
- numpy arrays C-contiguos.

### Envía a

- Import Python `cortex_core._native`.
- Código Python que, si `CORTEX_NATIVE=1`, llama estas APIs.

### Notas de implementación observadas en el código

`embed_batch` usa `unwrap_or_else(|e| panic!(...))` en vez de `PyResult`. Locks con `.expect("store lock")`. Store vacío en `get_many` no llama al inner `get_many` con dim desconocida: devuelve shape `(n, 0)`.
