# Obra 03 — Migración a Rust

> Estado: PLANIFICACIÓN · Planificador: plan-rust · Basado en: docs/reviews/2026-08-deep-review/ + lectura directa del código.
> Requisito duro del dueño: rendimiento y eficiencia máximos (consumo de batería en laptop). Migración entera eventual.

## 0. Resumen ejecutivo
- Cortex es hoy 100% Python (~48k LOC). Las rutas calientes (búsqueda semántica, BM25,
  webgraph, ingesta) hacen matemática de vectores en Python puro, sin numpy vectorizado:
  cada query recorre N chunks con un coseno O(384) escrito a mano (`vault_reader._cosine_similarity`).
- Estrategia: migración **incremental vía PyO3**. El núcleo caliente se porta a Rust como
  extension-module; la fachada Python (`VaultReader`, `HybridSearch`, servicios) queda intacta.
  El CLI y los servicios se portan después. Rewrite total desde día 1: descartado (ver §3).
- Orden duro: **benchmark baseline primero** (§5), podar primero (Obra 01), elegir modelo nuevo
  de embeddings antes de portear el stack vectorial (Obra 04).
- Meta cuantitativa del programa: ≥5× en rutas calientes, medido con el harness de benchmarks.
  Sin número antes/después por fase, la fase no cierra (decision gates, §4).

## 1. Criterios de entrada y salida (gates de la obra)

### Criterio de ENTRADA (no se arranca sin esto)
- [ ] Obra 01 en estado "suite verde": pin de `mcp<2` resuelto, 0 tests caídos, gates propios en CI.
- [ ] Podado ejecutado sobre las rutas calientes: no se porta código muerto (vulture limpio en
      `cortex/semantic/`, `cortex/retrieval/`, `cortex/webgraph/`, `cortex/embedders/`).
- [ ] Baseline de benchmarks capturado y commiteado (§5): `bench/results/baseline-<fecha>.json`.
      Sin baseline NO hay migración.
- [ ] Obra 04 con decisión tomada de modelo de embeddings objetivo (dim ≠ 384 posible);
      el core Rust debe ser agnóstico de dimensión (bug conocido: `vector_cache.py:41`
      hardcodea `VECTOR_DIM=384`).
- [ ] Suite de evaluación retrieval ES+EN (de Obra 04) disponible para gate de paridad.

### Criterio de SALIDA (la obra no cierra sin esto)
- [ ] Todas las rutas calientes listadas en §2 corren en Rust detrás de fachada Python o CLI Rust.
- [ ] Cada fase tiene par benchmark antes/después con ≥5× o justificación escrita de por qué se acepta menos.
- [ ] Paridad de resultados: misma top-k que la línea base en ≥95% de queries del set de evaluación
      (gate de paridad, §7 riesgo R1).
- [ ] Wheels binarios para Linux/macOS/Windows (x86_64 + arm64 donde aplique) publicados por CI.
- [ ] Documentación de build actualizada (`maturin develop` documentado para contribuidores).

## 2. Rutas calientes reales (evidencia de código)

### 2.1 Búsqueda semántica — `cortex/semantic/vault_reader.py`
| Aspecto | Hoy |
|---|---|
| Coseno | `_cosine_similarity()` (`vault_reader.py:243-252`): Python puro, 3 pasadas + zip por par. **O(N·384) interpretado** por query. |
| Loop de scoring | `search()` itera TODOS los chunks en dict de `list[float]`, sin matriz: O(N_chunks · dim) en bytecode Python. |
| Normas | Recalcula `norm_b` para cada chunk en cada query (los vectores son constantes): 2× trabajo innecesario. |
| BM25 fallback | `_bm25_search()`: para cada doc hace `text.lower()` + `text.count(term)` por término → O(N_docs · len(doc) · N_terms) y re-loweriza el corpus entero **por query**. |
| IDF | `_compute_idf()`: tokeniza todo el corpus con `str.split()` en sync; aceptable pero sin caching entre syncs. |
| Por qué quema batería | Cada query ejecuta ~N_chunks × 384 multiplicaciones en el intérprete (~50-100 ns c/u vs ~0.1 ns/vector SIMD). Con 5k chunks ≈ 2M ops interpretadas + sort. En laptop con batería, CPU despierta más tiempo del necesario. |
| Ganancia esperada Rust | Matriz f32 contigua + dot product SIMD auto-vectorizado + normas precalculadas → **20-100× en scoring**, p99 de query de decenas de ms a <1 ms. Además: menos tiempo de CPU = menos energía (objetivo directo del dueño). |

