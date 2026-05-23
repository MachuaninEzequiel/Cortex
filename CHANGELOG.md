# CHANGELOG

## [Unreleased] — Phase 07: CI plugin (3 levels)

Provider-agnostic CLI to validate pull requests against the matching
Cortex Session. Three levels, each shippable independently. The only
schema change is two additive enum entries — no breaking changes.

### Added — Level 1 · Validation gate

- New ``cortex ci`` subapp (``cortex/cli/ci.py``) registered in the
  main app, with the ``validate-pr`` command.
- New ``cortex.ci`` module: ``validator``, ``session_matcher``,
  ``diff_io``, ``result``, ``markdown_formatter``, ``review_session``.
- ``cortex ci validate-pr`` runs scope cross-check + verification hooks
  + lifecycle checks against the matching Session + spec. Exit codes
  ``0/1/2/3`` map to ``pass/warn/blocked/error``.
- Workflow templates: ``templates/ci/github-actions-cortex-validate.yml``,
  ``templates/ci/gitlab-ci-cortex-validate.yml``, plus
  ``templates/ci/README.md`` with adoption tips.

### Added — Level 2 · Sticky PR comment

- ``--format pr-comment`` emits Markdown delimited by the sentinel
  marker ``<!-- cortex-pr-summary -->`` for ``gh pr comment
  --edit-last`` deduplication.
- GitHub Actions template includes the optional PR-comment step.
- GitLab CI template includes the optional MR-note step.

### Added — Level 3 · Review sessions

- ``CheckpointSource.CI_BOT`` and ``SessionMode.CI_REVIEW`` enum
  values; ``SessionService.infer_mode`` returns ``CI_REVIEW`` when
  every checkpoint is ``CI_BOT``.
- New CLI commands: ``cortex ci open-review-session``,
  ``cortex ci report-checkpoint``, ``cortex ci close-review-session``.
- Architectural decision documented in
  ``docs/architecture/review-sessions.md`` (Opción B chosen).
- Tests: ``tests/unit/ci/{__init__,test_session_matcher,test_diff_io,
  test_validator,test_markdown_formatter,test_review_session}.py``
  (34 cases). All new modules pass ``mypy --strict`` + ``ruff check``.

---

## [Unreleased] — Phase 05: opencode hook adapter

Fourth bundled adapter for the Observed mode. No breaking changes;
``default_installer()`` simply exposes one more IDE.

### Added

- ``cortex/session/hooks/adapters/opencode.py`` — installs a Cortex
  block inside ``.opencode/hooks.md`` with sentinel markers
  (``<!-- >>> cortex-session-hook ... >>> -->``). The block contains a
  fenced ``sh`` invocation of
  ``cortex session checkpoint --source ide-hook`` with the standard
  ``|| true`` failure guard.
- ``cortex session hooks install --ide opencode`` now works (and
  ``hooks list`` / ``hooks status`` report it).
- Tests: ``tests/unit/session/hooks/test_opencode.py`` (14 cases) +
  three new CLI scenarios in ``test_session_hooks_cli.py``.
- Research note: ``docs/pluggable-middle/fases/_internal/opencode-hooks-research.md``.

---

## [Unreleased] — Phase 09: SDD Refinement (proposal + design + tasks)

Three independent sub-phases that close the openspec workflow gaps the
Pluggable Middle audit identified. All additive — no breaking changes.

### Added — Sub-phase 09.A · Proposal step

- ``--proposal-mode`` flag on ``cortex create-spec`` (CLI + MCP). Values:
  ``optional`` (default), ``required`` (rejects unless
  ``--proposal-confirmed``), ``skip``.
- ``cortex-sync`` skill prompt extended with a Step 3.5 (proposal
  emission + edit/cancel handling) — both the on-disk skill and the
  renderer in ``cortex/setup/cortex_workspace.py``.
- ``SpecService.create`` validates ``proposal_mode`` and raises
  ``ValueError`` when ``required`` mode is missing confirmation.
- Tests: ``tests/unit/services/test_spec_service_proposal_mode.py`` +
  ``tests/e2e/test_proposal_flow.py``.

### Added — Sub-phase 09.B · Design step

- New ``cortex-code-designer`` subagent (``.cortex/subagents/`` +
  ``cortex-pi/.pi/agents/`` + renderer in ``cortex_workspace.py``).
- New ``DocType.DESIGN`` with ``DesignFrontmatter``,
  ``DesignDocData``, ``design.md.j2`` template, routing entry under
  ``vault/designs/<session_id>.md`` and canonical writer
  ``write_design_note`` (alias ``write_design_note_canonical``).
- MCP tool ``write_design_note_canonical`` + canonical-tools entry.
- SDDwork Deep Track now runs **explorer → designer → implementer →
  wrap-up**. Designer can skip with a minimal note when ``task_type ==
  "docs-only"``.
- New ``CheckpointSource.CORTEX_CODE_DESIGNER`` enum value.
- Tests: ``tests/unit/documentation/test_design_doc.py`` +
  ``tests/unit/mcp/test_write_design_note_tool.py``.

### Added — Sub-phase 09.C · Tasks granular

