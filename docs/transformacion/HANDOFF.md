# HANDOFF — Programa de Transformación Cortex

> **HANDOFF ACTIVO (2026-08-24, cierre sesión integración).**
> Obra 07 dual-stream EN CURSO. Si algo acá contradice historia vieja de este
> archivo, MANDA ESTA SECCIÓN.

## 0. Contexto en 30 segundos

Cortex (`cortex-memory` v0.7.0): memoria cognitiva híbrida + gobernanza para
agentes. Programa: migración TOTAL Python→Rust (Obra 07, plan maestro
`docs/transformacion/08-MIGRACION-TOTAL-RUST.md`). Master sellado v0.5.0;
trabajo en `feature/transformacion-2026-08`. Suite Python = ORÁCULO
(2451+ tests verdes). Paridad-como-contrato en todo.

## 1. Estado por fases (detalle y evidencia: ESTADO-ACTUAL.md)

✅ P0 scaffolding+harness · P1 config · P2 vault/hybrid (100+100) ·
P3 episódica (+fix keyword) · P4 sessions/hooks/gates (+fix lstrip) ·
P5 reconstructor gitless/git-aware + persister (note byte-parity) ·
P10 branding/TUI (stream del dueño, 73 tests).

## 2. DUAL-STREAM ACTIVO — leé esto ANTES de tocar nada

Dos agentes comparten ESTE working tree. Asignaciones y reglas duras:
**plan maestro §4b** (`08-MIGRACION-TOTAL-RUST.md`). Resumen:

| | Stream A | Stream B |
|---|---|---|
| Fases | P6 cortex-actions + P7 context(module) | P8 cortex-setup + P9 cortex-mcp(rmcp) |
| Progreso | progreso-streamA.md | progreso-streamB.md |

REGLAS: cada stream SOLO sus archivos · cortex-app lo edita exclusivamente A ·
verificación SIEMPRE `-p` por crate · commits `feat(obra07 P#)` atómicos ·
NO actualizar ESTADO-ACTUAL/HANDOFF (integración posterior) · index.lock
ocupado ⇒ esperar/reintentar · reglas de memoria vigentes.

## 3. Cómo verificar (SIEMPRE)

```bash
cd /home/chucho/Cortex/rust
cargo fmt --check && cargo clippy -p <TU_CRATE> --all-targets -- -D warnings
cargo test -p <TU_CRATE>            # NUNCA confíes en el global sin filtrar
cargo run -q -p cortex-app --example bm25_search …   # harness patterns:
```

Paridad: `bench/parity/README.md` + scripts golden existentes (doctor,
next_stats, search_bm25_100, search_semantic_100, episódico, session dumps,
verification, gates, documenter, persister). Suite Python:
`.venv/bin/python -m pytest tests/unit tests/integration -q --no-cov`.

## 4. Decisiones cerradas (no re-discutir)

1. Paridad bit-exacta; f32/SIMD prohibido sin ADR que re-valide.
2. BM25 casero (substring semantics); tantivy descartado.
3. Embeddings por ort sobre artefactos chroma/fastembed cacheados.
4. ChromaDB sale → store nativo JSONL/export neutro (decisión migración total).
5. minijinja/ratatui/rmcp/tokio/git2 aprobados como deps del porteo.
6. Brain: propone-nunca-muta; LFM2.5 GGUF vía llama.cpp.
7. El cerebro ASCII+degradado del TUI/banner: RESUELTO por stream P10
   (cortex-branding half-block + paleta azul/cian).

## 5. Reglas de trabajo heredadas

Suite verde antes de cada commit (por crate) · planes mandan · verificación
contra código real, no checkboxes · un gate por commit · commits atómicos
prefijados · websearch no configurado (API pública HF vía httpx) · reglas de
memoria: un modelo residente por vez, batches ≤64, caché jamás en /tmp.

## 6. Deudas/decisiones pendientes del dueño

GPU para ≥5× e2e · H-8 CHANGELOG ya normalizado a 0.7.0 (release cuando
corresponda) · H-11 ventana pct_motor (uso real ≥2 semanas) · adopción CLI
nativo (P12) · reindex vault real cuando el vault crezca (hoy vacío; la
bóveda personal vive en ~/Polar con 2 notas).

