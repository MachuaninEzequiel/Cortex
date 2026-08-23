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

## G3 — T-BM25-1 BM25 nativo (CORTEX_NATIVE=1) · ADR: docs/transformacion/ADR-BM25.md

| Métrica | baseline Python | fase3-post (nativo) | Δ | Gate |
|---|---|---|---|---|
| **bm25_search p99** | 10.09 ms | **1.85 ms** | 5.4× | ✅ ≤2 ms |
| bm25_search p50 | 5.56 ms | 1.19 ms | 4.7× | informativa |
| Paridad ranking + scores (200 queries) | — | **BIT-IDÉNTICA** (`parity_check --bm25`) | — | ✅ exigente |

### Notas

1. **Decisión (ADR-BM25.md): casero en Rust, NO tantivy** — el scorer Python cuenta
   tf por SUBSTRING sobre texto bajado (`text.count(term)`); un índice invertido
   tokenizante produce otro ranking por construcción ⇒ violaría la regla de paridad.
   La réplica Rust es bit-exacta (mismo orden f64, match_indices == str.count).
2. Optimización con salida idéntica: top-k seleccionado EN RUST (desempate estable
   replicado: a igual score gana menor índice) + model_copy diferido al top-k final.
3. Warm-up del pool rayon dentro del rebuild (fuera del timing) + warm-up sin medir
   en suite_bm25 (misma metodología que retrieve, §5.2). Sin esto la primera query
   pagaba ~6 ms de spawn de threads y contaminaba el p99.
4. Falsas regresiones del compare fase2→fase3 investigadas: `webgraph n250` +24% y
   `first_query_after_sync` +11% son deriva ambiental (rutas no tocadas por este gate;
   webgraph aislado midió 98 ms minutos después — el mismo código oscila 98–3200 ms
   entre corridas en esta máquina con governor powersave). Sin regresión real.

## G2 — T-PY-2 store binario schema v3 (CORTEX_NATIVE=1)

| Métrica | VectorCache Python v2 | NativeVectorCache Rust v3 | Δ | Gate |
|---|---|---|---|---|
| **Cold load completo** (índice + leer 5000×384 f32) | 31.6 ms | **5.0 ms** | **6.4×** (mediana de 5) | ✅ ≥5× carga índice · <100 ms |
| Ingesta 5000 chunks (batch_put) | 50.2 s | **13.6 ms** | **3684×** | ✅ sin curva O(N²) |
| Paridad de hits (5000 fps, bits) | — | **BIT-IDÉNTICA** (`suite vector_store`) | — | ✅ exigente |

### Notas

1. Formato nuevo: log append-only de UN archivo (`vectors.v3.bin`, magic `CCTXV3`).
   Elimina las dos patologías del esquema v2: O(N) opens por carga y re-serialización
   JSON del índice por put/invalidate (O(N²) de ingesta — 50 s → 14 ms medidos).
2. Paridad estructural: mismos fingerprints (sha256 Python intacto), dim paramétrica
   inferida del primer vector + validación ruidosa, modelo distinto ⇒ reset (A3),
   batch_put transaccional (A2), invalidaciones idempotentes, leak-hasta-compact,
   cola truncada ⇒ prefijo válido + WARNING (R8). Tests: 8 en
   test_native_vector_cache.py + 7 en cortex-core::store.
3. Metodología: cold load con mediana de 5 reaperturas (n=1 en escala ms es ruido;
   primera corrida dio 7.8×, segunda 4.7×, mediana-5 estabiliza ~6×). Ingesta única
   corrida (dominada por trabajo real). Wiring: flag CORTEX_NATIVE=1 en los puntos de
   construcción reales (`cli/docs_vectorization._resolve_cache`, `cli/embedding reindex`);
   VaultReader no cambia (interfaz duck-type idéntica).
4. `cold_start.sync_warm_cache` mejora −37% ya bajo flag: efecto colateral esperado
   (el warm sync ahora sí tiene cache nativo disponible).