- ``TaskStatus`` enum + ``Task`` Pydantic model (id pattern
  ``T<n>``/``T<n>.<n>...``) and ``SessionRecord.tasks`` field
  (default ``[]`` — fully backward-compatible with older session
  YAMLs).
- ``SessionService.add_task`` / ``update_task_status`` / ``list_tasks``
  and the ``AgentMemory`` facade methods that mirror them.
- ``cortex session task list | done | in-progress | skip | block`` CLI
  subapp.
- MCP tools ``cortex_session_task_list`` and ``cortex_session_task_update``
  (the latter doubles as create-or-update when ``description`` is
  supplied).
- ``--with-tasks`` flag on ``cortex create-spec`` (adds the
  ``tasks-required`` tag the SDDwork skill reads).
- SDDwork prompt addendum on opt-in task decomposition (3–10 tasks
  typical, naming convention enforced).
- ``DocumenterPersister`` reports ``tasks: X/Y done (Z skipped)`` in
  the summary line; ``session.md.j2`` renders a dedicated ``## Tasks``
  block when the session has any.
- Tests: ``tests/unit/session/test_tasks.py`` (model + service),
  ``tests/unit/cli/test_session_task_cli.py``,
  ``tests/unit/mcp/test_session_task_tools.py``, and new cases in
  ``tests/unit/documenter/test_persistence.py`` covering the % completion
  summary.

---

## [Unreleased] — Phase 06: Sessions TUI

Live observability view of the Session primitive with `rich`. No data-
model changes; only adds CLI commands and a pure render module.

### Added

- **`cortex session watch [ID] [--refresh N]`** — live TUI. Refreshes
  every `--refresh` seconds (default 1.5, range 0.5–30). Layout adapts
  to terminal width: 3 columns at ≥ 100 cols, 2 columns at ≥ 70, vertical
  stack below. Active session panel, checkpoints table, truncated diff
  preview, verification summary, recent-sessions sidebar.
- **`cortex session show <ID> --watch`** — alias of the above focused on
  a specific session.
- **`cortex/cli/session_tui.py`** — `SessionTuiState` (frozen snapshot),
  `render_layout(state, max_width, console) → Layout` (pure function),
  `run_tui(service, project_root, refresh_interval, focus_session_id)`
  (live loop with `KeyboardInterrupt` handling).
- **`cortex/cli/_unicode_fallback.py`** — `glyph(name, console=...)` +
  `supports_unicode(console)` so the TUI degrades to ASCII on legacy
  Windows consoles (cp1252).

### Notes

- No keyboard interactivity in v1 — Ctrl+C exits cleanly, that's it.
- Single-threaded polling, mtime-based change detection on
  `.cortex/sessions/active.txt` and the per-session YAML files. Sidebar
  refresh throttled to every 10 ticks.
- Non-TTY invocations exit with an explanatory message instead of
  rendering into a pipe.

---

## [Unreleased] — Phase 08: Managed Quality Gates

Restores five quality mechanisms that the Phase 03 Autopilot fusion
removed without porting forward. No data-model changes; no breaking
changes. Each gate ships independent tests (`tests/unit/services/`,
`tests/unit/session/test_quality_gates.py`,
`tests/unit/documenter/test_persistence.py`,
`tests/unit/context_enricher/test_budget_resolver.py`,
`tests/unit/documentation/test_session_template_conditional.py`).

### Added

- **Transactional rollback** in
  `cortex.services.note_service.NoteService.create`: if semantic /
  episodic indexing fails after the session note has been persisted,
  the file is unlinked and the exception propagates. Preserves *"file
  on disk ⇒ file indexed"*.
- **`cortex_review_checkpoint` MCP tool** + `cortex.session.quality_gates`
  module: two-stage review (spec compliance + quality) over any
  checkpoint of an OPEN session. Returns `accept` / `redelegate` /
  `warn`. Registered in `cortex.ide.canonical_tools` for IDE adapters.
- **Self-review pass** in `cortex.documenter.persistence.DocumenterPersister`:
  scans the about-to-persist draft for placeholders, file mentions, and
  hollow success claims. Informational — surfaces the `auto-draft` tag
  and `[self-review]` next-step entries; never blocks.
- **`cortex.context_enricher.budget_resolver`** module:
  `resolve_budget_profile(task_type, complexity)` maps the detected
  task profile to a `(top_k, max_chars)` envelope. `cortex_context`
  accepts an optional `task_type` argument and resizes retrieval
  accordingly.
- **Conditional `session.md.j2` template**: same template renders
  `question-only` / `docs-only` (no *Changes Made* / *Files Touched*),
  `security` (dedicated *Security Review* section), and `fast-code` /
  `deep-code` / unspecified (current full layout).
- **`SessionData.task_type`** field — propagates the detected profile
  from the spec frontmatter (`raw_frontmatter["task_type"]`) through
  `NoteService.create(task_type=...)` to the template.

### Changed

- `.cortex/skills/cortex-SDDwork.md` (and its renderer in
  `cortex/setup/cortex_workspace.py`): Deep Track instructs the
  orchestrator to invoke `cortex_review_checkpoint` after each subagent
  checkpoint, and to pass `task_type` when calling `cortex_context`.
- `cortex.documenter.persistence` no longer reorders / silently drops
  warnings; `next_steps` carry `[self-review]` entries verbatim.