---


---

# HISTORIAL DE HANDOFFS ANTERIORES

# 🦀 ESTADO-GATES-2026-08-24b — sesión de migración Rust cerrada

> Esta sección registra el resultado de ejecutar §TAREA-RUST. Actualiza y no
> reemplaza el orden de trabajo; lo que sigue es lo PENDIENTE.

## Completado en esta sesión (commits atómicos, suite verde en cada uno)

| Gate | Commit | Resultado |
|---|---|---|
| I-1 | 9d24813 | ci-gates.yml bloqueante (pytest+ruff+vulture+cargo+bench nocturno) |
| R2 T-CARGO-1 | 995ad7b | workspace rust/: core PURO + embed + py (cortex_core._native) |
| G1 T-PY-1 | d1ee5b0 | scoring Neumaier f64 bit-exacto · sub-path **27.6×** (≥5× vs baseline del path) · search p50 3.4× |
| G2 T-PY-2 | 68c131b | store v3 append-only: cold load **6.4×** (5.0ms) · ingesta **3684×** (13.6ms) · hits idénticos |
| G3 T-BM25-1 | 56fca16 | BM25 casero Rust (ADR-BM25): p99 **1.85ms ≤2ms** · ranking bit-idéntico 200/200 |
| G4 T-WG-1 | f729f18 | webgraph nativo: n1000 **9.2×** (345ms corrida completa, 255–276 aislado ≤300) · edges idénticos |
| G5 spike T-EMB-1 | 98381a8 | ADR-EMBEDDINGS: **ort elegido** · paridad cos=1.00000000 · 2.2× latencia batch |
| C1 T-DEC-1 | 664fede | ADR-EPISODIC: chromadb queda; criterios de re-evaluación |
| G5-integración | 9e838d6 | NativeEmbedder productivo: cos=1.0 · batch 2.1× · first_query_cold 20.8× · fix harness sync_empty_cache |
| T-BRAIN inc.1 | 235498a | cortex-brain nativo: router 1:1 + tools CLI + loop/banner + trait LlmBackend (26 tests) |
| T-BRAIN inc.2 | 9d224d7 | backend llama.cpp REAL (llama-cpp-2, feature llama) + GGUF LFM2.5 Q4_K_M descargado; generación end-to-end verificada |
| T-BRAIN pulido | 6a5479f | protocolo TOOL confirmado + temp/seed/samplers + ventana BRAIN-3 multiplataforma |
| Wheels CI | (ver git) | workflows/wheels.yml: maturin-action matriz 5 plataformas + release en tags |
| T-EVAL-1 | 96d0dd8 | queries-es-en.jsonl (100) + eval_retrieval.py: BM25 hit@5=1.0 MRR=1.0 ✅ |

Decisiones técnicas nuevas registradas (no re-discutir sin dueño):

1. Paridad f64 = suma compensada de Neumaier (réplica de `sum()` CPython ≥3.12);
   f32/SIMD prohibido sin ADR nuevo que re-valide paridad.
2. BM25 casero sobre tantivy (semántica substring del scorer original).
3. Embeddings por ort sobre los artefactos chroma ya cacheados.
4. Umbral `_CROSS_SOURCE_NATIVE_MIN_PAIRS=100k` para cross-source nativo.

## Pendiente (orden estricto para la próxima sesión)

1. ~~T-BRAIN pulido [M]~~ ✅ RESUELTO 2026-08-24c (ver §ESTADO-2026-08-24c
   arriba): lo pendiente real era ScriptedBackend/CI + i18n; el resto ya
   estaba en 6a5479f.
2. **G6/T-CLI-1 [L]**: cortex-cli clap feature-par nivel-0/1 con parity
   --json — CONFIRMAR ADOPCIÓN CON EL DUEÑO antes de cerrar Obra 03.
3. Métrica retrieve end-to-end: p50 4.3× / p99 2.2× (piso físico ~13.8ms de
   inferencia; ver COMPARE.md §G5-integración nota 2). El ≥5× end-to-end exige
   int8 (H-9) o GPU — decisión de dueño.
4. Cada uno con su JSON bench + COMPARE.md + commit atómico.

