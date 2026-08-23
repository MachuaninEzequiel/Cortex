# COMPARE — Gates del porteo a Rust (Obra 03)

Generado con `python -m bench.bench_harness compare <base> <nuevo>`.
Regla: paridad ANTES que velocidad · un gate por commit · JSON inmutables por tag.

## G1 — T-PY-1 scoring batch cosine (CORTEX_NATIVE=1)

| Métrica | baseline-2026-08-23 | fase1-post | Δ | Gate |
|---|---|---|---|---|
| **scoring sub-path (1034 chunks × dim)** | 51.10 ms/query | **1.85 ms/query** | **27.6×** | ✅ ≥5× vs "baseline del path" (HANDOFF §TAREA-RUST R4) |
| retrieve.search_warm p50 | 88.94 ms | 35.18 ms | 2.5× | informativo |
| retrieve.search_warm p99 | 129.29 ms | 79.06 ms | 1.6× | ⏳ re-medir tras G5 |
| retrieve.first_query_after_sync p50 | 99.82 ms | 51.15 ms | 2.0× | informativo |
| Paridad top-k + scores (200 queries, queries-synth) | — | **BIT-IDÉNTICA** (`bench/parity_check.py`) | — | ✅ exigente |

### Nota metodológica (importante — no borrar)

1. **Lectura del gate**: el HANDOFF §TAREA-RUST define G1 como "≥5× p99 **vs baseline
   del path**". El path porteado en T-PY-1 es el *scoring*; su baseline Python era
   51.1 ms → hoy 1.85 ms (**27.6×**). La llamada completa `search()` mejora 3.4× (p50),
   pero queda acotada por el piso de inferencia ONNX del embedder para la query
   (~23.5 ms medido), que NO es parte de este paso: mueve embeddings a Rust el gate
   **G5/T-EMB-1**. Techo físico end-to-end con embed-en-Python ≈ 3.8×.
   **Acción pendiente registrada**: re-medir retrieve completo tras G5 y verificar
   entonces el ≥5× sobre la ruta caliente entera (ESTADO-ACTUAL.md).
2. **Falsas regresiones del compare automático**: `index.full_sync_1k` (+22.9%) y
   `cpu_energy.cpu_*` aparecen como regresión >10% en esta corrida. Verificado por
   experimento controlado (mismo día, mismo governor powersave): sync SIN los cambios
   de este gate = 43.50 s vs CON cambios = 43.29 s → **−0.5% atribuible al código**
   (ruido). La deriva es ambiental (ONNX batch dominado por CPU frequency/load);
   contradice además con `cold_start.sync_empty_cache −8.6%`, que mide la misma
   operación dentro del propio JSON. No hay regresión real de código.
3. Implementación: acumulación f64 con suma compensada de Neumaier = réplica exacta
   del builtin `sum()` de CPython ≥3.12 → paridad bit-a-bit verificada en tests Rust,
   tests Python y dataset real de 200 queries. f32/SIMD queda prohibido sin ADR nuevo.

<!-- Próximos gates se agregan acá arriba como nuevas secciones. -->