### 2.2 Cache de vectores — `cortex/semantic/vector_cache.py`
| Aspecto | Hoy |
|---|---|
| Lectura | `_read_vector_at()` abre `chunks.bin` **por cada vector** (open/seek/read/close): O(N) syscalls por carga. |
| Serialización índice | `index.json` es un dict JSON de entradas; `_save_index()` re-serializa TODO el índice en cada invalidación → O(N) por put/invalidate, O(N²) acumulado sobre una ingesta masiva de N chunks. |
| Conversión | `cached.tolist()` convierte numpy→listas Python por vector en cada hit (`vault_reader._embed_batch_with_cache`): O(N·384) allocaciones. |
| Compact | `compact()` lee vector-por-vector (O(N) opens) y reescribe; correcto pero caro. |
| Bug estructural | `VECTOR_DIM=384` hardcodeado (`vector_cache.py:41`) — bloquea Obra 04. El porteo DEBE eliminar este hardcode. |
| Ganancia esperada Rust | Store propio binario mapeado en memoria (`memmap2`) o archivo único leído de una pasada: carga completa en ms, index binario (sin JSON), zero-copy hacia Python vía PyO3 buffer protocol. **10-50× en cold load** y elimina el O(N²) de ingesta. |

### 2.3 Webgraph — `cortex/webgraph/relation_builder.py`
| Aspecto | Hoy |
|---|---|
| Vecinos semánticos | `_add_semantic_neighbors()` (`relation_builder.py:264+`): doble loop O(n²) sobre todos los registros híbridos con coseno Python puro por par → O(n²·384). Con cap `semantic_neighbor_max_nodes`, pero ese cap es el que decide si corre o no. |
| Tokenización | regex `re.findall` por registro, sets Python; coste menor pero repetido por build. |
| Merge de edges | `dict.fromkeys(existing.evidence + evidence)` por colisión; lineal en evidencia. |
| Por qué quema batería | El build del webgraph se dispara tras ingesta/sync; n≈1000 nodos ya implica ~500k cosenos Python (~30-60 s de CPU pura). |
| Ganancia esperada Rust | Mismo O(n²) pero con matriz + BLAS/SIMD y rayon para paralelizar: **~50-200× wall-clock**; opcionalmente top-k por ANN en vez de fuerza bruta (cambio de complejidad, fase posterior). |

### 2.4 BM25 — hoy repartido (`vault_reader._bm25_search`, `context_enricher/filters.py`)
- Implementación casera sin índice invertido: escanea el corpus completo por query (ver 2.1).
- Rust: índice invertido persistente (tantivy) o BM25 casero sobre postings; pasa de O(corpus) por query a O(postings del término). **10-100× según corpus**, y habilita queries que hoy son inviables.

### 2.5 Ingesta masiva (cold start / sync completo)
Ruta compuesta: `VaultReader.sync()` → parser markdown → chunker → embed batch ONNX → cache put → IDF.
- Cold start real: si no hay cache válido, re-embebe TODO el vault (modelo ONNX domina: minutos).
- Con cache válido, el costo dominante es Python: parseo, fingerprinting SHA-256 por chunk, O(N) puts con re-save JSON del índice (2.2).
- Ganancia Rust: parsing (`comrak`/pulldown-cmark), hashing, IO y serialización nativos; embeddings siguen en ONNX Runtime (mismo coste, ver §7 R2). **Cold start con cache: de segundos a ms salvo inferencia.**

### 2.6 Qué NO es ruta caliente (no portear primero)
- `cli/main.py`, servicios session/documenter/workitems, MCP server: I/O-bound y orquestación.
  Su coste no es CPU de cómputo. Se portean al final (§8 tramo D) o quedan como fachada Python indefinidamente.

## 3. Estrategia de migración incremental vs rewrite total