---

## [Unreleased] — Pluggable Middle Architecture (Phases 00–04)

Five-phase reformulation of the Cortex execution model. The original
mandatory tripartite flow (`cortex-sync` → `cortex-SDDwork` → `cortex-documenter`)
becomes a **pluggable middle**: the framework keeps the two endpoints
fixed (sync produces a spec; documenter persists from a Session) but the
middle is now one of three modes — Managed, Observed, BYO. See
`docs/pluggable-middle/ARQUITECTURA-PLUGGABLE-MIDDLE.md` for the full
design and `docs/pluggable-middle/MIGRATION-FROM-TRIPARTITO.md` for the
migration guide.

### Added

- **Session primitive** (`cortex.session`): `SessionRecord`,
  `Checkpoint`, `VerificationHook` + `VerificationHookResult`,
  `SessionService` (open/checkpoint/close), `SessionStorage` (atomic
  YAML), `git.py` (HEAD/branch/diff helpers). 100% coverage.
- **Three operating modes** (inferred at close from checkpoint sources):
  - `managed` — `cortex-SDDwork` orchestrates with verified checkpoints.
  - `observed` — user IDE + IDE hooks emit checkpoints automatically.
  - `byo` — develop with anything, reconstructor synthesizes from diff.
- **Verification hooks** (now declared in every spec): executable
  commands the documenter runs to prove the work is done. Runner with
  output truncation, timeout, exit-code reporting.
- **Documenter reconstruction** (`cortex.documenter`): 8-step algorithm
  (load → diff → hooks → scope cross-check → contradictions → handoff
  synthesis → status decision → persist).
- **CLI** — Session primitive UX:
  - `cortex session current | list | show | diff | switch | abandon`
  - `cortex session checkpoint --source <s> --note ... --artifact ...`
  - `cortex session hooks list | install --ide <name> | uninstall | status`
  - `cortex finish-session [SESSION_ID]` (+ `--handoff`, `--abandon`,
    `--reason`, `--interactive`, `--json`)
- **MCP tools** (6 canonical session tools + 1 finish):
  `cortex_session_open`, `cortex_session_checkpoint`,
  `cortex_session_close`, `cortex_session_status`, `cortex_session_list`,
  `cortex_finish_session`.
- **IDE hook adapters** (`cortex.session.hooks`, Phase 03 / T3.6–T3.10):
  - `claude-code` — `PostToolUse` entry in `.claude/settings.json`.
  - `cursor` — `.git/hooks/post-commit` (works for VSCode/Cline/Roo too).
  - `pi` — `cortex-checkpoint` / `cortex-finish` / `cortex-status`
    recipes in `justfile`.
  - All adapters: idempotent install/uninstall with sentinel markers,
    `|| true` guards so a Cortex failure never aborts an IDE operation.
- **Documenter interactive mode** (Phase 04 / T4.1–T4.7):
  `cortex finish-session --interactive` renders a draft session note
  with `rich`, surfaces ADR suggestions one by one, allows editing
  title/body via `$EDITOR`, and supports approve/edit/handoff/cancel
  hotkeys. Config field `documenter.default_mode: auto | interactive`.
- **Doctor** sections added: `[sessions]` (Phase 00), `[autopilot]`
  policy + IDE hooks (Phase 03), `[pluggable_middle]` health
  (documenter modules, interactive UX, verification runner, MCP tools
  registered, Phase 04).
- **Docs**: `docs/architecture/session-primitive.md` (full reference
  with §8 IDE hooks), `docs/pluggable-middle/` (architecture,
  per-phase plans, migration guide, short overview).

### Changed

- `cortex-SDDwork`, `cortex-code-explorer`, `cortex-code-implementer`
  now emit `cortex_session_checkpoint` calls instead of YAML
  `AgentHandoff` blocks between subagents.
- `cortex-documenter` subagent operates by default in
  **Reconstruction mode** (session_id input).
- `cortex.autopilot` is now a thin policy + hook layer over
  `cortex.session.SessionService`. CLI `cortex autopilot ...` and MCP
  `cortex_autopilot_*` tools preserved as aliases (delegate to the new
  service); commands `cleanup` and `report` removed (superseded by
  `cortex session list`).
- `cortex/services/session_service.py` renamed to `note_service.py`
  (alias kept with `DeprecationWarning` for one release).

### Deprecated

- `cortex_validate_handoff` MCP tool — kept for the documenter's
  Legacy YAML mode (single-agent IDEs like Codex). Emits a deprecation
  warning on every invocation. Removal targeted for the major after
  Codex (or equivalent) supports `cortex_session_checkpoint` natively.
- `cortex.handoff.AgentHandoff` — schema preserved for Legacy YAML.

### Removed

- `cortex/autopilot/state_store.py`, `session_builder.py`,
  `session_writer.py` (Sessions handles persistence; documenter writes
  notes via `NoteService`).
- `cortex/autopilot/{context,budget_profiles,context_budget,registry,
  reporting,delegation,packaging}.py` (consolidated, retired, or no
  callers).
- `cortex/autopilot/renderers/` (all 5 renderers — documenter owns
  session notes now).
- `cortex/autopilot/policies/{base,default,auto_checkpoint}.py`
  (replaced by the consolidated `cortex/autopilot/policies.py`).
