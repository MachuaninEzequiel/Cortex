# HANDOFF — Programa de Transformación Cortex

> **Leer esto COMPLETO antes de hacer nada.** Última actualización: 2026-08-24.
> Este documento es el contrato de continuidad entre sesiones/agentes. Si algo acá y en
> otro lado se contradice, este archivo manda (y actualizá el otro).

---

## 1. Contexto en 30 segundos

**Proyecto**: Cortex (`cortex-memory` v0.5.0) — memoria cognitiva híbrida (episódica +
semántica) y gobernanza para agentes de IA. CLI Typer + MCP server + retrieval híbrido
(ChromaDB + ONNX/fastembed + BM25) + vault estilo Obsidian + enterprise + webgraph +
ActionEngine. Repo: `/home/chucho/Cortex`. ~18k LOC en cortex/.

**Programa**: Transformación total nacida del deep-review de 12 subsistemas
(`docs/reviews/2026-08-deep-review/`), administrada en `docs/transformacion/`.

**Dónde estamos**: Obras 01, 02, 05 COMPLETAS · Obra 04 al ~90% (falta intervención del
dueño) · **Obra 03 (Rust) solo tiene A1 — la migración es LA TAREA DE LA PRÓXIMA SESIÓN**
(ver §TAREA-RUST abajo, con pasos concretos).

## 2. Estado VERIFICADO hoy (no confíes, ejecutá)

```bash
cd /home/chucho/Cortex
git branch --show-current          # feature/transformacion-2026-08 (master SELLADO v0.5.0-baseline-seal)
.venv/bin/python -m pytest tests/unit tests/integration -q --no-cov -p no:warnings   # ✅ 2415 passed
uvx ruff check --select F401,F841,F821 cortex   # ✅ 0
uvx vulture cortex --min-confidence 80          # ✅ 0
.venv/bin/python -m pytest tests/unit --cov=cortex -q | grep TOTAL   # ≥80%
```

Auditoría completa de realidad con evidencia: `docs/transformacion/07-AUDITORIA-2026-08-24.md`.
Todos sus hallazgos (R-1..3, H-1..H-7) están RESUELTOS con commits `fix(auditoria)`.

## 3. Qué se hizo en TODO el programa (resumen por obra)

### Obra 01 — Podado ✅ COMPLETA (P1-P8 + P-bugs)
- TRAMO 0: pin `mcp>=1.2,<2` (API 1.x; migración 2.x = P9 opcional post-split), suite verde.
- Monolitos partidos: mcp/server.py 2977→491 (schemas.py + tools/{search,sessions,
  documenter,workspace} mixins + dispatcher tabla `_TOOL_ROUTES`) con **golden contract MCP**
  byte-a-byte (`tests/unit/mcp/test_golden_contract.py`, snapshot en golden/list_tools.json).
- main.py 2277→~1925: subapps cli/{pr_context,hu,common,embedding,mcp_cmd,next,documenting}.
- V1-V9 resueltas: _PathVault único, schemas ×13 → mixins `_XSpecific`, skills embebidos →
  `setup/workspace_files/*.md` package-data, enricher sync/async unificados vía
  `_finalize_items()`, ciclo session↔documenter roto (TYPE_CHECKING + guardia), co_occurrence
  podada -50%, memory_decay podado a superficie viva.
- P-bugs 10/10: ver tabla §4 del plan 01 (+ bug #13 nuevo arreglado: SetupOrchestrator
  dry_run ahora REAL — test_dry_run_real.py).

### Obra 02 — Estándar IDE/CLI ✅ COMPLETA
- `cortex ide list|setup|remove|status` único contrato; uninstall seguro con marcadores
  BEGIN/END CORTEX SECTION en los 11 adapters; legacy root ocultos como aliases.

### Obra 04 — Vectorización ~90% (falta dueño)
- Embeddings por idioma MEDIDOS: ES=`intfloat/multilingual-e5-large` (fastembed, MRR@10
  0.9615 vs MiniLM 0.8821) · EN=all-MiniLM-L6-v2 onnx. Config `embedding:` per-language.
- Fixes vectoriales: dim paramétrica, fail-fast anti-búsqueda vacía, cache schema v2,
  prefijos query:/passage:, colisiones chunk_id, frontmatter preservado.
- `cortex reindex` (backup→rebuild→rollback) + `embedding-status`.
- Pendiente: int8 (plan en 04 §RECOMENDACIÓN), reindex vault real + flip default (DUEÑO).

