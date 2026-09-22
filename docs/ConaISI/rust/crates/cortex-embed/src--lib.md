# src/lib.rs

## Qué tiene adentro

- `EmbeddingDim(usize)`: newtype. `from_model_output(last_dim)` falla si `last_dim == 0`. `get()`.
- `#[cfg(feature = "onnx")] pub mod onnx;`
- Tests: acepta 384/768/1024; dim 0 es error.

## Para qué sirve

Forzar que la dimensión salga del modelo, no de una constante (el comentario cita el bug `VECTOR_DIM=384` de `vector_cache.py:41`).

## Relaciones

### Recibe de

- Shape de salida del modelo ONNX (vía `onnx.rs` en producción).

### Envía a

- Tests del propio crate.
- El módulo `onnx` (cuando hay feature) usa `self.dim` interno, no necesariamente este newtype.

### Notas de implementación observadas en el código

Sin feature `onnx`, no hay embedder productivo: solo el tipo de dimensión.
