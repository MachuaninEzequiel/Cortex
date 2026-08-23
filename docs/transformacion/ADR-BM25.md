# ADR-001 — BM25: casero en Rust vs tantivy (Gate G3)

> Estado: ACEPTADO · Fecha: 2026-08-24 · Gate: G3 / T-BM25-1
> Contexto del programa: docs/transformacion/03-MIGRACION-RUST.md §6.1 planteaba
> "tantivy o BM25 casero sobre postings — decidir con benchmark de tamaño
> binario/tiempo de build". Este ADR cierra esa decisión.

## Decisión

**BM25 casero en Rust (`cortex-core::bm25`), escaneando el corpus en memoria con
rayon. Tantivy descartado para esta fase.**

## Razón determinante: la semántica de scoring NO es BM25 estándar

El gate exige **ranking idéntico** al Python actual sobre queries-synth (regla
dura R5.2). El código de referencia (`VaultReader._bm25_search`) tiene tres
peculiaridades que un índice invertido no puede reproducir:

1. **tf por SUBSTRING**: `text.count(term)` cuenta ocurrencias no solapadas del
   término como substring dentro de `(title + " " + content)` bajado — un doc
   con "authentic" suma tf para el término "auth". Un analizador tokenizante
   (tantivy) indexa términos completos y produce OTRO ranking por construcción.
2. **doc_len en tokens-whitespace** del texto crudo, mezclado con tf-substring:
   una combinación sin equivalente en motores estándar.
3. **Fórmula idf propia** `log((n-df+0.5)/(df+0.5) + 1)` con df calculado sobre
   tokens — ya divergente de cualquier configuración default de tantivy, y el
   IDF vive en Python (`_compute_idf`) junto a `_avgdl`.

Portar el scoring EXACTO a Rust replica los bits; portarlo a un motor real
requeriría primero cambiar la semántica de scoring del producto (decisión de
dueño, fuera del alcance de este gate).

## Costos evaluados

| Criterio | tantivy | casero elegido |
|---|---|---|
| Paridad de ranking con el código actual | ❌ imposible sin reescribir semántica | ✅ bit-exacta verificada |
| Tiempo de build extra | +dependencia pesada (~200+ crates transitivos) | 0 (std + rayon ya en workspace) |
| Tamaño binario wheel | +varios MB | ~0 |
| p99 bm25-only query (corpus 1000 docs / 2.6 MB) | proyectado <1 ms | **~1.1 ms medido** (gate ≤2 ms ✅) |
| Escalabilidad futura (corpus ≥100k docs, queries complejas) | excelente | limitada por scan O(corpus)/query |

## Consecuencias

- La ruta nativa activable (`CORTEX_NATIVE=1`) mantiene ranking bit-idéntico:
  verificado en tests unitarios y `bench/parity_check.py --bm25`
  (200/200 queries, scores == exactos).
- Optimización honesta incluida: copia diferida del top-k en `_bm25_search`
  (misma salida, ~1.3 ms menos por query en ambas rutas).
- **Re-evaluación disparada si**: (a) el dueño decide migrar el scorer a
  tokenización real (entonces tantivy/tantivy-like vuelve a mesa), (b) los
  vaults objetivo crecen 2 órdenes de magnitud (>100k docs), o (c) aparecen
  queries interactivas que exijan <100 µs.
