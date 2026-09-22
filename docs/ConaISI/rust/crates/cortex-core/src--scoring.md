# src/scoring.rs

## Qué tiene adentro

Scoring cosine batch (Gate G1).

- `ScoringError`: `EmptyDim`, `DimMismatch { query_len, dim }`, `MatrixNotMultiple { matrix_len, dim }`. Falla ruidosa; no trunca.
- `sum_neumaier`: suma compensada izquierda→derecha, réplica de `sum()` de CPython ≥3.12.
- `cosine_scores(query: &[f64], matrix: &[f64], dim: usize) -> Result<Vec<f64>, ScoringError>`: 1 query × N filas fila-major aplanadas → N scores. Vector cero → `0.0`. Usa `f64::sqrt` IEEE.

Tests: ortogonales/paralelos/cero; dim paramétrica 3 y 8; paridad bit a bit vs referencia Python en 50 filas × 384; errores de dimensión; matriz vacía.

## Para qué sirve

Reemplazar el bucle Python `VaultReader._cosine_similarity` con una API gruesa (una llamada, todas las filas) sin cambiar bits de score.

## Relaciones

### Recibe de

- Caller: query `f64` de longitud `dim` y matriz `n×dim` contigua.
- No importa otros módulos del crate (Neumaier está duplicado en `webgraph.rs` a propósito).

### Envía a

- `cortex-py::cosine_scores` (numpy → slice → este fn → `PyArray1`).
- Tests internos.

### Notas de implementación observadas en el código

Se rechaza f32/SIMD en este gate porque cambiaría bits y empates de top-k. Componentes se asumen finitos; `±inf` se propaga IEEE (Python lanzaría OverflowError). `zip` de Python no-estricto se sustituye por validación de longitudes.