- `cortex/autopilot/adapters/` (all 8 legacy IDE adapters — replaced
  by `cortex/session/hooks/adapters/`).
- `cortex/autopilot/hooks/` (4 files — replaced by Phase 03 hooks).
- `cortex autopilot install/uninstall/cleanup/report` CLI commands.
- `cortex.autopilot.models.{AutopilotSessionState, AutopilotCheckpoint,
  AutopilotEvent, SessionDraft, AutopilotBudgetSnapshot,
  HookSessionStartOutput}` (superseded by `cortex.session.models`).

### Fixed

- `cortex/mcp/_subprocess.py:140` `AttributeError: '_R' object has no
  attribute 'returncode'` (the 3 `TestVerifySessionClaims` tests
  preexisting from `master` — root cause was an incomplete test double
  for the new defensive `safe_run` helper).

---

## [0.6.0] — 2026-05-15 — "Multi-IDE & MCP Hardening"

Resuelve el incidente del 2026-05-15 (subagente colgado 14 minutos + MCP desconectandose). 5 fases del plan `docs/multi-ide-mcp-hardening/` ya aplicadas: inventario read-only + decisiones firmadas, MCP defensivo (4 capas), health-check `cortex_ping`, vocabulario canonico de tools, refactor de adapters segun docs oficiales 2026, eliminacion del delegate experimental. **355 tests verdes** al cierre de Fase 5.

### BREAKING — MCP Delegate experimental eliminado (Fase 5)

- **3 tools MCP eliminados de `cortex/mcp/server.py`**: `cortex_delegate_task`, `cortex_delegate_batch`, `cortex_get_task_result`. Estaban hardcoded a `opencode run --agent` via subprocess y devolvian no-op silencioso en cualquier IDE distinto de opencode — el bug exacto que detono el incidente del 2026-05-15.
- **Metodos privados eliminados**: `_delegate_task`, `_delegate_batch`, `_store_task_result`, `_get_task_result`. Imports huerfanos limpiados.
- **`cortex_delegate_task` eliminado del vocabulario canonico** (`cortex/ide/canonical_tools.py`).
- **Skill `.cortex/skills/cortex-SDDwork.md` regenerada** desde el render actualizado (sin mencionar el delegate; describe los mecanismos NATIVOS de delegacion por IDE).
- **`cortex/agent_guidelines.md` actualizado**: la delegacion es responsabilidad del IDE, no del MCP server.

**Migration:** la delegacion a subagentes ahora es nativa por IDE (Task tool en Claude Code, `mode: subagent` en opencode, Task tool en Cursor 2.4+, secuencial single-agent en Codex). Ver `docs/multi-ide-mcp-hardening/MATRIZ-NATIVA-IDES.md` para detalles por IDE. Si tenias un script externo invocando `cortex_delegate_task` directamente: dejar que el IDE delegue nativamente — los adapters de Fase 4 lo configuran automaticamente.

**Preservado:** el motor `DelegationEngine` + `register_task` / `get_task_result` en `cortex/autopilot/delegation.py`. Es el two-stage review legitimo del autopilot, no parte del delegate experimental.

### Fases anteriores (Fase 0 a Fase 4 — ver docs/multi-ide-mcp-hardening/)

- **Fase 0 (inventario)**: 4 decisiones arquitecturales firmadas (pi no se toca, codex single-agent secuencial, cursor con 3 subagents reales, community/experimental no validados).
- **Fase 1 (MCP defensivo)**: 4 capas — logging stdio, defensive subprocess (`safe_run`), ThreadPoolExecutor con timeout por tool, ONNX double-check locking. Cleanup del executor en `shutdown()`.
- **Fase 2 (health-check)**: tool `cortex_ping` con `last_error_seen` rolling buffer (`maxlen=10`, sanitizacion). Latencia <50ms p99.
- **Fase 3 (canonical tools)**: `cortex/ide/canonical_tools.py` con vocabulario y matriz de traduccion para los 2 IDEs validados (claude_code, opencode).
- **Fase 4 (adapters)**: claude_code inyecta `tools` traducido; opencode migrado a `permission` (deprecated `tools`); codex rediseno (AGENTS.md root + MCP TOML); cursor rediseno con 3 subagents reales; eliminado hibrido `cortex-SDDwork-cursor`. Pre-flight check de `cortex_ping` inyectado en renders canonicos.

---

## [0.5.0] — 2026-05-14 — "Tripartita Refinada"

Hardening pass que convierte los contratos entre subagents en artefactos verificables: handoffs estructurados, Verification Gate del documenter, confidence labels en memorias, y materialización completa en los 4 IDEs target. Suite al release: **831 passed, 6 skipped, 0 failed** (+96 vs 0.4.0). Ejecutado en 7 planes (Plan 01-07) bajo el ciclo `docs/agents/plan/` + `docs/agents/implementacion/`.

### 🔵 Plan 01 — Subagents y skills canonical

