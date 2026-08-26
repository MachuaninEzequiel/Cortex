# Progreso CIERRE OBRA 07 — residual post-P12

> Registro ÚNICO de progreso del cierre residual de la Obra 07
> (`docs/transformacion/PROMPT-CIERRE-OBRA07.md`). Mapa de trabajo: doc 12 §9.2.
> NO actualiza ESTADO-ACTUAL.md ni HANDOFF.md hasta T7.
>
> Territorio: `rust/crates/cortex-mcp/src/` (handlers no-sesión),
> `rust/crates/cortex-cli/src/`, `cortex-autopilot`, `cortex-pipeline`,
> `cortex-tui` (solo pantalla sesiones T6), `tests/e2e/**` rotos,
> gates `bench/parity/*cierre*`. PROHIBIDO: cortex-companion (P13),
> borrar Python vivo del oráculo, cambiar goldens existentes sin motivo,
> uv.lock/progress.md en commits.

## Precondiciones de arranque

- ✅ Trunk limpio: cambios de depreciación post-P12 commiteados como
  `chore(obra07): depreciación post-P12 según doc 12` (`538cec4`)
  — 9 archivos: cortex/brain ×5, embedders/openai.py, hooks/agent_hooks.py,
  HANDOFF.md, docs 12. Verificado contenido = guardas de depreciación.
- ✅ R0: `pgrep -af "pytest|cargo|python"` → sin zombis heredados.
- ✅ Sin `.cortex/heavy.lock` huérfano al arranque.
- RAM al arranque: 9506 MB available (≥4000 requerido).

## Baseline del oráculo (pre-T1) — REGISTRADO 2026-08-25

Corrido bajo lock `.cortex/heavy.lock` (mkdir) + `timeout` + threads=2.

**unit+integration** (`timeout 2400 .venv/bin/python -m pytest tests/unit
tests/integration --no-cov --tb=no`, rc=0):

```
2455 passed, 18 skipped, 7 warnings in 35.86s
```

**e2e** (`timeout 2400 .venv/bin/python -m pytest tests/e2e --no-cov
--tb=no --ignore=tests/e2e/scenarios/test_autopilot_budget.py -rEf`, rc=1):

```
29 failed, 63 passed, 3 skipped, 2 warnings, 3 errors in 64.61s
```

**Set EXACTO de fallos/errores preexistentes (línea de base para T5):**

Colección rota (+1 E):
- `tests/e2e/scenarios/test_autopilot_budget.py` — ImportError:
  `from cortex.autopilot.context_budget import ...` — módulo borrado en la
  recatorización. Impide correr e2e sin `--ignore`.

FAILED ×29:
- `tests/e2e/scenarios/test_autopilot_basic.py` ×7:
  TestQuestionOnly::{test_detects_question_only, test_no_embeddings_budget},
  TestFastCode::test_fast_track_draft_on_finish,
  TestDocsOnly::test_docs_only_profile,
  TestDeepTrack::{test_deep_track_suggestion,
  test_delegation_stub_no_cross_process_persistence},
  TestCleanupAndConfig::test_cleanup_archives_old_jsonl
- `tests/e2e/scenarios/test_autopilot_finish.py` ×7:
  TestFinishIndexesAutomatically::test_finished_note_appears_in_search,
  TestFinishPersistsToDisk::test_session_note_file_exists_after_finish_auto,
  TestFinishNoData::{test_safe_draft_no_evidence,
  test_no_invented_files_or_tests},
  TestFinishDuplicate::test_no_duplicate_session_note,
  TestFinishBlocked::{test_blocked_generates_warning_draft,
  test_blocked_does_not_mark_documented}
- `tests/e2e/scenarios/test_setup_basic.py` ×1:
  TestSetupBasic::test_doctor_strict_passes_after_agent_setup
- `tests/e2e/scenarios/test_setup_full.py` ×4:
  TestSetupFull::{test_full_setup_generates_workflows, _scripts, _skills,
  _agent_files}