### Opción A (ELEGIDA): incremental vía PyO3
El núcleo computacional se escribe en Rust como crate `cortex-core` y se expone a Python como
extension-module (`cortex_core._native`) con PyO3 + `numpy` (ndarray views, buffer protocol).
Las clases Python actuales (`VaultReader`, `VectorCache`, `RelationBuilder`, `HybridSearch`)
conservan su API pública exacta; internamente delegan en Rust.

Pros:
- Cada fase entrega valor medible sin romper a los consumidores (MCP server, CLI, tutor, enricher).
- Los tests existentes de caracterización siguen pasando contra la misma fachada → paridad verificable.
- Rollback trivial por fase: desactivar el flag de feature y volver a la ruta Python.
- Permite migrar "la obra entera" eventualmente: cada fase reduce el código Python que queda.

Contras:
- Doble toolchain durante meses (cargo + uv/pip); build de wheels multiplataforma en CI.
- Frontera FFI tiene coste fijo por llamada: hay que diseñar APIs gruesas (batch), no finas
  (nunca llamar Rust por-vector desde Python).
- Riesgo de "Python para siempre" si no se planifica el tramo final (mitigado por §8 tramo E).

### Opción B (DESCARTADA como arranque): rewrite total del CLI+core en Rust
Pros: un solo binario, sin GIL, startup instantáneo, distribución simple.
Contras (por eso no primero):
- El MCP server y los IDE-adapters dependen de Python hoy; reescribirlos de una vez = semanas sin
  releases estables y sin paridad demostrable.
- Sin baseline ni suite de evaluación al día (depende de Obra 04), un rewrite masivo portearía bugs
  y decisiones no validadas (p.ej. dim=384 hardcodeada).
- El dueño quiere batería/rendimiento YA: las rutas calientes son ~5% del LOC pero ~95% del coste CPU.

### Decisión intermedia registrada
CLI en Rust (`clap`) puede avanzar EN PARALELO (tramo D) consumiendo `cortex-core` directamente,
sin pasar por Python. Los servicios orquestadores permanecen en Python hasta el tramo final.

## 4. Decision gates con métricas

Regla general: **todo gate exige benchmark antes/después con el mismo harness y dataset** (§5),
más paridad de resultados. Un gate que falla NO bloquea retroceder: revertir la fase y documentar.

| Gate | Se cruza cuando | Métrica obligatoria | Umbral |
|---|---|---|---|
| G0 — Baseline | harness de bench corre verde en CI local | cold start, retrieve p50/p99, index, webgraph, CPU-time | baseline commiteado |
| G1 — Scoring vectorial en Rust | PR de fase 1 listo | retrieve p50/p99 vs baseline | ≥5× p99 y paridad top-k ≥95% queries |
| G2 — Vector store propio | store binario Rust reemplaza chunks.bin/index.json | cold load + ingesta N=5k chunks | carga <100 ms; ingesta sin curva O(N²); paridad de fingerprints |
| G3 — BM25/índice invertido | BM25 vía Rust (tantivy o casero) | bm25-only query p50/p99 | ≥10× p50; misma relevancia ordenada en eval set |
| G4 — Webgraph | RelationBuilder delega vecinos en Rust | build webgraph n=1k nodos | ≥20× wall-clock; mismos edges (comparación exacta de sets) |
| G5 — Embeddings ONNX en Rust | inferencia sale de chromadb hacia ort/candle | embed batch 512 textos | ≥paridad de velocidad Y similitud coseno ≥0.999 vs ONNX Python |
| G6 — CLI Rust | clap-paralelo feature-complete | startup + comando típico | startup <50 ms; salida idéntica (`--json` diff vacío) |

Criterio de avance entre fases: gate anterior en verde + Obra 01 sin regresiones.

## 5. Plan de benchmarks (baseline ANTES de tocar nada)

Sin baseline no hay migración. El harness se escribe en Python (mide la fachada, que es lo que el
usuario experimenta) y se commitea en `bench/` con resultados versionados.

### 5.1 Estructura
```
bench/
  bench_harness.py      # runner único, CLI: --suite <name> --out results/<tag>.json
  datasets/
    vault-synth-1k/     # vault sintético determinista (~1k docs, seed fija)
    queries-es-en.jsonl # 100 queries con top-k esperado (compartido con Obra 04)
  results/              # JSON inmutables por tag: baseline-2026-08-21.json, fase1-post.json ...
  COMPARE.md            # tabla generada: python bench/bench_harness.py compare a.json b.json
```