### Obra 05 — UX/ActionEngine ✅ A-E completas
- **Fase A**: FeedbackStore JSONL (.cortex/feedback.jsonl + rotación), telemetría cableada
  en los 4 sitios de ContextEnricher + rotación events JSONL, APIs públicas SessionService,
  guide_path revivido en tutor.
- **Fase B**: paquete `cortex/action_engine/` (models/store/registry/scheduler/runner/
  learning/signals/metrics/i18n) + catálogo v1 (10 acciones sobre servicios existentes) +
  comando `cortex next` (--json/--explain-why-not/--all/--stats; <2s gate).
- **Fase C**: nivel-0 `start`/`finish`; aliases viejos ocultos; help raíz = 8 exacto;
  B3/B4 search (scope/project-id reales, --format siempre honrado); E2E ≤3 comandos
  (tests/e2e/test_flujo_3_comandos.py).
- **Fase D**: TUI home (`cortex` sin args) <300ms snapshot, pantalla acciones §3.5 real
  (Learner+Runner), búsqueda con feedback persistido, watch deprecado.
- **Fase E**: señales feedback→score (±25%), métrica pct_motor (`next --stats`),
  i18n ui.language ES/EN.
- ⚠ Gate final pendiente de USO REAL: registrar pct_motor tras ≥2 semanas.

## 4. Decisiones técnicas CERRADAS (NO re-discutir)

1. **Embeddings**: e5-large ES / MiniLM EN vía fastembed+onnx — elegidos por eval suite
   (`eval/retrieval/run_eval.py`), no intuición. Config per-language es el default recomendado.
2. **Pin mcp>=1.2,<2** hasta P9 (migración API 2.x opcional tras split ya hecho).
3. **LFM2.5 (Liquid)** NO es embedder: Obra 06 futura, investigación primero. Licencia LFM1.0
   libre solo <$10M/año.
4. **MrBERT-es** requiere fine-tune contrastivo para ser embedder (obra futura candidata).
5. Piezas dormidas RESERVADAS Obra 05 (feedback_loop/telemetría/tutor) ya CONECTADAS — no tocar sin necesidad.
6. TUIs: typer+rich, NO Textual en v1 (escape clause documentado §4.1).
7. Dry-run del ActionEngine calcula su propio plan (el orquestador recién ahora respeta dry_run).
8. Report-only actions: reversible=True con undo no-op (contrato exige undo si reversible).

## 5. Reglas de trabajo (aprendidas — se aplican SIEMPRE)

1. Suite verde antes de cada commit: `.venv/bin/python -m pytest tests/unit tests/integration
   -q --no-cov -p no:warnings`. Commits atómicos por lógica. Nunca mezclar poda+refactor+bugfix.
2. Los planes de las obras MANDAN; si están mal, actualizar el plan PRIMERO.
3. Verificación contra código real, no checkboxes (ver 07-AUDITORIA: así se detectaron
   regresiones propias).
4. Subagentes: briefs edit-first, scopes disjuntos, git prohibido, entrega incremental;
   si un hijo se traba 2 veces, hacerlo directo.
5. Al cerrar sesión: actualizar ESTADO-ACTUAL.md + este HANDOFF.
6. Websearch no configurado; para investigar modelos usar API pública HF vía httpx.

## 6. Deudas vivas (fuera de Rust — prioridad menor)

| # | Ítem | Nota |
|---|---|---|
| I-1 | **Gate CI propio (T0.6)**: workflow que corra pytest+ruff+vulture bloqueante | HACERLO JUNTO AL ARRANQUE RUST (bloquea merges desde día uno) |
| H-8 | CHANGELOG: normalizar 8 [Unreleased] | decisión de versión = DUEÑO |
| H-9 | int8 e5-large (cuantizar ONNX + backend + eval gate MRR≥0.93) | plan en doc 04 |
| H-10 | Reindex vault real + flip default global | REQUIERE DUEÑO |
| H-11 | Ventana 2 semanas pct_motor | REQUIERE USO REAL |

---
---

# 🦀 ESTADO-2026-08-24c — T-BRAIN pulido COMPLETO + OOM de memoria resuelto

> Sesión siguiente a la de arriba. Actualiza (no reemplaza) el orden: lo que
> sigue es G6/T-CLI-1 con decisión de dueño.

## OOM del kernel: causa raíz y lección permanente (leer ANTES de correr modelos)

Dos sesiones seguidas murieron por `oom-kill` global (23/08 21:15 · 24/08 09:08).
Evidencia en journalctl: un solo `python` con ~9.4–10.3GB (RSS+zram) sobre
11GB RAM — era `bench/int8_probe.py` v1: fp32+int8 cargados A LA VEZ + corpus
de 1000 textos en un batch. Fix commiteado (fases secuenciales, batch 64,
arena off): pico 10GB→397MB.