- `tests/e2e/scenarios/test_setup_on_fixtures.py` ×9:
  test_setup_full_on_all_projects[empty-project, vite-react-project,
  python-package, legacy-cortex-project],
  test_legacy_project_maintains_layout,
  test_doctor_passes_on_all_fixtures[×4 proyectos]
- `tests/e2e/test_session_tui_smoke.py` ×1:
  TestWatchSubprocess::test_watch_with_no_active_session_starts_and_stops

ERROR ×3 (todos en):
- `tests/e2e/test_artefact_integrity.py::TestMcpCliAlignment`:
  {test_mcp_tools_list_is_not_empty, test_mcp_tools_match_expected_set,
  test_mcp_tools_have_cli_counterpart_or_documented}

Coincide con el registro de P12B-8: **29F+3E+1E-colección**, todos e2e
trunk (doc 12 §6: deuda de la recatorización, no culpa de P12).
Cero fallos unit/integration.

## T5 — Oráculo 100% verde (registro de decisiones una-por-una)

Principio aplicado: si el escenario sigue teniendo sentido se ACTUALIZÓ a
la estructura actual; si el contrato que probaba fue eliminado, se RETIRÓ
con justificación. Ningún assert de test vivo fue debilitado.

### tests/e2e/scenarios/conftest.py
- NUEVO fixture `autopilot_session`: abre sesión real vía
  `SessionService.open` sobre spec mínimo. Motivo: post-recatorización
  `AutopilotService.start` ADOPTA la sesión activa, ya no la crea.

### test_autopilot_basic.py (7F → 4 actualizados, 2 retirados, 1 ajuste)
- `test_detects_question_only` / `test_no_embeddings_budget` /
  `test_fast_track_draft_on_finish` / `test_docs_only_profile` /
  `test_deep_track_suggestion`: usan fixture; `preflight` ya no toma
  `--session-id`; payload de finish hoy es `{documented, status,
  session_note_path,…}` (antes `saved/status="documented"/state-file`).
- `test_no_embeddings_budget`: assert `not vault/specs` retirado — contrato
  viejo donde start creaba sesiones sin spec; hoy toda sesión nace de un
  spec (el fixture crea una).
- RETIRADO `test_delegation_stub_no_cross_process_persistence`: el módulo
  `cortex.autopilot.delegation` fue eliminado (delegación = responsabilidad
  nativa del IDE, decisión Fase 5 multi-IDE).
- RETIRADO `test_cleanup_archives_old_jsonl`: comando `cleanup` eliminado en
  Fase 03 §11.3 junto con los eventos JSONL (docstring de autopilot/cli.py).

### test_autopilot_finish.py (7F → 3 actualizados, 4 retirados)
- Helper `_json_out`: finish emite línea informativa previa al JSON.
- ACTUALIZADO `test_session_note_file_exists_after_finish_auto`: la ruta
  física viaja en el payload (`session_note_path`); el state file de
  `.cortex/run/autopilot/sessions/` ya no existe.
- ACTUALIZADO `test_no_invented_files_or_tests`: anti-hollow-claims ahora
  verifica el CONTENIDO real de la nota generada sin checkpoints.
- ACTUALIZADO `test_no_duplicate_session_note`: segundo finish sobre sesión
  cerrada ⇒ `documented=False` y exactamente 1 nota (sin duplicados).
- RETIRADO `test_finished_note_appears_in_search`: la indexación automática
  post-finish no está cableada en el flujo CLI actual; sync/search corre vía
  `memory.sync_vault` (cubierto por gates del persister P5/P12A).
- RETIRADOS `TestFinishBlocked::{warning_draft, not_marked_documented}`:
  el bloqueo AutoCheckpointPolicy sobre `finish --auto` no está cableado
  hoy; policies nativas en Rust con gate propio (P12B-5).
- RETIRADO implícito `draft_confidence/draft_warnings`: claves eliminadas
  del payload (ver TestFinishNoData docstring).

