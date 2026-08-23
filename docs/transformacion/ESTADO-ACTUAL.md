# ESTADO ACTUAL DEL PROGRAMA

> **PRÓXIMA SESIÓN = CONTINUAR OBRA 03**: quedan **G5-integración** (embedder ort
> productivo conectado a VaultReader), **G6** (CLI clap) y **T-BRAIN** (nativo).
> Leé `HANDOFF.md` §ESTADO-GATES-2026-08-24b + los ADRs en docs/transformacion/.
> Flag de ruta nativa: `CORTEX_NATIVE=1` (default APAGADO; paridad bit-exacta
> verificada en G1/G2/G3/G4). Compilado nativo:
> `.venv/bin/python -m maturin develop --release -m rust/crates/cortex-py/Cargo.toml`

## Estado al cierre de la sesión de migración Rust (2026-08-24b)

**GATES COMPLETADOS Y COMMITEADOS (uno por commit, suite verde en cada uno):**

- **I-1 ✅** `.github/workflows/ci-gates.yml`: gate bloqueante pytest+ruff
  F401/F841/F821+vulture80 + cargo clippy/test (condicional a rust/) + bench
  nocturno con compare >10%.
- **R2/T-CARGO-1 ✅** workspace `rust/`: cortex-core (PURO), cortex-embed,
  cortex-py (`cortex_core._native`). pyproject dedicado del crate (mixed layout)
  para NO pisar el build setuptools raíz. Dev loop:
  `maturin develop --release -m rust/crates/cortex-py/Cargo.toml`.
- **G1/T-PY-1 ✅** scoring batch cosine f64+Neumaier (= `sum()` CPython ≥3.12 →
  paridad BIT-exacta): scoring sub-path 51.1ms → 1.85ms (**27.6×**, gate ≥5× vs
  "baseline del path"); search() completo p50 89→26ms. Piso ONNX embed (~23ms)
  es de G5. Falsas regresiones index/cpu_energy investigadas y descartadas
  (-0.5% atribuible, experimento stash). Ver bench/results/COMPARE.md §G1.
- **G2/T-PY-2 ✅** store binario v3 append-only (`NativeVectorCache` drop-in;
  wiring flag en `_resolve_cache` + `embedding reindex`): cold load 5k
  **31.6→5.0ms (6.4×)** · ingesta 5k **50s→13.6ms (3684×**, O(N²) eliminada) ·
  hits bit-idénticos en 5000 fps.
- **G3/T-BM25-1 ✅** BM25 casero Rust (ADR-BM25.md: tantivy NO puede replicar tf
  por substring): p99 **10.09→1.85ms ≤2ms** · p50 5.56→1.19ms · ranking
  bit-idéntico 200/200 queries-synth (`bench/parity_check.py --bm25`).
- **G4/T-WG-1 ✅** webgraph nativo: vecinos rayon + cross-source con merge/dedupe
  en Rust + memoización pre-cómputos: n1000 **3162→345ms (9.2×**; 255–276 aislado
  ≤300) · edges IDÉNTICOS n∈{250,500,1000}.
- **G5-spike/T-EMB-1 ✅ decisión** (ADR-EMBEDDINGS.md): **ort elegido**, candle
  descartado. Paridad cos=**1.00000000** 5/5 textos ES+EN vs OnnxEmbedder;
  batch 100 textos 2871→1305ms (**2.2×**). Feature `onnx` no default.
  ⏳ INTEGRACIÓN productiva a VaultReader pendiente.
- **C1/T-DEC-1 ✅ decisión** (ADR-EPISODIC.md): chromadb QUEDA (crossover HNSW
  ~2-3k vectores, lejos del volumen episódico); criterios de re-evaluación
  explícitos (>50k memorias / Obra E).

- Suite: **2451 passed, 13 skipped** · ruff/vulture en 0 · cargo clippy/test
  verde · commits atómicos un-gate-por-commit.

- **G5-INTEGRACIÓN ✅** (commit 9e838d6): `NativeEmbedder` productivo conectado
  a `OnnxEmbedder` tras flag (singleton class-level). Paridad cos=1.0000000000
  (incluye textos >128 tokens); batch 100 textos **2.1×** más rápido;
  first_query_cold **457→22ms (20.8×)**; retrieve end-to-end p50 **4.3×** /
  p99 2.2× — el ≥5× end-to-end NO se alcanza: piso físico de inferencia
  ~13.8ms por query en este hardware (análisis y palancas: int8 H-9/GPU en
  COMPARE.md §G5-integración). FIX de harness: sync_empty_cache medía hits de
  cache (baseline p50=0.8s era inválido; costo frío real ≈ p99 42.6s → nativo
  38.3s honesto).
- **T-BRAIN ✅ incrementos 1+2** (commits 235498a + 9d224d7): crate
  `cortex-brain` binario nativo — router determinista 1:1 con router.py, tools
  READ/SAFE_ACTION delegando al CLI cortex vía subprocess (servicios Python
  hasta Obra E), loop+banner+slash commands, trait `LlmBackend`.
  **Incremento 2**: backend llama.cpp REAL (llama-cpp-2 0.1.154, feature
  `llama`) con GGUF oficial LiquidAI LFM2.5-1.2B-Instruct-Q4_K_M (730MB en
  ~/.cache/cortex/models/); chat template tomado del GGUF y aplicado con el
  motor jinja de llama.cpp; generación end-to-end VERIFICADA referenciando
  herramientas del catálogo. Muestreo greedy v1.

