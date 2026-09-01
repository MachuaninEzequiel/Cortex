# PROMPT REANUDAR-C — Continuación CIERRE OBRA 07 (post T2-núcleo)

Sos el agente de **CONTINUACIÓN del Cierre Residual de la Obra 07** (migración
Python→Rust de Cortex). Este prompt reemplaza/actualiza a PROMPT-CIERRE-OBRA07.md
para la cola que queda. Reglas vinculantes, guardarrailes y la definición de
hecho de la Obra viven en `docs/transformacion/PROMPT-CIERRE-OBRA07.md` —
LEELO PRIMERO junto con este archivo.

## Contexto en 30 segundos

Cierre residual post-P12: la cola T1–T7 del prompt original está EN CURSO con
**dos agentes en paralelo sobre el MISMO working tree** (rama
`feature/transformacion-2026-08`):

- **AGENTE PRINCIPAL (vos)** — cola: terminar T2 → T4 → T7 (integrador final).
- **AGENTE PARALELO** — T3 ✅ hecha (`e089a25`) y T6 EN CURSO. Su registro:
  `docs/transformacion/progreso-cierre-paralelo.md`. NO tocar:
  `rust/crates/cortex-autopilot/`, `cortex-mcp/src/handlers_autopilot.rs`,
  `rust/crates/cortex-tui/`.

## Estado por tareas (commits en `git log --oneline -16`)

| Tarea | Estado | Evidencia / Commit |
|---|---|---|
| Precondiciones + baseline | ✅ | `538cec4` `c9229f8` |
| T1 handlers MCP no-sesión | ✅ | `21536f5` — gate `bench/parity/cierre_mcp_golden.py` 51 escenarios byte-a-byte vs dispatcher Python real |
| T5 oráculo 100% verde | ✅ | `f6fb828` — **2552 passed 0F 0E** (primera vez desde la recatorización) |
| T2 CLI wireado NÚCLEO | ✅ | `c210cef` + `33871a7` — gate `bench/parity/cierre_cli_golden.py` 19 casos byte-parity post-normalización vs CLI Python real |
| T2-cola (lo que falta de T2) | ⏳ | inventario abajo |
| T3 autopilot service+cli+mcp×5 | ✅ (paralelo) | `e089a25` — su gate: `bench/parity/cierre_autopilot_golden.py` |
| T4 pipeline stage Documentation | ⏳ | TODO TUYO |
| T6 pantalla ratatui sesiones | ⏳ (paralelo) | NO TOCAR |
| T7 refresco documental | ⏳ | **quien termine ÚLTIMO** (tu registro + paralelo) |