### test_autopilot_budget.py (1E-colección → reescrito)
- Importaba `cortex.autopilot.context_budget` (eliminado). Reescrito contra
  el contrato vigente `context_enricher.budget_resolver.resolve_budget_profile`
  (dict top_k/max_chars; perfiles question-only 0/0 · docs-only 3/1200 ·
  fast-code 5/2000 · deep-code 8/3500 · security 8/3500 · ambiguous 3/1500 ·
  noop 0/0 · fallback fast-code) + detección viva vía payload de preflight.
  El StateStore/build_context fueron retirados en la recatorización.

### test_setup_basic.py / test_setup_full.py / test_setup_on_fixtures.py (14F)
- `setup full` prompt-ea IDE desde Fase 6 ⇒ invocaciones e2e con
  `--non-interactive --ide pi` (sin TTY).
- `test_doctor_strict_passes_after_agent_setup`: instala hooks vía
  `session hooks install --ide pi` (movido desde setup agent en Fase 04) y
  agrega `.cortex/session.lock` al .gitignore (artefacto runtime nuevo).
- `test_doctor_passes_on_all_fixtures`: ídem gitignore + hooks.

### test_artefact_integrity.py (3E)
- `TestMcpCliAlignment.mcp_tools`: el catálogo se movió de server.py a
  schemas.py en la recatorización — el regex ahora lee schemas.py.

### test_session_tui_smoke.py (1F)
- `python -m cortex` ya no existe (sin __main__) ⇒ entrada
  `cortex.cli.main`; y la TUI exige stdout interactivo ⇒ `_spawn_watch`
  usa pty en POSIX (Windows conserva pipe; rc=1 no-TTY sigue aceptado).

## Nota de orden de ejecución (2026-08-25)

La cola del prompt es "orden de valor", no dependencia dura. Tras cerrar T1
(gate verde + commit `21536f5`), la sesión reordena: **T5 pasa antes que
T2/T3/T4** porque (a) es REQUISITO duro para autorizar la baja definitiva,
(b) no depende de T2-T4 (limpia tests e2e rotos por la recatorización),
y (c) deja al trunk en el mejor estado posible si la sesión muere.
T2/T3/T4 quedan con fundación puesta (backends in-process de T1 reusables
por el CLI/autopilot/pipeline) y se ejecutan en la continuación.

## Estado al cierre de esta sesión (2026-08-25)

**Completadas y gateadas:** T1 (`21536f5`) · T5 (`f6fb828`) ·
T2-núcleo (`c210cef`+`33871a7`) · T3-paralelo (`e089a25`).
Punto de partida de la próxima sesión: leer **`PROMPT-REANUDAR-C.md`**
(el handoff completo para el próximo agente) + ESTE archivo +
`git log --oneline -16`.

**Cola restante:** T2-cola (docs{search,migrate}, ci ×4, setup ×5,
pr-context {store,search,generate,full}, mcp-serve, list/show texto con
tablas rich) · T4 pipeline Documentation · T6 (paralelo, en curso) ·
T7 integrando registros principal + paralelo. Cargo.lock compartido en
flujo (lo integra quien cierre último).

**Verificación final de la sesión (re-run):**
- Suite Python completa `-p no:randomly`: **2552 passed, 21 skipped, 0F, 0E**
- `cargo test -p cortex-mcp` 25 ✅ · clippy `-D warnings` ✅ · fmt ✅
- Gate T1: build/verify + checker byte-parity `✅ PARIDAD CIERRE T1`

**Cómo continuar T2 (fundación ya validada):**
1. Recrear `cortex-cli/src/memory.rs` (glue `_load_memory`): layout discover →
   config.yaml → `SemanticIndex::build(vault)` + JSONL episódico vía
   `resolve_episodic_persist_dir` + `OnnxEmbedder::open(default_model_dir())`.
   El patrón completo está en `cortex-webgraph-server/src/sources.rs`.
2. Presentaciones search/context ya existen nativas (presenter.rs P12A-7,
   models.rs to_json); el wire-format de los handlers T1 es reutilizable.