Reglas vigentes: las mismas de §R5 (paridad antes que velocidad, flag default
apagado, suite verde antes de commit, un gate por commit).

---


# 🦀 TAREA EXPLÍCITA PRÓXIMA SESIÓN: MIGRACIÓN A RUST (Obra 03) (HISTÓRICA — leída y ejecutada; ver estado arriba)

> El objetivo declarado del dueño: rendimiento/batería (≥5× en rutas calientes).
> Todo el diseño está en `docs/transformacion/03-MIGRACION-RUST.md` — LÉELO COMPLETO.
> Esta sección te da el orden de ejecución, los comandos exactos y los criterios.

## R0. Qué tienes YA disponible

- **Baseline Python commiteado**: `bench/results/baseline-2026-08-23.json`
  (cold_start import=872ms · full_sync_1k=37s · retrieve p50/p99=89/129ms ·
  webgraph n1000 p50=3162ms · bm25 p50=5.6ms). Máquina anotada dentro.
- **Harness**: `bench/bench_harness.py` con suites cold_start/retrieve/index/webgraph/bm25
  y subcomando compare:
  ```bash
  .venv/bin/python -m bench.bench_harness run --suite all --out bench/results/<tag>.json
  .venv/bin/python -m bench.bench_harness compare bench/results/baseline-2026-08-23.json bench/results/faseN.json
  # exit 1 si hay regresión >10% en alguna métrica
  ```
- **Dataset determinista commiteado**: `bench/datasets/vault-synth-1k/` (1000 docs seed 42)
  + queries-synth.json. NO regenerar.
- Suite verde 2415 passed · ruff/vulture en 0.

## R1. Preparación (primera media hora)

1. Leer `docs/transformacion/03-MIGRACION-RUST.md` COMPLETO (stack §6, gates §4, fases §9).
2. Leer este handoff entero + ESTADO-ACTUAL.md + 07-AUDITORIA.md.
3. Crear todo list propia: T-CARGO-1 → T-EVAL-1 → T-PY-1(G1) → T-PY-2(G2) → T-BM25-1(G3)
   → T-WG-1(G4) → T-EMB-1(G5) → T-DEC-1(C1) → T-CLI-1(D). UN gate por commit/PR.
4. Verificar toolchain: `cargo --version` (si falta, instalar rustup stable) + `uv pip show maturin`.

## R2. T-CARGO-1 (A2): workspace que compila

```
rust/
  Cargo.toml            # workspace
  crates/cortex-core/   # dominio PURO (sin pyo3): Chunk, DocType, scoring, BM25, store, parser
  crates/cortex-embed/  # wrapper ort sobre modelos ONNX (dim PARAMÉTRICA — jamás constante)
  crates/cortex-py/     # pyo3 extension-module → cortex_core._native (fachada GRUESA)
crates reglas: core testeable puro · embed usa ort (mismo runtime ONNX que Python → paridad G5 fácil)
```

- Empaquetado: maturin (pep517). Dev loop: `uv run maturin develop --release`.
- Crates vacíos pero compilando con 1 test smoke cada uno.
- Validación: `cd rust && cargo clippy -D warnings && cargo test` verde.
- CI: agregar job cargo (clippy+test) al gate CI nuevo (ver I-1) + job bench nocturno que
  falla si p99 empeora >10%.

## R3. I-1 (hacer AHORA mismo, 30 min): gate CI bloqueante

Crear `.github/workflows/ci-gates.yml`: pytest unit+integration + `ruff check --select F401,F841,F821 cortex`
+ `vulture cortex --min-confidence 80` (falla si >0) + (desde R2) cargo clippy/test.
Sin esto, las regresiones de limpieza vuelven a colarse (pasó en Fase B-E — ver auditoría §3).

## R4. Orden técnico de porteo (uno por vez, NUNCA en paralelo)

Cada paso = benchmark antes/después con `bench compare` + paridad de resultados + suite
Python verde con el flag apagado. Feature flag global: env `CORTEX_NATIVE=1` activa ruta
Rust; default apagado hasta que el gate dé verde.