- **`AgentHandoff` schema** (`cortex/handoff.py`, nuevo) — Pydantic model que reemplaza handoffs en prosa entre subagents. 7 agent names canonical (5 generales + 2 Pi-only: security-auditor, test-verifier). Métodos `to_yaml()` / `from_yaml()`. 12 tests.
- **5 prompts canonical reescritos** (`.cortex/subagents/cortex-{code-explorer,code-implementer,documenter}.md` + `.cortex/skills/cortex-{sync,SDDwork}.md`) con: HIGH-SIGNAL, 3 criterios ADR, Verification Gate, Modo Handoff, tablas Anti-rationalization, Contrato de Salida YAML.
- **`MemoryEntry.confidence`** y **`SessionDraft.confidence_level`**: tri-state `verified | asserted | contradicted | None` (None = pre-0.5.0, backwards-compat).
- **`AutopilotSessionState.status`** acepta `"handoff"`. **`IndexingSessionWriter._build_tags`** agrega tag `handoff` automáticamente cuando `state.status == "handoff"`.
- **`CONTEXT.md`** como prompt asset: `WorkspaceLayout.context_md_path`, `render_context_md()` template, auto-create idempotente en `setup full`.
- **`_meets_adr_criteria`** helper module-level (`cortex/doc_generator.py`) que aplica 3 criterios sobre PR body: filtro de keyword heuristics, listo para uso futuro.

### 🟢 Plan 02 — MCP server

- **2 tools nuevos en `cortex/mcp/server.py`**:
  - `cortex_validate_handoff` — valida YAML contra `AgentHandoff` schema. Soporta `expected_agent` para asertion downstream.
  - `cortex_verify_session_claims` — cruza claims contra `git diff` con heurística keyword-based. Retorna buckets `verified` / `asserted` (bucket `contradicted` reservado para heurística de negación futura).
- **Cascade `cortex_save_session` extendida** con 5 parámetros opcionales (`handoff`, `blockers`, `verified_state`, `unverified_claims`, `suggested_skills`) propagados en 4 niveles: MCP `_save_session_text` → `AgentMemory.save_session_note` → `SessionService.create` → `write_session_note` (`cortex/documentation.py`).
- **Confidence label propagado** en `RetrievalResult.to_prompt()` y `EnrichedContext.to_prompt_format()` cuando el campo es no-None. Nuevo campo `EnrichedItem.confidence`.
- **`tests/e2e/test_artefact_integrity.py::MCP_TO_CLI`** actualizado con los 2 tools nuevos marcados `None` (MCP-only por diseño).

### 🟡 Plan 03 — IDE Claude Code

- **Template `CLAUDE.md` ampliado** (`cortex/ide/adapters/claude_code.py::inject_profiles`) con sección `## Tripartita Refinada — verifiable contracts` y 4 reglas: Verification Gate, validate_handoff schema, status: handoff first-class, CONTEXT.md awareness.
- **Tests de inheritance**: `TestClaudeCodeTripartitaRefinada` con 3 tests (CLAUDE.md markers + cortex-documenter inheritance + explorer/implementer Anti-rationalization).

### 🔴 Plan 04 — IDE OpenCode

- **2 tools handoff/verify habilitados** en `cortex_profiles` (`cortex/ide/adapters/opencode.py`): `cortex_validate_handoff` y `cortex_verify_session_claims` aparecen en el toggle de `tools` para `cortex-sync` y `cortex-SDDwork` con comentarios inline explicando el rol de cada agent con cada tool.
- **Tests** `TestOpenCodeTripartitaRefinada` (3 tests: sync tools, SDDwork tools, regression de tools pre-existentes).

### 🟣 Plan 05 — IDE Pi (caso especial)

- **`PiAdapter.sync_canonical_subagents`** mirror automático de `.cortex/subagents/` → `cortex-pi/.pi/agents/` antes de copiar el bundle al proyecto. Cierra la deuda histórica de drift entre canonical y bundle Pi.
- **CLI flag `--sync-canonical / --no-sync-canonical`** en `cortex inject` (default True; ignorado por adapters distintos a Pi).
- **`cortex.ide.inject` ampliado** con kwarg `sync_canonical=True`. Detección por nombre del adapter Pi (`adapter.name == "pi"`) para evitar import circular.
- **4 agents Pi-only actualizados** (`cortex-pi/.pi/agents/`): `cortex-sync.md` (Pre-flight CONTEXT.md + Anti-rationalization + Contrato YAML), `cortex-SDDwork.md` (Validación de handoffs + Anti-rationalization + Contrato YAML), `cortex-security-auditor.md` (Anti-rationalization + Contrato YAML), `cortex-test-verifier.md` (Anti-rationalization + Contrato YAML).
- **`agent-chain.yaml`** con keys declarativas `validate_handoff` + `expected_input_agent` por step en los 3 chains (sddwork, hotfix, refactor). La extensión Pi actual las ignora; el orquestador SDDwork hace la validación manualmente vía la sección "Validación de handoffs" del prompt.
- **`damage-control-rules.yaml`** sección nueva `handoffRules` con 3 reglas (handoff-malformed/block, handoff-status-mismatch/warn, handoff-context-overflow/warn).
- **`cortex-vault/SKILL.md`** secciones CONTEXT.md awareness + confidence labels.
- **6 tests** (`TestPiSyncCanonicalSubagents` + CLI flag) — todos con bundle fake / monkeypatch del default path para no mutar el bundle real del repo.

### 🟠 Plan 06 — IDE Codex