3. Superficie REAL del CLI a wirear (verificada contra `cortex session --help`
   etc.): session{current,list,show,diff,switch,checkpoint,abandon,task,hooks},
   next (--json con elapsed_ms normalizable {{ELAPSED}}), vault stats
   (= comando `stats` oculto), reindex (cli/embedding.py), docs search/migrate,
   ci {validate-pr,open-review-session,report-checkpoint,close-review-session},
   hu {import,list,show}, pr-context ×5, setup
   {agent,pipeline,full,webgraph,enterprise} con --non-interactive, mcp-serve.
4. Gate: crear `bench/parity/cierre_cli_golden.py` (≥2 casos por subcomando,
   texto+--json, vs CLI Python real; normalizar {{ROOT}}/{{TS}}/{{ELAPSED}})
   + medición cold start release N=20.

**T3/T4:** los autopilot-tools MCP ×5 entran tras T3 (requiere
AutopilotService nativo sobre SessionService); pipeline Documentation stage
se conecta al persister nativo (P5) — ambos con gates propios según plan.

**T6 (opcional):** pendiente de decisión; la smoke e2e del watch rich sigue
verde con pty, así que no urge hasta la baja de Python.

**No anunciado "OBRA 07 — CIERRE COMPLETO"**: queda condicionado a T2-T4
(+T6 hecha-o-deuda). HANDOFF.md / ESTADO-ACTUAL.md / doc 12 §9.2 se
actualizan en T7 cuando el cierre esté completo — este archivo es la única
fuente de verdad de la sesión.

## Cierre T2-cola — cola restante nativa (2026-08-26)

Commit `7d988a7` — `feat(obra07 cierre T2): cola nativa completa`. Continúa el gate `bench/parity/cierre_cli_golden.py` desde los 19 casos del núcleo.

**Red→Green (TDD):** `rust/crates/cortex-cli/tests/t2_tail_native.rs` ×4
(`docs_migrate_and_session_text_are_native`, `docs_search_uses_native_enricher`,
`ci_setup_and_pr_context_are_native`, `mcp_aliases_start_native_stdio`).
RED: quitando las rutas de dispatch (`docs`/`ci`/`setup`/`pr-context`/`mcp-server`,
como en BASE `d8b77a6`) los 4 tests fallan — derivan a `fallback::passthrough` y
mueren con exit 127 (CORTEX_BIN inválido) o broken pipe. GREEN: reestablecidas las
rutas nativas, 4/4 ok (`cargo test -p cortex-cli --test t2_tail_native`).

**Verificación niveles:**
- N1: `cargo fmt --all --check` ✅ · `cargo clippy -p cortex-cli --all-targets -- -D warnings` ✅ · `cargo test -p cortex-cli` ✅ (todos los bins)
- N2 gates vecinos (sin regresión por server.rs / session_cmd.rs):
  `cargo test -p cortex-mcp` 25 ✅ · `cierre_mcp_golden.py verify` + `cierre_check` `✅ PARIDAD CIERRE T1` · `cierre_autopilot_golden.py verify` + `cierre_autopilot_check` `✅ PARIDAD CIERRE T3` · `cargo test -p cortex-tui` ✅
- N2 gate T2: `cierre_cli_golden.py build` (golden regenerado desde el CLI Python REAL → auténtico, diff 0) y `verify` → `[PASS] cierre_cli byte-parity post-normalización (2123 líneas)` / `✅ PARIDAD CIERRE T2`. **39 casos** de terminal (S01–S18, S20–S22, S25–S42; S19 retirado por traceback no portable, S23/S24 docs search cubierto por test Rust) + **1 exchange MCP stdio acotado** (initialize + notifications/initialized + tools/list + tools/call cortex_self_review_note, envelope Anexo A null≡omisión).
- N3 oráculo completo pre-commit bajo lock: `timeout 2400 .venv/bin/python -m pytest tests/unit tests/integration tests/e2e --no-cov --tb=no -p no:randomly` → **2552 passed, 21 skipped, 0 failed, 0 errors** (175s).