| Paso | Qué porta | Gate | Detalle clave |
|---|---|---|---|
| **T-PY-1 (B1)** | `cortex-core::scoring` + binding batch `cosine_scores(query, matrix)->Vec<f32>` | **G1**: ≥5× p99 vs baseline del path + top-k idéntico | VaultReader.search usa native SOLO con CORTEX_NATIVE=1. Comparar con queries-synth.json |
| **T-PY-2 (B2)** | store binario propio (schema v2 dim paramétrica, falla RUIDOSA si mismatch) reemplazando VectorCache interno | **G2**: carga índice ≥5× + mismos hits | Respetar lección vector_cache.py:41 |
| **T-BM25-1 (B5)** | BM25: decidir tantivy vs casero (ADR con build-time/binario) | **G3**: p99 bm25 ≤2ms (base 5.6ms) + ranking idéntico | `_bm25_search` paridad sobre queries-synth |
| **T-WG-1 (B3)** | webgraph `_add_semantic_neighbors` → `cortex-core::webgraph` (rayon) | **G4**: sets de edges IDÉNTICOS + n1000 de 3.16s → ≤300ms | base O(n²) 200→3162ms es el mayor win |
| **T-EMB-1 (B4)** | embeddings: ort vs candle vs pre/post en Rust — spike + ADR | **G5**: mismos embeddings (cos sim ≥0.999 vs Python) + latencia | primera opción ort (paridad fácil) |
| **T-DEC-1 (C1)** | spike episodic store (sqlite-vec/HNSW/chromadb queda) | ADR con números | NO migrar por migrar |
| **T-CLI-1 (D)** | cortex-cli clap feature-par con comandos nivel-0/1 | **G6**: parity tests | solo al final |
| **T-BRAIN (NUEVO, decisión dueño 2026-08-24)** | BRAIN-2/3 NATIVOS en Rust: crate `cortex-brain` con bindings llama.cpp (GGUF LFM2.5), tool-calling sobre las acciones ya migradas, chat loop + ventana | paridad conductual vs los 13 tests de tests/unit/brain/ (son LA especificación) | NO re-implementar en Python: ver doc 06 §DECISIÓN DE LENGUAJE |

## R5. Reglas duras de la migración

1. **Un paso a la vez.** Si el gate del paso no da verde, se revierte y se documenta —
   no se "avanza" dejando dos mitades.
2. Paridad ANTES que velocidad: un resultado distinto invalida el gate aunque sea 10× más rápido.
3. Cada gate genera: JSON de bench (`bench/results/faseN-post.json`) + fila en COMPARE.md +
   actualización de ESTADO-ACTUAL.md con tag del gate.
4. La fachada Python (`cortex_core._native`) expone APIs BATCH/GRUESAS (matrices, no loops):
   llamar por-item mata el win de FFI.
5. `dim` de vectores = parámetro SIEMPRE (lección vector_cache.py:41).
6. Suite Python completa verde en cada commit (el flag apagado = comportamiento idéntico a hoy).
7. No portear código muerto: si aparece algo dudoso durante el porteo, podarlo en commit
   separado de poda o dejarlo en Python.
8. **El brain (Obra 06) se implementa DIRECTO EN RUST** tras los gates (decisión del
   dueño). BRAIN-1 Python es solo spec+fallback: sus 13 tests definen el comportamiento
   que cortex-brain debe replicar.

## R6. Definición de "programa terminado"

- Gates G1-G6 verdes con JSONs commiteados + ADRs (BM25, embeddings, episodic).
- CLI Rust feature-par (D) solo si el dueño confirma adopción.
- Métrica del programa: ≥5× p99 en retrieve/BM25/webgraph medido con el harness.
- ESTADO-ACTUAL.md refleja cada gate; Obra 03 marcada completa solo con todos.

## 7. Si algo rompe

- Suite roja → git revert del commit ofensor (los commits son atómicos justamente para esto).
- Golden contract MCP falla → algo cambió el contrato observable: revertir y diagnosticar.
- Bench compare exit 1 → regresión real: investigar ANTES de seguir al siguiente paso.
- Dudas de decisión cerrada → sección 4 arriba; dudas nuevas → registrarlas en el doc de
  obra correspondiente y consultar al dueño.

— Fin del handoff. Buena suerte con el porteo: el baseline ya hizo la parte aburrida. 🦀