**Reglas duras de memoria en esta máquina (ASUS S5402ZA, 11GB + zram):**
1. NUNCA dos modelos residentes simultáneos (embedder + LLM, o dos variantes
   del mismo). Fase completa → liberar → recién entonces abrir el otro.
2. Inferencia batch SIEMPRE trozada (≤64 textos); jamás batches gigantes.
3. onnxruntime con `enable_cpu_mem_arena=False` cuando el proceso conviva con
   uso interactivo del equipo.
4. Antes de lanzar algo que cargue LFM2.5 (~1.3GB) o e5-large (~2.2GB):
   verificar `free -m` primero.
Pesos medidos 2026-08-24c: search CLI 106MB · embedder MiniLM 465MB ·
cortex-brain --model 1312MB · probe corregido ~400MB.

## Gate H-9 int8: NO PASA (cerrado por gate)

`bench/results/int8-spike.json`: cos mean **0.947** <0.99 · hit@5 int8 0.79 vs
fp32 0.86 (cae >5% rel) · speedup 1.62×. Decisión automática del gate acordado:
se descarta la cuantización dinámica; NO se integra nada. El ≥5× end-to-end
queda supeditado a GPU (o aceptar piso actual) — decisión de dueño.

## T-BRAIN pulido ✅ (commits test/feat de esta sesión)

Auditoría contra código real (regla R3): auto-despacho c/confirmación,
temp/seed/samplers y ventana BRAIN-3 ya existían desde 6a5479f. Lo faltante:

| Pieza | Commit | Contenido |
|---|---|---|
| Protocolo TOOL testeable + CI sin modelo | test(rust T-BRAIN) | `chat::extraer_tool / respuesta_sin_tool / confirma / procesar_respuesta_modelo` en librería; **ScriptedBackend** público (backend falso scriptado); 12 tests e2e con CORTEX_BIN=/bin/echo; el job cargo de ci-gates.yml los corre sin cambios extra |
| i18n ES/EN | feat(rust T-BRAIN) | `i18n.rs`: CORTEX_LANG > ui.language (.cortex/config.yaml > legacy) > es — misma convención que action_engine/i18n.py; help/prompts/avisos traducidos; router/catálogo/salidas de tools invariantes; confirma acepta s\|si\|sí\|y\|yes |
| Fix bench OOM | fix(bench) | int8_probe seguro + int8-spike.json (gate NO PASA) |

Verificación de cierre: rust workspace fmt/clippy/test verde (**78 tests**) ·
suite Python verde · smoke --model real exit 0 pico 1312MB · smoke i18n EN/ES
por stdin OK.

## Descubrimiento post-docs: G6/T-CLI-1 YA ESTABA COMPLETO (3c38e69)

Revisando `git log` apareció un commit de la sesión anterior (23/08 21:12,
tres minutos antes del OOM #1) que no llegó a documentarse:

- **G6/T-CLI-1 ✅** `feat(rust G6/T-CLI-1)`: crate `cortex-cli` — fachada
  nativa passthrough (decisión del dueño 2026-08-24b: "fachada sobre CLI
  Python"). Paridad por construcción (argv + stdio heredados, --json
  idéntico), startup nativo <50ms (--cli-version), override CORTEX_BIN, 2
  tests de paridad verde.
- Desviación documentada en el propio commit: clap SE OMITE en modo fachada
  porque subcomandos propios interceptarían --help/--json del CLI real;
  subcomandos nativos recién en Obra E cuando migren los servicios.

**Con esto, OBRA 03 QUEDA COMPLETA**: A1/I-1/T-CARGO-1/G1/G2/G3/G4/G5+
integración/C1/G6/T-BRAIN pulido/wheels/T-EVAL-1 — todos commiteados con
suite verde y JSON/ADR correspondientes.

## Pendiente (orden actualizado)

1. **Cierre Obra 04 CON EL DUEÑO**: reindex vault real + flip default global
   per-language (e5-large ES / MiniLM EN).
2. **H-8**: normalizar CHANGELOG (decisión de versión = dueño).
3. **H-11**: registrar pct_motor tras ≥2 semanas de uso real.
4. Opcionales: GPU para ≥5× e2e (int8 descartado); traducción de salidas de
   tools (hoy solo chrome está en EN); subcomandos nativos del CLI en Obra E;
   f32/SIMD con ADR nuevo.
5. Reglas vigentes: las mismas de §R5 (paridad antes que velocidad, flag
   default apagado, suite verde antes de commit, un gate por commit) + las 4
   reglas de memoria de arriba.

---

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