**PENDIENTE (siguientes sesiones, EN ORDEN):**

1. **T-BRAIN pulido [M]**: auto-ejecución de la herramienta sugerida por el
   LLM con confirmación del usuario (hoy la referencia se muestra pero no se
   despacha automáticamente); temperature/samplers; ventana dedicada
   (BRAIN-3) + i18n; CI con backend falso scriptado.
2. **G6/T-CLI-1 [L]**: cortex-cli clap feature-par nivel-0/1 (parity --json)
   — confirmar adopción con el dueño antes de cerrar Obra 03.
3. Opcionales: int8 e5-large (H-9) para bajar el piso de inferencia (~13.8ms
   por query, único obstáculo del ≥5× end-to-end); f32/SIMD en scoring con ADR.
4. Al cerrar cada uno: JSON bench + fila COMPARE.md + este archivo.

> **PRÓXIMA SESIÓN = MIGRACIÓN RUST.** Leé primero `HANDOFF.md` §TAREA-RUST (tarea
> explícita con pasos R0-R6) + `07-AUDITORIA-2026-08-24.md` (auditoría de realidad
> con todos los hallazgos resueltos). Plan técnico: `03-MIGRACION-RUST.md`.

## Estado al cierre de la sesión de auditoría y pulido (2026-08-24)

- TRAMO 0 ✅ · ola 1 ✅ · OBRA 02 ✅ · OBRA 01: **P2 ✅ P3 ✅ P4 ✅ P5 ✅ P6 ✅ P7 ✅ P8 ✅**
  · **P-BUGS COMPLETOS** (#3,#4,#5,#6 verificados resueltos; #7,#9,#10 arreglados con test)
  · Deudas: requirements.txt eliminado, _resolve_cache ya OK, V4 cerrada (factory), V7 ✅,
  V11 cerrada (lazy-deprecation existente), V12 ✅ GC tmp.
- **OBRA 03 A1 ✅**: bench/bench_harness.py + vault-synth-1k determinista commiteado +
  baseline-2026-08-23.json (webgraph O(n²) n1000=3.2s · full_sync_1k=37s · retrieve p99=129ms).
- **OBRA 04**: recomendación default global documentada (per-language; flip+reindex=dueño);
  int8 con plan concreto pendiente de ejecución.
- **OBRA 05 Fase A 1/4 ✅**: FeedbackStore JSONL + hook opcional en collector.
  **Fase A COMPLETA 4/4**: + telemetría cableada (rotación JSONL),
  + APIs públicas SessionService (cero ._storage externo), + guide_path revivido.
  **Fase B COMPLETA**: paquete cortex/action_engine/ (models/store/registry/
  scheduler/runner/learning) + catálogo v1 completo (10 acciones) + comando
  **Fase C COMPLETA**: nivel-0 start/finish + aliases ocultos; help raíz = 8
  visibles exacto; B3/B4 search arreglados (--format honrado siempre);
  **Fase D COMPLETA**: cortex/tui/core.py (Home <300ms + pantallas
  acciones/búsqueda, decisión→Learner→Runner reales), `cortex` sin
  argumentos abre el Home, session --watch deprecado. Sigue Fase E:
  aprendizaje cerrado + pulido i18n.
- Refactors de este tramo: main.py 2540→1894 l (pr-context/hu/embedding/mcp/documenting);
  enricher sync/async unificados vía _finalize_items (V3) con DOS bugs reales corregidos
  (closure de lambdas: todas las estrategias buscaban la última query + drift Fase 08);
  schemas ×13 → mixins (V5); skills embebidos → workspace_files/*.md (V8, -1400 l);
  V9 ciclo session↔documenter roto con TYPE_CHECKING + guardia de arquitectura.
- Suite unit+integration: VERDE (**2347 passed**, 13 skipped). Rama:
  feature/transformacion-2026-08. master sellado.
- Deudas restantes registradas: F821 cli/main.py `cortex_ide` (P-bugs),
  F821 ×5 WorkspaceLayout en templates.py (TYPE_CHECKING, cosmético),
  `_sync_vault_text` candidato de poda, CHANGELOG para momento de release.

## NUEVO (2026-08-24): Obra 06 ACTIVADA — `cortex brain` BRAIN-1 ✅

- Diseño cerrado por el dueño: llama.cpp/GGUF · comando `cortex brain` ·
  permisos estrictos (mutaciones=propone, no ejecuta) · embeddings opt-in.
- BRAIN-1 entregado: tools.py (7 tools READ/SAFE), router determinista,
  chat loop testeable sin TTY/modelo. `cortex brain` visible nivel-0;
  `next` oculto-funcional.
- Sigue: BRAIN-2 (llama.cpp/GGUF + tool-calling) y BRAIN-3 (ventana+logo).

## Próximos pasos (detalle en HANDOFF.md §5)

1. Obra 01: terminar P4 (documenting trio) → P5 → P6 (mixins schemas; V7 devsecdocops;
   cerrar V4) → P7 → P8.
2. Obra 03: **T-BENCH-1 ✅** (baseline-2026-08-23.json commiteado). Sigue T-EVAL-1 (queries anotadas, junto Obra 04) y T-CARGO-1 (workspace rust).
3. Cierre Obra 04 CON EL DUEÑO: reindex vault real + flip default global (int8 pendiente).
4. Obra 05: arrancar fases A-B.
5. Obra 06 (LFM2.5): futuro.
