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

## Cola de tareas

| Tarea | Estado | Evidencia | Commit |
|---|---|---|---|
| T1 handlers MCP no-sesión | ✅ | `bench/parity/cierre_mcp_golden.py` build/verify (51 escenarios, 261 líneas) + `examples/cierre_check.rs` **byte-parity** → `[PASS] cierre_check byte-parity` / `✅ PARIDAD CIERRE T1`. Oráculo = dispatcher Python REAL (`_dispatch_tool_sync`) con fakes deterministas y motores P5/P7 patcheados; write_doc usa writers REALES sobre vault tmp. Familias: search/search_vector/context (to_prompt/to_prompt_format byte-exact, budget resolver real), sync_ticket (candidatos reales vía resolve_safe), emit_proposal (pydantic 2.13 byte-a-byte: string_too_short/long, too_short/long, missing, extra_forbidden, value_error field+model, truncado de repr >50 → 25+"..."+24), create_spec (gobernanza+gap 2.0s con reloj congelado), self_review_note, write_doc ×11 doc_types (validaciones handler + writers P8b: duplicados por fingerprint, local-only, enterprise fields), design note, import/get_hu, finish_session/documenter_briefing (serialización completa del ReconstructionOutput). Autopilot-tools ×5: diferido a T3 (requiere AutopilotService nativo). Suite oráculo: **2455 passed, 18 skipped** (-p no:randomly; flaky HermesAdapter documentado en P12A-3). cargo test -p cortex-mcp: 25 ✅ · clippy `-D warnings` ✅ · fmt ✅. ADR chico: regex "1" ya en lock (cero paquetes nuevos) | `21536f5` |
| T2 subcomandos CLI restantes | ⏳ | | |
| T3 autopilot service+cli | ⏳ | | |
| T4 pipeline Documentation | ⏳ | | |
| T5 oráculo 100% verde | ⏳ | | |
| T6 pantalla ratatui (opcional) | ⏳ | | |
| T7 refresco documental | ⏳ | | |
