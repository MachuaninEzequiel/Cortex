# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
y este proyecto adopta [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> Nota de normalización (2026-08-24, H-8): las 8 secciones `[Unreleased]`
> acumuladas se consolidaron en la entrada `[0.7.0]` de abajo, sumando el
> Programa de Transformación 2026-08 (Obras 01–06) que no había llegado al
> CHANGELOG. Las entradas históricas no se tocaron.

## [0.7.0] — 2026-08-24 — "Transformación: nativo, bilingual, brain"

Consolida el trabajo post-0.5.0-baseline-seal: arquitectura pluggable-middle,
quality gates, plugin CI, refinamiento SDD, TUI de sesiones, el Programa de
Transformación 2026-08 (podas, capa nativa Rust, embeddings per-language,
ActionEngine/TUI/i18n, brain LLM local) y la auditoría de realidad 2026-08.

### Added

#### Programa de Transformación 2026-08 (Obras 01–06)

- **Obra 03 — Capa nativa Rust** (`rust/`: cortex-core PURO + cortex-embed +
  cortex-py, opt-in vía `CORTEX_NATIVE=1`, default APAGADO, paridad
  bit-exacta verificada gate por gate):
  - scoring batch f64+Neumaier (27.6× en sub-path; search p50 89→26ms),
  - store binario v3 append-only (cold load 6.4× · ingesta 3684×),
  - BM25 casero en Rust (p99 10.1→1.85ms, ranking idéntico 200/200),
  - webgraph con rayon (n1000 3162→345ms, edges idénticos),
  - `NativeEmbedder` sobre ort (paridad cos=1.00000000, first_query_cold 20.8×),
  - wheels CI multiplataforma (maturin-action, 5 targets),
  - ADRs: ADR-BM25, ADR-EMBEDDINGS, ADR-EPISODIC.
- **Obra 03/06 — cortex-brain nativo**: asistente local experto del proyecto.
  Router determinista 1:1 con la spec Python (13 tests espejados), tools
  READ/SAFE_ACTION delegando en el CLI `cortex` (el brain NUNCA ejecuta
  mutaciones: propone el comando exacto), backend llama.cpp/GGUF real
  (LFM2.5-1.2B-Instruct Q4_K_M, chat template del GGUF vía jinja, samplers
  temp/top_k/dist con seed), protocolo TOOL con confirmación explícita
  testeable (`ScriptedBackend` para CI sin modelo), ventana dedicada
  multiplataforma (BRAIN-3), i18n ES/EN del chrome (convención `ui.language`).
- **Obra 03 — cortex-cli**: fachada nativa passthrough (decisión dueño:
  "fachada sobre CLI Python"; paridad por construcción, startup <50ms;
  subcomandos nativos recién en Obra E).
- **Obra 03 — evaluación**: `queries-es-en.jsonl` (100 queries anotadas,
  seed 42) + scorer hit@5/MRR@10; BM25 hit@5=1.0 MRR=1.0.
- **Obra 04 — embeddings per-language**: bloque `embedding:` con
  `per_language`, detección heurística ES/EN (diacríticos + stopwords,
  frontmatter `lang:` gana siempre, retrocompat estricta), backend genérico
  `fastembed` ONNX sin PyTorch con prefijos automáticos E5
  `query:/passage:`. Recomendación medida: EN=all-MiniLM-L6-v2 (MRR@10=1.0)
  · ES=intfloat/multilingual-e5-large (MRR 0.8821→0.9615).
- **Obra 04 — migración de modelos**: identidad de modelo en cache de
  vectores (fingerprint salteado, schema v2, invalidación automática),
  dimensión paramétrica (adiós 384 hardcodeado), comando `cortex reindex`
  (backup→rebuild→rollback opcional `--prune-old-caches`) y
  `cortex embedding-status`. Suite de evaluación `eval/retrieval/`.
- **Obra 05 — ActionEngine**: paquete `cortex/action_engine/` (models/store/
  registry/scheduler/runner/learning/signals/metrics/i18n) con catálogo v1
  de 10 acciones sobre servicios existentes; comando `cortex next`
  (--json/--explain-why-not/--all/--stats; gate <2s); nivel-0
  `cortex start|finish`; señales feedback→score (±25%) y métrica `pct_motor`;
  FeedbackStore JSONL con rotación; telemetría cableada en los 4 sitios de
  ContextEnricher; APIs públicas SessionService.
- **Obra 05 — TUI**: `cortex` sin argumentos abre el Home (<300ms snapshot)
  con pantallas de acciones y búsqueda (decisión→Learner→Runner reales);
  `session --watch` deprecado en favor del Home.
- **Obra 05 — i18n**: `ui.language` ES/EN para ActionEngine y Home.
- **Obra 01 — podas estructurales**: `mcp/server.py` 2977→491 líneas
  (schemas.py + mixins tools/{search,sessions,documenter,workspace} +
  dispatcher tabular) con golden contract byte-a-byte
  (`tests/unit/mcp/test_golden_contract.py`); `main.py` 2540→~1900 líneas
  (subapps cli/{pr_context,hu,common,embedding,mcp_cmd,next,documenting});
  `_PathVault` único; skills embebidos → package-data
  (`setup/workspace_files/*.md`, −1400 líneas); ciclo session↔documenter
  roto (TYPE_CHECKING + guardia de arquitectura).
- **Obra 02 — estándar IDE único**: `cortex ide list|setup|remove|status`
  contrato único; uninstall seguro con marcadores BEGIN/END CORTEX SECTION
  en los 11 adapters.
- **I-1 — CI gates bloqueante**: `.github/workflows/ci-gates.yml`
  (pytest+ruff F401/F841/F821+vulture80+cargo fmt/clippy/test+bench nocturno
  con compare >10%).
- **Auditoría 2026-08** (`docs/transformacion/07-AUDITORIA`): todos los
  hallazgos R-1..3 y H-1..H-7 resueltos con commits `fix(auditoria)`.

#### Pluggable Middle Architecture (Phases 00–04)

- **Session primitive** (`cortex.session`): `SessionRecord`, `Checkpoint`,
  `VerificationHook`+result, `SessionService` (open/checkpoint/close),
  `SessionStorage` YAML atómico, helpers git. Tres modos operativos
  (managed/observed/byo inferidos al cerrar).
- **Verification hooks**: comandos ejecutables declarados en la spec que el
  documenter corre para probar el trabajo; runner con timeout/truncation.
- **Reconstrucción del documenter**: algoritmo de 8 pasos (load→diff→hooks→
  scope cross-check→contradictions→handoff synthesis→status→persist).
- **CLI Session**: `current|list|show|diff|switch|abandon`,
  `checkpoint --source`, `hooks list|install|uninstall|status`,
  `cortex finish-session` (+--handoff/--abandon/--interactive/--json).
- **MCP**: 7 tools canónicos de sesión (`cortex_session_open/checkpoint/
  close/status/list`, `cortex_finish_session`, …).
- **IDE hook adapters**: claude-code (PostToolUse), cursor (post-commit),
  pi (recipes justfile), opencode (`.opencode/hooks.md`) — instalación
  idempotente con sentinel markers y guardias `|| true`.
- **Documenter interactivo**: `finish-session --interactive` con rich, ADRs
  uno por uno, `$EDITOR`, hotkeys; `documenter.default_mode: auto|
  interactive`.
- **Doctor**: secciones `[sessions]`, `[autopilot]` policy+hooks,
  `[pluggable_middle]`.
- Docs: `docs/architecture/session-primitive.md`, `docs/pluggable-middle/`.

#### Phase 08 — Managed Quality Gates

- Rollback transaccional en `NoteService.create` (archivo en disco ⇒
  archivo indexado).
- Tool MCP `cortex_review_checkpoint` (review en dos etapas: spec+calidad;
  devuelve accept/redelegate/warn).
- Self-review pass del documenter (detecta placeholders y claims vacíos;
  informativo, nunca bloquea).
- `budget_resolver`: `resolve_budget_profile(task_type, complexity)` →
  `(top_k, max_chars)`; `cortex_context` acepta `task_type`.
- Template condicional `session.md.j2` (question-only/docs-only/security/
  fast-code/deep-code) + campo `SessionData.task_type`.

#### Phase 09 — SDD Refinement

- `--proposal-mode optional|required|skip` en `create-spec` (CLI+MCP) con
  `--proposal-confirmed`.
- Subagente `cortex-code-designer` + `DocType.DESIGN` + tool MCP
  `write_design_note_canonical`; Deep Track ahora
  explorer→designer→implementer→wrap-up.
- Tasks granulares: enum `TaskStatus`, modelo `Task` (ids `T<n>[.<n>]`),
  `SessionService.add_task/update_task_status/list_tasks`,
  CLI `cortex session task list|done|in-progress|skip|block`, tools MCP de
  tasks, `--with-tasks` en create-spec, % completion en el documenter.

#### Phase 07 — CI plugin (3 niveles)

- `cortex ci validate-pr`: scope cross-check + verification hooks +
  lifecycle checks contra la Session matching; exit codes 0/1/2/3 =
  pass/warn/blocked/error.
- `--format pr-comment` con sentinel marker para `gh pr comment --edit-last`.
- Templates GitHub Actions / GitLab CI (+ README de adopción).
- Review sessions: `CheckpointSource.CI_BOT`, `SessionMode.CI_REVIEW`,
  comandos open-review/report-checkpoint/close-review-session.

#### Otros

- `embedding-status`: diagnóstico por idioma/modelo.
- OpenCode hook adapter (cuarto IDE del modo Observed).

### Changed

- **Embeddings**: embedder stacks duplicados consolidados
  (`episodic/embedder` delega en `EmbedderFactory`); OpenAI embebe por
  batch; template de setup genera defaults bilingües; legacy
  `episodic.embedding_*` deprecado en favor del bloque `embedding:`
  (sigue funcional con warning).
- **Autopilot → Session**: `cortex.autopilot` es ahora una capa fina de
  policy+hooks sobre `SessionService`; aliases CLI/MCP preservados;
  documenter opera por defecto en modo Reconstrucción; skills
  explorer/implementer/SDDwork emiten `cortex_session_checkpoint`.
- `cortex-SDDwork` skill: Deep Track invoca quality gates y pasa `task_type`
  a `cortex_context`; documenter no reordena ni descarta warnings.
- Config validada con Pydantic end-to-end (ver 2.0.0) extendida con los
  bloques nuevos (`embedding`, `pluggable_middle`, `documenter`).

### Deprecated

- `cortex_validate_handoff` MCP tool (modo Legacy YAML para single-agent
  IDEs; warning en cada invocación; remoción objetivo: major posterior).
- `cortex.handoff.AgentHandoff` — schema preservado para Legacy YAML.
- Legacy `episodic.embedding_model/embedding_backend` (reemplazados por el
  bloque `embedding:`; siguen funcionando con warning de migración).
- `cortex session watch` / `show --watch` — reemplazados por la TUI Home
  (`cortex` sin argumentos).

### Removed

(consolidación Phases 00–04 — ver detalle en docs/pluggable-middle/)
- `cortex/autopilot/{state_store,session_builder,session_writer}.py`.
- `cortex/autopilot/{context,budget_profiles,context_budget,registry,
  reporting,delegation,packaging}.py`.
- `cortex/autopilot/renderers/` (los 5 renderers — el documenter es dueño de
  las session notes ahora).
- `cortex/autopilot/policies/{base,default,auto_checkpoint}.py`.
- `cortex/autopilot/adapters/` (8 adapters legacy →
  `cortex/session/hooks/adapters/`).
- `cortex autopilot install/uninstall/cleanup/report` (CLI).
- Modelos `Autopilot*` superseded por `cortex.session.models`.

### Fixed

- **Empty-search silencioso**: falla de vector-cache a mitad de batch
  producía resultados vacíos sin error; ahora fail-fast con contexto del
  chunk; errores de cache degradan a WARNING.
- `update_note` destruía frontmatter; ahora se preserva verbatim.
- Colisiones de títulos de sección en chunk ids (se perdían secciones);
  sufijos posicionales solo en colisión real.
- `create_note` no persistía metadata de índice.
- `cortex/mcp/_subprocess.py` `AttributeError '_R' object has no attribute
  'returncode'` (test double incompleto del defensive `safe_run`).

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