### 5.2 Suites a medir
| Suite | Qué mide | Método |
|---|---|---|
| `cold_start` | tiempo hasta primera query servible, proceso nuevo | `time` alrededor de import + `VaultReader.sync()` con cache válido / vacío (dos mediciones) |
| `retrieve` | p50/p99 de 200 `search()` sobre queries del set | `time.perf_counter` por query, warm y cold index |
| `index` | sync completo (parse+chunk+embed+idf) N=1k | una corrida + mediana de 3 |
| `webgraph` | `RelationBuilder.build_edges` con n∈{250,500,1000} registros sintéticos | mediana de 3 corridas por n |
| `bm25` | `_bm25_search(use_embeddings=False)` 200 queries | igual que retrieve |
| `cpu_energy` | tiempo CPU + instrucciones aproximadas | `resource.getrusage(RUSAGE_SELF)` (utime+stime); opcional `perf stat` en Linux; energía ≈ proxy CPU-time (el dueño quiere batería: menos CPU-despierto = menos Wh) |

### 5.3 Reglas de validez
- [ ] Dataset determinista y commiteado: mismos bytes → misma fingerprint → mismo trabajo.
- [ ] Máquina de referencia anotada en cada JSON (CPU, RAM, OS, governor, si corre con batería o AC).
- [ ] Cada medición descarta outliers >p99.9 y reporta n, media, p50, p95, p99.
- [ ] `COMPARE.md` se regenera en cada gate (G0-G6) y se pega en la descripción del PR.
- [ ] Comando concreto de validación:
      `python -m bench.bench_harness --suite all --out bench/results/<tag>.json`
      `python -m bench.bench_harness compare bench/results/baseline-*.json bench/results/faseN-post.json`
- [ ] Gate de paridad usa `datasets/queries-es-en.jsonl`: top-k@5 debe coincidir ≥95% (y para los
      casos divergentes, capturar delta de score para revisión manual).

### 5.4 Primera tarea ejecutable
- [ ] T-BENCH-1: escribir `bench/bench_harness.py` + dataset sintético + capturar `baseline-<fecha>.json`. (M)

## 6. Stack recomendado (crates, workspace, CI)

### 6.1 Crates
| Necesidad | Crate | Notas |
|---|---|---|
| FFI Python | `pyo3` + `numpy` (crate) | extension-module; APIs batch/gruesas |
| Embeddings ONNX | `ort` (onnxruntime bindings) | primera opción: mismo runtime que hoy → paridad fácil (G5). Alternativa `candle` si se quiere 100% Rust, pero exige re-validar el modelo (más riesgo) |
| Búsqueda full-text | `tantivy` | índice invertido + BM25 probados. Alternativa honesta: BM25 casero sobre postings si tantivy pesa demasiado como dependencia — decidir en G3 con benchmark de tamaño binario/tiempo de build |
| Serialización | `serde` + `serde_json` / `bincode` | bincode para stores binarios internos |
| Markdown | `pulldown-cmark` o `comrak` | comrak es compatible-GFM; elegir según frontmatter/wikilinks del parser actual |
| Async/servicios | `tokio` | solo tramo D/E (CLI/servidor); el core numérico es sync |
| Paralelismo | `rayon` | webgraph O(n²), ingesta |
| Memmap | `memmap2` | vector store |
| Hashing | `sha2` | paridad con fingerprints actuales (`compute_fingerprint`) |
| Errores | `thiserror` (lib), `anyhow` (bins) | |
| Bench interno | `criterion` | micro-benchs Rust complementarios al harness Python |

### 6.2 Workspace cargo
```
rust/
  Cargo.toml            # workspace
  crates/
    cortex-core/        # dominio: Chunk, DocType, scoring, BM25, store vectorial, parser
    cortex-embed/       # wrapper ort/candle sobre modelos ONNX (dim paramétrica)
    cortex-py/          # pyo3 extension-module: cortex_core._native (fachada gruesa)
    cortex-cli/         # binario clap (tramo D)
  benches/              # criterion
```
Reglas: `cortex-core` NO depende de pyo3 (testeable puro); `cortex-py` solo adapta tipos.
La dimensión de vectores es parámetro de config, jamás constante (lección de `vector_cache.py:41`).