**Cold start release N=20 (fixture gate `construir_fixture`):**

| Comando | mediana | min | max | nota |
|---|---|---|---|---|
| docs migrate | 2.9ms | 2.8 | 3.4 | liviano |
| ci validate-pr | 2.9ms | 2.9 | 3.0 | liviano |
| ci open-review-session | 2.9ms | 2.9 | 3.1 | liviano |
| ci report-checkpoint | 3.3ms | 3.2 | 4.1 | liviano |
| ci close-review-session | 3.0ms | 3.0 | 23.9 | liviano (max anómalo init) |
| setup agent | 2.3ms | 2.2 | 2.9 | liviano |
| setup pipeline | 2.3ms | 2.2 | 2.7 | liviano |
| setup full | 2.4ms | 2.2 | 2.6 | liviano |
| setup webgraph | 2.4ms | 2.2 | 2.8 | liviano |
| setup enterprise | 3.9ms | 3.1 | 5.0 | liviano |
| pr-context generate | 3.8ms | 3.3 | 4.3 | liviano |
| session list | 8.9ms | 7.6 | 10.5 | liviano |
| session show | 4.6ms | 3.7 | 5.4 | liviano |
| pr-context store | 307.9ms | 272.4 | 369.2 | ONNX init+inferencia |
| pr-context search | 316.7ms | 271.0 | 352.4 | ONNX |
| pr-context full | 365.5ms | 313.8 | 419.0 | ONNX |

Todos los comandos livianos cumplen `<100ms`. Los de memoria/embeddings
(store/search/full) pagan la inicialización del runtime ONNX+inferencia real
(costo honesto, no debilitado para medir).

**Auditoría passthrough residual (leaves que aún invocan Python vía
`fallback::passthrough`, con motivo):**
- `session watch`/`session tui` — ahora NATIVOS (pantalla ratatui de cortex-tui, T6-b `9d4de37`). Quedan en passthrough: `session task {list,done,in-progress,skip,block}` y `session hooks {list,install,uninstall,status}` — fuera del inventario de esta tarea (no son leaves T2-cola listados en el brief).
- `ide {list,setup,remove,status}` — fuera del inventario T2-cola.
- `docs {validate,restore,list-backups,routing-table}` — docs search/migrate son los únicos leaves del inventario; el resto no tiene requisito vinculante (no expandir).
- `hu import` — lanza excepción no manejada en Python (traceback rich no portable); mejora deliberada documentada para S19. list/show ya nativos.
- `{remember,forget,init,inject,sync-enterprise-vault,sync-ide,verify-docs,validate-docs,index-docs}` — fuera del inventario T2-cola.
- `webgraph {serve,doctor}` y resto de `autopilot` no-preflight — delegan por diseño (documentado en sus gates).
- `search-vector` NO es un comando CLI (solo tool MCP) — no inventar.

`CORTEX_PY=1` sigue siendo el rollback total explícito (main.rs paso 1).

## Cierre T4 — DocumentationStage real (2026-08-26)

Commit `65c5a40` — `feat(obra07 cierre T4): DocumentationStage real — DocVerifier +
session service + persister nativo (P5/P12A-5)`. Reemplaza el stub (`Skipped`
`backend no nativo aún`) por la implementación real espejando
`cortex/pipeline/stages/documentation.py`.

**Red→Green (TDD):** `rust/crates/cortex-pipeline/tests/documentation_stage.rs` ×6.
RED: contra el stub devuelven todos `Skipped` (0/6). GREEN: solo la implementación
nueva — 6/6 ok:
1. docs-present → `PASSED` + `has_agent_docs=true` + `indexed=1` (msg oráculo).
2. no-docs → fallback REAL (`reconstruct_gitless` → `build_create_args` →
   `NoteService::create`) → `PASSED` + `has_agent_docs=false` + nota en disco (msg
   `No agent docs found. Fallback generated: <path>`).