- **Template `.codex/AGENTS.md` ampliado** con las 4 reglas Tripartita Refinada + nota explícita sobre la ausencia de `Task` tool nativo (la "delegación" se logra por convención: el handoff es el último mensaje del agent saliente; el siguiente lo consume como input).
- **Tests** `TestCodexTripartitaRefinada` con 3 tests (AGENTS.md markers + cortex-documenter inheritance + explorer/implementer Anti-rationalization).

### ⚫ Plan 07 — Tests cross-IDE, doc-guides, bump

- **Smoke cross-IDE parametrizado** (`tests/unit/test_ide_adapters.py::TestTripartitaCrossIDE`) — 5 tests que verifican los markers Tripartita Refinada en los 3 IDEs que comparten el patrón canonical-from-disk (Claude Code, Codex, OpenCode).
- **Pi bundle markers** (`TestPiBundleHasTripartitaRefinada`) — 6 tests que aseguran que los archivos del bundle `cortex-pi/.pi/` mantienen los markers Tripartita Refinada (guardia contra rollback silencioso del bundle).
- **MCP tools registrados** (`tests/unit/test_mcp_server.py::TestNewMcpToolsRegistered`) — 3 tests que verifican que `cortex_validate_handoff` y `cortex_verify_session_claims` están registrados en `list_tools` y dispatchados correctamente.
- **Cascade `write_session_note(handoff=True)` end-to-end** — 3 tests (`tests/unit/test_documentation.py`) que persisten un session note real con `handoff=True` y verifican `status: handoff` en frontmatter, tag `handoff`, y secciones nuevas (Verified State / Unverified Claims / Blockers / Suggested Skills) emitidas solo si las listas son no-vacías.
- **Doc-guides actualizadas** en los 4 IDEs target (`docs/guides/ide-{claude-code,opencode,pi,codex}.md`) con sección "Tripartita Refinada (0.5.0)".
- **Bump 0.4.0 → 0.5.0** en `pyproject.toml` y `cortex/__init__.py`.

### Breaking changes