### 6.3 Build y CI
- Empaquetado Python: `maturin` (pep 517). Dev: `uv run maturin develop --release`.
- CI (se suma a los gates existentes de Obra 01):
  - [ ] `cargo fmt --check && cargo clippy -D warnings && cargo test` en cada PR.
  - [ ] Matriz de wheels: {linux-x86_64, linux-aarch64, macos-x86_64, macos-aarch64, windows-x86_64} vía `maturin-action`/`cibuildwheel`; publicar en cada tag.
  - [ ] Job bench nocturno que corre el harness y falla si p99 empeora >10% vs último gate verde (detección temprana de regresiones).
  - [ ] sccache para tiempos de build razonables.

## 7. Registro de riesgos

| # | Riesgo | Impacto | Mitigación |
|---|---|---|---|
| R1 | **Paridad de resultados**: orden de desempates, float asociativity SIMD vs Python cambian top-k marginal | retrieval distinto sin aviso | eval set ES+EN obligatorio por fase (≥95% top-k@5 igual); tests golden de scores con tolerancia 1e-5; documentar desempates deterministas (por chunk_id) |
| R2 | **ONNX Runtime en Rust** (`ort`): versiones de onnxruntime.dll/so/dylib por plataforma, tokenizers HF | build roto en algún OS; outputs ligeramente distintos | empezar G5 copiando exactamente el modelo ONNX que usa chromadb hoy; comparar salidas bit-a-bit antes de cambiar de modelo; vendor del runtime via `ort` download-binaries; fallback declarado: dejar inferencia en Python y solo portear pre/post-proceso |
| R3 | **chromadb NO portable**: `episodic/memory_store.py` depende de chromadb embebido (pesado, acoplado); no hay camino natural a Rust | bloquea migración entera y distribución | DECISIÓN A TOMAR (tarea T-DEC-1): opciones (a) store propio en `cortex-core` (sqlite + vecino-más-cercano propio o sqlite-vec), (b) qdrant embebido no existe estable → descartado probable, (c) mantener chromadb solo para episodic hasta tramo E. Recomendación preliminar: store propio sqlite-vec/HNSW casero detrás de la MISMA interfaz de MemoryStore, decidido con benchmark en G2 |
| R4 | Dimensión hardcodeada 384 choca con Obra 04 (modelo nuevo puede tener otra dim) | re-trabajo del store | core Rust paramétrico desde día 1; migración de cache con schema_version bump ya previsto en el diseño actual |
| R5 | Frontera FFI fina mata la ganancia (llamadas por-vector) | 0× real pese al porteo | regla de diseño: API batch-only; criterion mide overhead FFI; revisión de PR exige perfil |
| R6 | Doble toolchain frena contribuidores; builds lentos en Windows | fricción dev | maturin develop documentado; wheels precompilados; sccache; CI como única puerta de release |
| R7 | Portear código que Obra 01 va a borrar | esfuerzo desperdiciado | gate de entrada: podado de rutas calientes completado ANTES de cada fase de porteo |
| R8 | Regresión silenciosa del VectorCache (hoy falla en silencio según review) | datos viejos servidos como frescos | el store nuevo debe fallar ruidoso (Result explícito) y test de corruptibilidad |
| R9 | Multiplataforma: paths, permisos, line endings en vaults reales | bugs solo-en-Windows | tests de integración corriendo la matriz CI completa sobre fixture de vault con casos límite (unicode, symlinks, .gitignore)

## 8. Roadmap por tramos con estimación relativa

Estimación relativa: S ≈ horas, M ≈ 1-2 días, L ≈ 3-5 días, XL ≈ >1 semana (de un agente/dev concentrado).