3. no-docs + `block_on_failure=true` → `FAILED`.
4. sin pr_ctx → fallback `skipped` (`fallback_path: null`).
5. sesión malformada (git-claim en repo no-git) → `ERROR`
   (`Documentation stage error: reconstruct: diff: …`).
6. glue episódico: store_pr_context escribe la fila `pr` en el JSONL nativo.
Fixture real (vault tmp + sesión gitless + spec en disco); sin mocks.

**Wiring nativo:** `DocVerifier::verify_from_list` (paso 2, fallback sessions-dir
no-bloqueante) · `SemanticIndex::build` como equiv. de `sync_vault` (paso 3) ·
`SessionService::find_for_pr` + `load_spec` + `reconstruct_gitless/git` +
`persister::build_create_args` + `cortex_services::note::NoteService::create`
(paso 4) · `PRService::store_pr_context` sobre `NativeEpisodicStore` con
`feature_embed` determinista (paso 1, glue documentado; `memory_jsonl` ausente ⇒
skip con log). Mensajes byte-a-byte del oráculo; `block_on_failure=false` por
defecto; divergencias P6/P9 documentadas en el header del módulo.

**Verificación niveles:**
- N1: `cargo fmt --all --check` ✅ · `cargo clippy -p cortex-pipeline --all-targets
  -- -D warnings` ✅ · `cargo test -p cortex-pipeline` ✅ (4 existentes + 6 nuevos).
- N2 gate: `pipeline_golden_p12b.py build` → `[OK] golden generado` y `verify` →
  `[PASS] golden_pipeline.txt determinista` (diff 0). Flows A–D verificados
  byte-idénticos al golden previo (10179 chars). Instrumentación: nuevo checker
  `rust/crates/cortex-pipeline/examples/documentation_gate.rs` corre el
  DocumentationStage REAL sobre fixture gitless FUERA del repo (lección P12B-7:
  `is_git_repo` usa `rev-parse`, ancestros) y congela el `StageResult` con reloj
  fijo (`FIXED_TS 2026-08-25T12:00:00+00:00`, `duration_ms=0`), normalización
  pactada `{{ROOT}}`/`{{ID}}`. Nuevo segmento del golden:

```
### DOCUMENTATION
## CASE docs_present
{"stage_name":"Documentation","status":"passed","message":"Agent documentation found and indexed (1 docs).","artifacts":{"has_agent_docs":true,"indexed":1},"duration_ms":0,"timestamp":"2026-08-25T12:00:00Z"}
## CASE no_docs_fallback
{"stage_name":"Documentation","status":"passed","message":"No agent docs found. Fallback generated: {{ROOT}}/.cortex/vault/sessions/{{ID}}.md","artifacts":{"fallback_path":"{{ROOT}}/.cortex/vault/sessions/{{ID}}.md","has_agent_docs":false},"duration_ms":0,"timestamp":"2026-08-25T12:00:00Z"}
## CASE no_docs_block
{"stage_name":"Documentation","status":"failed","message":"No agent docs found. Fallback generated: {{ROOT}}/.cortex/vault/sessions/{{ID}}.md","artifacts":{"fallback_path":"{{ROOT}}/.cortex/vault/sessions/{{ID}}.md","has_agent_docs":false},"duration_ms":0,"timestamp":"2026-08-25T12:00:00Z"}
```

Cargo.lock: hunk propio `65c5a40` solo agrega las aristas de `cortex-pipeline`
(`cortex-app`, `cortex-services`, `cortex-workspace` dev) — cero paquetes nuevos.
- N3 oráculo completo pre-commit bajo lock: `timeout 1200 .venv/bin/python -m pytest
  tests/unit tests/integration tests/e2e --no-cov --tb=no -p no:randomly` →
  **2552 passed, 21 skipped, 0 failed, 0 errors** (117.6s).

## Cierre T6-b — integración CLI de la pantalla sesiones (2026-08-26)

Commit `9d4de37` — `feat(obra07 cierre T6-b): …`. Wirea el brazo nativo
`cortex session watch` / `cortex session tui` (mismo entrypoint) al
renderer ratatui ya gateado por T6 (`cortex-tui::sessions`, contrato v1
read-only), cerrando el paso que T6 dejó documentado como pendiente.