- **`cortex.ide.inject` firma:** ahora acepta kwarg `sync_canonical: bool = True`. Backwards-compat: el default reproduce el comportamiento previo para todos los adapters distintos de Pi. Tests externos que mockean `cortex.ide.inject` deben aceptar el kwarg (el repo's `tests/unit/cli/test_main.py` se actualizó).
- **`cortex_save_session` MCP tool** acepta 5 nuevos parámetros opcionales (`handoff`, `blockers`, `verified_state`, `unverified_claims`, `suggested_skills`). Defaults reproducen comportamiento previo (`handoff=False`, listas vacías).
- **`AgentMemory.save_session_note`, `SessionService.create`, `write_session_note`**: idem (5 nuevos kwargs opcionales con defaults).
- **`MemoryEntry.confidence`** y **`EnrichedItem.confidence`**: nuevo campo opcional `Literal["verified","asserted","contradicted"] | None = None`. Memorias pre-0.5.0 tienen `None` y siguen funcionando.

### Métricas

- Tests: 829 → 831 passed (+96 desde Plan 01 baseline 749 → +82 nuevos a Tripartita Refinada).
- Líneas de código nuevas: ~1100 (handoff schema, MCP tools, cascade, sync_canonical, prompts canonical, agent-chain, damage-control rules).
- Documentación: 7 bitácoras de implementación (`docs/agents/implementacion/01-07-*.md`) + 1 doc de cierre (`docs/olas/tripartita-refinada.md`) + 4 secciones nuevas en doc-guides + entrada CHANGELOG (este).
- Adopters target: 2 startups, reunión inicial dentro de pocos días post-0.5.0.

## [0.4.0] — 2026-05-13 — "Camino a los early adopters"

Wave-based hardening pass to bring Cortex from "alpha demo" to "framework usable by an external adopter without hand-holding". Suite at release: **829 passed, 6 skipped, 0 failed**.

### 🔴 Ola 0 — Critical fixes

- **Autopilot persists session note transactionally.** `autopilot finish --auto` now actually writes the markdown file to `<vault>/sessions/` and indexes it. Previously `saved=True` was reported but no file existed. New `SessionWriter` Protocol + `VaultSessionWriter` + `IndexingSessionWriter` (transactional: if indexing fails the file is rolled back, never an orphan).
- **Indexing is mandatory on every doc write.** `IndexingSessionWriter` wraps the writer; `PRService.write_pr_docs` indexes generated docs; `cortex_save_session` and `cortex_create_spec` already indexed via `SessionService`/`SpecService`. The contract "file on disk ⇒ file indexed" is now invariant. Doctor flags degraded writers via the new `session_indexing` check.
- **MCP governance guard fixed encoding + refactored DRY.** `_create_spec_text` had double-encoded UTF-8 (`âŒ VIOLACIÃ“N` instead of `❌ VIOLACIÓN`). Centralized into `_GOVERNANCE_VIOLATION_MESSAGE` constant. Dispatcher delegates to the helper. Verify-by-deletion test confirms the guard actually blocks.
- **`cortex context --output` honours `--format json`.** Already correct in code; added 3 regression tests in `tests/unit/cli/test_main.py`.
- **Entity round-trip in episodic memory.** Already serialized via `metadata_json`; added 10 parametrized tests covering 8 entity types (function, class, endpoint, error, config_key, dependency, variable, constant).

### 🔵 Ola 1 — IDEs y MCP

- **New IDE adapter: Codex.** `cortex/ide/adapters/codex.py` from scratch. `cortex inject --ide codex` writes `.codex/AGENTS.md`, `.codex/mcp.json` (absolute `--project-root`), `.codex/skills/`, `.codex/agents/`. Detects installation via `which("codex")`.
- **Claude Code MCP uses absolute path.** Was emitting `--project-root "."` which broke when the IDE launched from a different cwd. Now uses `str(project_root)`.
- **Pi adapter detects real installation.** `PiAdapter.detect_installation()` now probes `which("pi")` instead of returning `True`.
- **IDE tiers exposed.** `TARGET_IDES = {claude_code, opencode, pi, codex}`, `COMMUNITY_IDES`, `_EXPERIMENTAL_IDES`. New helpers `get_target_ides()`, `get_ide_tier()`. Error message on unknown IDE lists all three tiers.
- **4 IDE adopter guides** in `docs/guides/ide-{claude-code,opencode,pi,codex}.md`.

### 🟢 Ola 2 — Pipelines y workflows

- **Layout-aware memory cache in generated workflows.** New helper `_get_memory_cache_path(layout)` returns `.cortex/memory` (new layout) or `.memory/chroma` (legacy). `render_ci_pull_request`, `render_ci_feature`, `render_cd_deploy` accept `layout=` and emit `actions/cache/restore@v4` + `actions/cache/save@v4` with the correct path.
- **CLI ↔ template alignment** verified by `TestCliAlignment::test_workflows_reference_known_subcommands` — extracts every `cortex <subcmd>` from generated workflows and asserts it exists in the Typer command tree.
- **Stack-agnostic templates** cover Node (npm/yarn/pnpm), Python (pip), Go via `_get_test/lint/audit/install/build_command` + `_get_setup_language` (Node 20, Python 3.11, Go 1.22, Java 21, Ruby 3.3).

### 🟡 Ola 3 — UX de primer contacto

- **`cortex setup full` ahora instala los 3 pilares.** Agent + WebGraph + Pipeline en una corrida. Cold start (preseed vault + git history mining + README fallback) integrado. Idempotente.
- **`--non-interactive` en `setup pipeline` y `setup full`.** Unblock automation: CI, scripted onboarding, containers. Default seguro: aceptar vault detectado.
- **`AgentMemory()` discovers layout automatically.** Sin args, hace `WorkspaceLayout.discover(cwd)` y usa `layout.config_path`. Resuelve UX rota donde correr `cortex search` desde el repo root de new-layout fallaba.
- **`cortex stats --project-root`.** Inconsistencia con doctor/mcp-server/etc resuelta.
- **Doctor gitignore layout-aware.** En new layout chequea `.cortex/memory/` y `.cortex/vault/sessions/`. En legacy chequea `.memory/` y `vault/sessions/`. Antes daba FAIL falsos en setups new-layout.
- **`cortex setup full` actualiza `.gitignore` automáticamente.** Nuevo paso `_update_gitignore()` agrega los patterns correctos según layout. Idempotente.
- **Error messages accionables.** `AgentMemory()` sin config y `_load_memory()` ahora explican qué comando correr.
- **Onboarding doc:** `docs/guides/getting-started-adopters.md`.

### 🟣 Ola 4 — Pulido final

- **Doc verifier classification mutually exclusive.** `verify_from_diff` refactorizado: `vault_files` = unión de las 3 partitions; nuevo helper `_vault_relative_md` centraliza el filtro de prefix + `.md`. Cierra weakness #7.
- **`release-2-known-weaknesses.md` cerrado** — 6 de 7 items resueltos, weakness #2 scoped out a `docs/roadmap/post-adopters.md`.
- **CLI docstring sincronizado** con la realidad: 35+ comandos + 4 sub-apps documentados.
- **`docs/olas/` con 5 documentos** (README + ola-0..4) — planes ejecutables auto-suficientes con checklist.
- **`docs/review/cortex-save-state.md`** — save state operativo del agente para sesiones futuras.

### Breaking changes

- **`AgentMemory.__init__` firma:** `config_path: str | Path | None = None` (era `"config.yaml"`). Backwards-compat: pasar un path explícito sigue funcionando.
- **`SessionWriter` Protocol introducido en autopilot:** `AutopilotService` ahora acepta `session_writer` opcional. Sin writer, `finish --auto` retorna `saved=False, status="finished"` (era `saved=True, status="documented"` con archivo inexistente).
- **`render_ci_pull_request`, `render_ci_feature`, `render_cd_deploy`** firma extendida con `layout=` opcional. Backwards-compat: sin layout cae a legacy.
- **`PRService.__init__`** firma extendida con `semantic: VaultReader | None`. Sin semantic, los docs generados se persisten pero no se indexan (con warning visible).
- **CLI `cortex remember --branch/--commit/--repo`** confirmados como soportados (estaban antes pero no documentados).

### Test suite

- 707 → 829 tests passing (+122 nuevos / regression coverage).
- 6 skipped consistentes (E2E que requieren red).
- 0 failed.

---

## [Unreleased]

### 🟣 Versionado y narrativa publica
- **Normalización de versionado**: Unificada la versión pública en `0.3.0` con estado `Alpha`.
  - `pyproject.toml`, `cortex/__init__.py` y README ahora muestran la misma versión.
  - Bajado el `Development Status` a `3 - Alpha` para reflejar el estado real del proyecto.
  - Eliminados del README los badges estáticos no auditables de cobertura y CI/CD.

### 🔵 Current Focus
- **Enterprise Memory Actualization**: Refining the integration between local Python codebase and Obsidian-based documentation pipeline.
- **MCP Server Optimization**: Streamlining context synchronization for high-latency environments.
- **Improved Context Injection**: Fine-tuning co-occurrence boost and domain detection.

---

## [2.5.0] — 2026-04-28

### 🔴 Enterprise Foundation
**What changed:** 
- Introduced `.cortex/org.yaml` for multi-project governance.
- **Multi-level Retrieval**: Capabilities to search across local and corporate memory spaces simultaneously.
- **Enterprise Doctor**: Advanced diagnostic tool for memory topology and governance health.

**Why it matters:** Enables Cortex to scale from a single-repo tool to an organization-wide knowledge system where agents can leverage cross-project context.

### 🟡 Cortex-Pi CLI
**What changed:**
- **Premium Branding**: Implementation of TrueColor ASCII branding and a high-fidelity visual identity.
- **Release 2.5 Protocol**: Mandatory integration of Security and Test subagents into the default development flow.
- **Pi Extensions**: Plugin system for customizing agent behavior in the Pi environment.

**Why it matters:** Provides a professional-grade interface that enforces project governance standards while offering a premium developer experience.

### 🟢 Infrastructure & Documentation
- **CI Stabilization**: Massive refactor of GitHub Actions pipelines to ensure 100% reliability in hardening gates.
- **Strategic Docs**: Reorganized enterprise-grade documentation into `docs/enterprise/`.

---

## [2.4.0] — 2026-04-25

### 🔴 Architectural Overhaul
**What changed:**
- **Core Refactor**: `cortex/core.py` transitioned to a clean Facade pattern with dependency injection for `cortex/services/`.
- **Pipeline Module**: Introduced `cortex/pipeline/` to replace legacy bash scripts for CI/CD gates.
- **MCP Delegation**: Parallel execution of subagent tasks (`_delegate_task`, `_delegate_batch`).

**Why it matters:** Improves maintainability and allows for more complex orchestration patterns without bloating the core logic.

### 🟡 Intelligence & Speed
**What changed:**
- **Adaptive RRF**: Fusion weights now adjust dynamically based on query intent.
- **Async Context Enricher**: Implemented `asyncio.gather` for concurrent context resolution.
- **Lazy Embedders**: `EmbeddersFactory` now loads backends on-demand, reducing CLI startup time.

**Why it matters:** Faster responses and more relevant results, especially in large-scale repositories.

### 🟢 Quality & Security
- **Property-Based Testing**: Added Hypothesis tests for RRF mathematical boundaries.
- **WebGraph Security**: CSRF protection via `X-Cortex-WebGraph` tokens.
- **Contract Testing**: Standardized tests for any new embedding backend.

---

## [2.0.0] — 2026-04-17

### 🔴 CRITICAL FIXES

#### 1. Semantic Memory Now Uses True Vector Embeddings
**What changed:** `VaultReader` no longer performs naive keyword counting. It now embeds every vault document using the same `Embedder` as the episodic layer.
**Why it matters:** Enables genuine cosine-similarity semantic search, allowing the agent to find documents by meaning rather than just exact words.

#### 2. True Cross-Source Reciprocal Rank Fusion (RRF)
**What changed:** RRF now fuses episodic and semantic results into a **single unified ranked list**.
**Why it matters:** Previously, sources didn't compete. Now, a highly relevant semantic doc can correctly outrank a weakly relevant episodic memory.

#### 3. Timestamp Restored on Episodic Memory Retrieval
**What changed:** Fixed a bug where retrieved memories always showed `datetime.now()`.
**Why it matters:** Restores chronological context to retrieved events.

### 🟡 IMPORTANT IMPROVEMENTS

#### 4. `AgentMemory.create_note()` Added to Public API
Added convenience method for creating semantic notes without accessing internal modules.

#### 5. `CortexHook` Decorator Enhancements
Uses `functools.wraps` and `inspect.signature` for better metadata preservation and readable input capture.

#### 6. Config Validated with Pydantic
A full Pydantic hierarchy now validates all `config.yaml` values on startup, rejecting invalid configurations early.

### 🟢 MINOR FIXES & CHORES
- **Modern Build Backend**: Switched to `setuptools.build_meta`.
- **Centralized Fixtures**: Moved all test fixtures to `tests/conftest.py`.
- **CLI Warnings**: Improved feedback when LLMs are not configured or when memory IDs are missing.

---

### BREAKING CHANGES (v2.0.0)
- `RetrievalResult.to_prompt()` uses unified RRF ranking.
- `AgentMemory.config` is now a Pydantic object (access via dot notation instead of keys).
- `VaultReader` now requires an `Embedder` instance.