```
Tramo A — Fundación (depende de Obra 01 suite verde)
  A1  Harness de benchmarks + dataset + baseline commiteado        [M]   ← G0, BLOQUEANTE
  A2  Workspace cargo + cortex-core esqueleto + CI cargo           [S]
  A3  Eval set ES+EN compartido con Obra 04                        [M]   ← co-producido con Obra 04

Tramo B — Núcleo caliente vía PyO3 (depende A; B4 depende de Obra 04 decisión de modelo)
  B1  Scoring vectorial en Rust (matriz + SIMD), fachada VaultReader intacta    [L]  ← G1
  B2  Vector store binario propio (reemplaza chunks.bin/index.json)             [L]  ← G2
  B3  Webgraph vecinos O(n²) → rayon + matriz                                   [M]  ← G4
  B4  Embeddings vía ort en Rust (o fallback: pre/post en Rust)                 [XL] ← G5
  B5  BM25/índice invertido (tantivy vs casero, decidir con bench)              [L]  ← G3

Tramo C — Decisión de store episódico (puede solaparse con B)
  C1  Spike sqlite-vec / HNSW propio vs chromadb (benchmark + paridad)          [M]
  C2  Migrar MemoryStore si el spike gana; si no, documentar por qué se queda   [XL]

Tramo D — CLI/servicios (paralelizable desde que cortex-core existe)
  D1  cortex-cli clap consumiendo cortex-core directo                           [L]  ← G6
  D2  Servicios orquestadores: evaluar porteo real vs fachada Python permanente [M] (solo evaluación)

Tramo E — Cierre de migración entera (visión del dueño)
  E1  MCP server sobre tokio en Rust o protocolo hacia core Rust                [XL]
  E2  Eliminar Python del runtime (queda solo para tests/plugins)               [XL]
```

Dependencias externas:
- **Obra 01**: Tramo A completo y cada fase de B requieren podado previo del área a portear (R7).
- **Obra 04**: B4 (embeddings) exige el modelo nuevo YA elegido — no portear dos veces el stack
  vectorial. B1/B2 deben ser paramétricos en dimensión para no bloquearse con esa decisión.
- Obra 05 construye sobre primitivas estables de este obra: su arranque requiere G1+G2 verdes.

## 9. Tareas accionables (checkbox)

Orden estricto de arriba a abajo; una tarea no empieza sin la anterior verificada.

- [x] T-BENCH-1 (A1) ✅ 2026-08-23: harness + dataset (vault-synth-1k seed 42) + `bench/results/baseline-2026-08-23.json` commiteados. Validación corrida verde (todas las suites). Números clave: webgraph O(n²) n1000=3.2s · full_sync_1k=37s · retrieve p99=129ms · import=872ms · bm25 p50=5.6ms.
- [ ] T-CARGO-1 (A2): workspace `rust/` con crates vacíos compilando (`cargo test` verde) + job CI cargo. Validación: `cd rust && cargo clippy -D warnings && cargo test`.
- [ ] T-EVAL-1 (A3): `datasets/queries-es-en.jsonl` con ≥100 queries anotadas (junto a Obra 04). Validación: script que puntúa baseline actual y persiste resultados.
- [ ] T-PY-1 (B1): crate `cortex-core::scoring` + binding batch `cosine_scores(query, matrix) -> Vec<f32>`; `VaultReader.search` usa flag feature `CORTEX_NATIVE=1`. Gate G1: benchmark compare ≥5× p99 y paridad.
- [ ] T-PY-2 (B2): store binario propio (schema v2, dim paramétrica, falla ruidosa) reemplazando VectorCache internamente. Gate G2.
- [ ] T-WG-1 (B3): `_add_semantic_neighbors` delegado a `cortex-core::webgraph`. Gate G4: sets de edges idénticos.
- [ ] T-DEC-1 (C1): spike documentado de store episódico (sqlite-vec/HNSW propio/chromadb queda). Salida: ADR en docs/transformacion/ con números de benchmark.
- [ ] T-EMB-1 (B4): decidir ort vs candle vs pre/post-en-Rust; ejecutar lo decidido. Gate G5.
- [ ] T-BM25-1 (B5): tantivy vs casero, benchmark de build-time/binario incluido en el ADR; implementar. Gate G3.
- [ ] T-CLI-1 (D1): cortex-cli clap feature-par con los comandos usados del estándar de Obra 02. Gate G6.
- [ ] Al cerrar cada gate: actualizar ESTADO-ACTUAL.md con tag de resultado y link al JSON de benchmark.