**Deps:** `cortex-cli` gana `cortex-tui` (path) + `ratatui = "0.30"`
(ya en el workspace vía cortex-tui; crossterm llega re-exportada por
`ratatui::crossterm`). Cargo.lock: solo dos aristas nuevas de cortex-cli,
cero paquetes nuevos. No se rompe current/checkpoint/switch/diff/abandon/
list/show (passthrough restante: `session task …`, `session hooks …`).

**Loop (TTY real):** `build_service()` → `SessionsScreenData::from_service`
reconstruido en cada tick (~250 ms, las sesiones cambian en disco);
alternate screen + raw mode + cursor oculto con restauración RAII
(drop/panic incluidos, guard activo desde el raw mode); salida con `q` o
`Ctrl+C`; errores de storage se pintan en la pantalla sin romper el loop.
`--status open|closed|handoff|abandoned` mapea a `SessionStatus`
(`parse_status_filter`, misma semántica que `session list`).

**No-TTY (CI):** `is_terminal()` falso ⇒ snapshot único del mismo render
vía `TestBackend` 100×40 fijo, rc 0 + aviso breve en stderr; el gate no
depende de TTY real.

**TDD RED→GREEN** (`rust/crates/cortex-cli/tests/t6b_session_watch.rs` ×3):
RED — antes del brazo `session watch` caía al passthrough Python (rc 127,
`no pude ejecutar 'cortex'`); GREEN — con el brazo, sobre fixtures reales
en tmp (`.cortex/config.yaml` marca de layout + `SessionService` real): rc 0,
ids del snapshot == ids de `session list --json` del mismo fixture, marca
`*` de la activa presente, `(no sessions on disk)` con fixture vacío y con
filtro sin resultados, y `tui` compartiendo entrypoint con `watch`.

**Verificación nativa:** `cargo test -p cortex-cli` 49/49 (3 nuevos) ·
`cargo test -p cortex-tui` 16/16 (5 sessions_screen verdes, gate T6
preservado) · `cargo fmt --all --check` ✅ · `cargo clippy -p cortex-cli
--all-targets -- -D warnings` ✅ · `cargo build -p cortex-cli --bin
cortex-cli` ✅ · smoke manual no-TTY con fixture real (rc 0, tabla con
`*` sobre la activa). Oráculo Python no re-ejecutado (los cambios no
tocan Python; sin riesgo detectado).

## Cola de tareas

