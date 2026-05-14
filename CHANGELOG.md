# CHANGELOG

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