Registros de progreso (únicos fuentes de verdad): TU archivo
`docs/transformacion/progreso-cierre.md` (lee la sección "Estado al cierre de
esta sesión" y "Cola restante") y el del paralelo `progreso-cierre-paralelo.md`.

## Lectura obligatoria (en orden)

1. `docs/transformacion/PROMPT-CIERRE-OBRA07.md` (reglas vinculantes + guardarrailes R0–R7 + definición de hecho)
2. Este archivo
3. `docs/transformacion/progreso-cierre.md` COMPLETO (especialmente "T2 — registros", "Estado al cierre", "Cola restante")
4. `docs/transformacion/progreso-cierre-paralelo.md` (qué hizo el otro agente, para no pisarlo)
5. `docs/transformacion/12-AUDITORIA-PYTHON-RESIDUAL.md` §9.2 (mapa de la brecha)

## Precondiciones de arranque (verificar antes de escribir código)

1. `git status` — hay WIP sin commitear de T6 del paralelo (`cortex-tui/*`,
   `Cargo.lock` compartido, `progreso-cierre-paralelo.md`). **NO los
   commitees.** Si tu sesión anterior dejó WIP tuyo, commitealo con prefijo
   `feat(obra07 cierre T…)` y gate verde.
2. `pgrep -af "pytest|cargo|python"` → matar zombis (R0).
3. Exportar R1: `OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2 CARGO_BUILD_JOBS=6`.
4. Baseline del oráculo esperado (registrado en progreso-cierre.md):
   **2552 passed, 21 skipped** (`-p no:randomly`, bajo lock R3).
5. El árbol compila: `cd rust && cargo check --workspace` — si FALLA por
   archivos del paralelo (T6 mid-edit), esperá y reintentá; NO arregles su
   territorio salvo que el fix sea mecánico y se lo dejes anotado en
   progreso-cierre-paralelo.md.

## Guardarrailes de recursos (VINCULANTES)

R0 zombis · R1 threads · R2 verificación por niveles (Nivel 1: fmt+clippy+
test -p <crate>; Nivel 2: goldens build/verify; Nivel 3: suite Python completa
UNA vez por tarea bajo lock R3) · R3 lock `.cortex/heavy.lock` (mkdir loop;
si hay lock huérfano sin proceso vivo, eliminarlo) · R4 `timeout 1200` · R5 un
solo proceso pesado · R6 commit temprano con gate verde prefijado
`feat(obra07 cierre T<n>)` + actualizar progreso INMEDIATO · R7 `git add`
SOLO tus archivos (¡el paralelo comparte el árbol!).

## TU COLA (orden de valor)

### T2-cola — wirear el passthrough restante (mata passthrough salvo CORTEX_PY=1)

Sobre el patrón ya establecido (memory.rs + commands/* + dispatch en main.rs),
wirear:

1. **`docs search` / `docs migrate`** — docs search = enricher estructural
   (filtros P12A-7 + presenters); docs migrate = `cortex-services::migration`
   (P12A-6) ya nativo, es presentación + flags. Ver
   `cortex/cli/docs_search.py` y `cortex/cli/docs_migrate.py` como oráculo.
2. **`ci validate-pr` + `ci open-review-session/report-checkpoint/
   close-review-session`** — nativos en `cortex-app::ci` (P11). El exit code
   es parte del contrato (0/1/2/3). Ver `cortex/cli/ci.py`.
3. **`setup agent|pipeline|full|webgraph|enterprise`** — `cortex-setup`
   (P8) es nativo; los flujos e2e requieren `--non-interactive` (lección T5).
   Ojo: setup full prompt-ea IDE; en gates usar `--non-interactive --ide pi`.
4. **`pr-context store|search|generate|full`** — store/search usan
   `memory.remember`/`retrieve` (glue nativo ya existe); generate usa
   `doc_generator` (P12A-4); full = composición.
5. **`session list/show` TEXTO (tablas rich)** — hoy passthrough deliberado.
   Replicar la tabla rich (bordes box-drawing, wrap con ellipsis, ancho de
   columnas) es frágil; decidir: replicar o documentar como única deuda UX.
6. **`mcp-serve`** — wirear el servidor nativo `cortex-mcp::server` con
   TODOS los backends (sessions P12A-9 + search/docs/spec/finish T1 +
   autopilot T3-paralelo). Gate: intercambio JSON-RPC stdio mínimo
   (initialize/list_tools/call_tool) contra el server Python real.
7. **`search-vector` NO existe como comando CLI** (solo tool MCP) — no wirear;
   ya documentado.

**Gate**: EXTENDER `bench/parity/cierre_cli_golden.py` con ≥2 casos por
subcomando nuevo (texto + --json contra el CLI Python real). Normalizaciones
pactadas ya implementadas: {{ROOT}} {{TS}} {{ELAPSED}} {{RUN}} {{MEMID}}
{{SHA}} + scores a 4 decimales. Cold start release N=20 por subcomando.

### T4 — pipeline stage Documentation (stub → real)

`cortex-pipeline` (P12B-6) dejó la stage Documentation como stub hasta tener
documenter nativo — ya existe (P5). Conectarla al persister/reconstructor
nativo. **Gate**: ampliar `bench/parity/pipeline_golden_p12b.py` con flow
Documentation pass/fail.

### T7 — refresco documental (solo cuando T2-cola+T4 estén verdes y el paralelo haya cerrado T6)

Actualizar `ESTADO-ACTUAL.md` (tabla de fases + "lo que todavía depende de
Python" reducido a lo REAL), `HANDOFF.md` (nueva sección HANDOFF ACTIVO
post-cierre), doc 12 §9.2 (marcar ítems resueltos). Integrar AMBOS registros
de progreso. Anunciar **"OBRA 07 — CIERRE COMPLETO"** con métricas
(subcomandos wireados, familias MCP in-process, cold start, estado del
oráculo). NO ejecutar la baja definitiva de Python (paso siguiente separado).
**Cargo.lock compartido**: si sigue con hunks mixtos al cierre, integrarlo
entero en el último commit (anotar en HANDOFF).

## Patrones técnicos críticos (aprendidos en T1/T2 — no reinventar)

- **Writers JSON**: `crate::pyjson` (cortex-cli) tiene `stdlib_dumps_indent2`
  (ensure_ascii), `pydantic_dumps_indent2` (UTF-8 crudo, para
  `model_dump_json`) y `stdlib_dumps_compact_array` (una línea). Pydantic
  serializa datetimes UTC con sufijo **Z** (no +00:00) — convertir al dump.
- **Orden de campos**: siempre = orden de declaración pydantic (verificable
  con `list(Model.model_fields.keys())`). Computed fields (display_*) van al
  FINAL del dump.
- **Glue de memoria**: `cortex-cli/src/memory.rs` (NativeMemory::open con
  `open_without_embeddings` para comandos sin retrieval). Patrón de
  resolución de rutas: `cortex-webgraph-server/src/sources.rs`.
- **matched_by**: orden pyset CPython seed-0, tabla precomputada
  `pyset_strategy_order` en cortex-app/src/context/mod.rs. NO volver a
  ordenar alfabético.
- **Errores como texto de tool vs excepción**: los ❌ son Ok-texto; las
  excepciones Python → `Error ejecutando {name}: {msg}` (dispatcher) o
  traceback rich (CLI) — los tracebacks rich NO son contrato portable
  (precedente: S19 retirado del gate con justificación).
- **Scores float**: drift ~1e-7 entre SIMD chroma/ONNX y cómputo nativo —
  normalizar a 4 decimales en gates; rankings exactos son el contrato.
- **IDs/shas aleatorios del fixture**: mem_{uuid8} → {{MEMID}}, SHA git → {{SHA}}.
- **Session**: `SessionService` native es `&self` en todos sus métodos
  (interior mutability); `SessionStorage::new(layout.sessions_dir())`.
- **Autopilot del paralelo**: `commands/autopilot.rs` es de ELLOS; si tocás
  cortex-cli y compila mal por ese archivo, esperá/reintentá.

## Verificación (SIEMPRE)

- Nivel 1: `cargo fmt --all --check && cargo clippy -p <crate> --all-targets -- -D warnings && cargo test -p <crate>`
- Nivel 2: `cierre_cli_golden.py build|verify` (+ los gates que amplíes)
- Nivel 3 (una vez por tarea, bajo lock R3):
  `.venv/bin/python -m pytest tests/unit tests/integration tests/e2e --no-cov -p no:randomly` → esperado **2552 passed, 21 skipped**
- Commits: `feat(obra07 cierre T2|T4): …` + docs separado con evidencia.

## Definición de hecho para esta continuación

T2-cola y T4 completas con gates verdes + suite Python 100% verde +
passthrough CLI reducido a SOLO rollback CORTEX_PY=1 (+ deuda UX documentada
si la tabla rich queda sin replicar). T7 integra ambos registros y anuncia
"OBRA 07 — CIERRE COMPLETO" con métricas. T6 la cierra el paralelo.