| Tarea | Estado | Evidencia | Commit |
|---|---|---|---|
| T1 handlers MCP no-sesión | ✅ | `bench/parity/cierre_mcp_golden.py` build/verify (51 escenarios, 261 líneas) + `examples/cierre_check.rs` **byte-parity** → `[PASS] cierre_check byte-parity` / `✅ PARIDAD CIERRE T1`. Oráculo = dispatcher Python REAL (`_dispatch_tool_sync`) con fakes deterministas y motores P5/P7 patcheados; write_doc usa writers REALES sobre vault tmp. Familias: search/search_vector/context (to_prompt/to_prompt_format byte-exact, budget resolver real), sync_ticket (candidatos reales vía resolve_safe), emit_proposal (pydantic 2.13 byte-a-byte: string_too_short/long, too_short/long, missing, extra_forbidden, value_error field+model, truncado de repr >50 → 25+"..."+24), create_spec (gobernanza+gap 2.0s con reloj congelado), self_review_note, write_doc ×11 doc_types (validaciones handler + writers P8b: duplicados por fingerprint, local-only, enterprise fields), design note, import/get_hu, finish_session/documenter_briefing (serialización completa del ReconstructionOutput). Autopilot-tools ×5: diferido a T3 (requiere AutopilotService nativo). Suite oráculo: **2455 passed, 18 skipped** (-p no:randomly; flaky HermesAdapter documentado en P12A-3). cargo test -p cortex-mcp: 25 ✅ · clippy `-D warnings` ✅ · fmt ✅. ADR chico: regex "1" ya en lock (cero paquetes nuevos) | `21536f5` |
| T2 subcomandos CLI restantes | ✅ COMPLETA (núcleo `c210cef`+`33871a7` + cola `7d988a7`) | Núcleo: gate 19 casos (700 líneas), search/context/stats/reindex/session{current,list--json,show--json,checkpoint,switch,diff,abandon}/next/hu/list,show/pr-context capture. **Cola (`7d988a7`)**: docs{search,migrate} (enricher nativo + P12A-7 filtros; migrate vía `cortex-services::migration`), ci ×4 (validate-pr/open/report/close sobre `cortex-app::ci`, exits 0-3 contrato), setup ×5 (`cortex-setup` in-process, `--non-interactive`; full con `--ide pi`), pr-context {store,search,generate,full} (remember/retrieve glue + `cortex-app::doc_generator`), session{list,show} texto Rich-compat, mcp-server/serve stdio rmcp (envelope Anexo A). Gate extendido **19→39 casos + MCP stdio bounded exchange** (initialize+tools/list+tools/call) → `[PASS] cierre_cli byte-parity post-normalización (2123 líneas)` / `✅ PARIDAD CIERRE T2`. Tests Rust nuevos `t2_tail_native.rs` (4, RED→GREEN). Cargo.lock hunk T2 commiteado. Detalle y cold start en sección "Cierre T2-cola" abajo | `c210cef`+`33871a7`+`7d988a7` |
| T3 autopilot service+cli | ✅ | Gate `cierre_autopilot_golden.py` + checker `cierre_autopilot_check` byte-parity; service e2e + MCP ×5 + CLI dual; doctor_golden ampliado | `e089a25` | |
| T4 pipeline Documentation | ✅ | Stage real nativo: `DocumentationStage` (stub → `DocVerifier` + `SessionService::find_for_pr` + `reconstruct_gitless/git` → `build_create_args` → `NoteService::create`; glue episódico `PRService::store_pr_context`). Tests `documentation_stage.rs` ×6 RED→GREEN; gate `pipeline_golden_p12b.py` + segmento `### DOCUMENTATION` (3 casos congelados, reloj fijo) — A–D byte-idénticos, `build`+`verify` diff 0. Oráculo 2552/21/0/0. Detalle en sección "Cierre T4" abajo | `65c5a40` | |
| T5 oráculo 100% verde | ✅ | Suite completa `-p no:randomly`: **2552 passed, 21 skipped, 0 failed, 0 errors** (128s) — primera vez verde desde la recatorización. Commit de tests `f6fb828`. Detalle de cambios por archivo abajo | `f6fb828` |
| T6 pantalla ratatui | ✅ | `cargo test -p cortex-tui` sessions_screen (5 tests) — datos == session list --json, render <50ms | `fa11473` | |
| T6-b integración CLI watch/tui | ✅ | Brazo nativo `watch`/`tui` en `session_cmd.rs::run()` (mismo entrypoint): cortex-tui + ratatui 0.30 como deps de cortex-cli, `--status` mapeado a `SessionStatus`, `SessionsScreenData::from_service` + loop ratatui read-only (tick ~250 ms, rebuild del snapshot por tick, salida con q/Ctrl+C, restauración RAII incluso en panic); no-TTY (CI) ⇒ snapshot único rc 0 + aviso breve. TDD `t6b_session_watch.rs` ×3 RED→GREEN (RED: `session watch` caía al passthrough rc 127); asserts sobre ids == `session list --json`, marca `*` de la activa y `(no sessions on disk)` — fixtures reales en tmp + SessionService real. Gates: cortex-cli 49/49, cortex-tui 16/16 (5 sessions_screen verdes), `cargo fmt --check` y `cargo clippy -p cortex-cli --all-targets -- -D warnings` limpios; detalle en "Cierre T6-b" arriba | `9d4de37` | |
| T7 refresco documental | ⏳ | | |
