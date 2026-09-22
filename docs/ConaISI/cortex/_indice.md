# Índice — paquete Python `cortex/`

Inventario generado desde el código de `cortex/` (262 `.py`). Cada ficha describe qué hay, para qué sirve, de quién recibe y a quién envía. **No se leyó documentación previa del repo.**

Versión del paquete observada: `__version__ = "0.7.0"` en `cortex/__init__.py`. Entrypoint CLI: `cortex.cli.main:app`.

## Cómo leer este índice

1. `00-estructura.md` — árbol completo del paquete.
2. `<subpaquete>/00-estructura.md` — árbol y relaciones de esa carpeta.
3. Un `.md` por archivo `.py` (y tres assets webgraph).
4. Archivos sueltos de `cortex/*.py` viven en `raiz/`.

## Síntesis por subpaquete

- **raiz** — Fachada AgentMemory, config Pydantic, doctor, decay/feedback, PR capture, handoff legado, helpers git/runtime.
- **action_engine** — Motor OBSERVAR→PROPONER→APROBAR→EJECUTAR→APRENDER. Acciones delegan a servicios; log JSONL.
- **autopilot** — Capa de política sobre SessionService (observe/assist/autopilot), no un segundo ciclo de vida.
- **brain** — DEPRECATED. Brain oficial es Rust cortex-brain. Este paquete es oráculo/legacy.
- **ci** — Validación provider-agnostic de PRs contra Session+spec; comentario Markdown.
- **cli** — Typer: search/context/remember/setup/session/mcp/doctor y sub-apps hidden.
- **context_enricher** — Contexto proactivo: observer, domain detector, multi-strategy search, presenter.
- **documentation** — DocType, schemas Pydantic, routing, writers Jinja2, migración/inventario del vault.
- **documenter** — Reconstrucción de sesión (diff+hooks+handoff sintético) y persistencia de notas/ADRs.
- **embedders** — Factory Strategy: onnx (default), local, openai, fastembed.
- **enterprise** — org.yaml, gobierno de equipos, promoción de conocimiento, retrieval multi-source.
- **episodic** — Chroma + Embedder wrapper + summarizer LLM opcional.
- **hooks** — Callbacks LangChain / agent hooks hacia AgentMemory.
- **ide** — Adapters de inyección MCP/perfiles: Cursor, Claude, VSCode, Pi, Codex, Zed, etc.
- **mcp** — Servidor MCP 1.x stdio, tools catalog v2.2, timeouts y mixins search/docs/session/workspace.
- **pipeline** — DevSecDocOps: Security/Lint/Test/Documentation stages + GitHubActionsRunner.
- **retrieval** — RRF k=60 + detector de intent léxico (episódico/semántico/mixed).
- **security** — resolve_safe / validate_under_root contra path traversal.
- **semantic** — Vault Markdown: parser, chunker, vector cache, BM25, opcional cortex_core._native.
- **services** — SpecService, NoteService (alias SessionService deprecado), PRService.
- **session** — Primitiva open/checkpoint/close, YAML, git, hooks IDE, verification hooks.
- **setup** — Detector de stack, orchestrator setup agent/pipeline/full, templates y workspace_files.
- **skills** — install_skills copia skills Obsidian embebidas a .cortex/skills/.
- **tui** — Home rich: dashboard y acciones; orquesta, no reimplementa.
- **tutor** — Tutorial offline + hints según estado del proyecto.
- **webgraph** — Proyección grafo Flask + vis-network; semantic/episodic/hybrid.
- **workitems** — Import opcional Jira → vault/hu.
- **workspace** — WorkspaceLayout: new (.cortex/) vs legacy; discover() walk-up.

## Flujo de datos (visión de código)

```
IDE / humano
  → cortex.cli.main (Typer)  o  cortex.mcp.server (stdio JSON-RPC)
    → WorkspaceLayout.discover
    → AgentMemory (core.py)
         ├─ EpisodicMemoryStore (Chroma + EmbedderFactory)
         ├─ VaultReader (markdown + embeddings + BM25 [+ rust nativo])
         ├─ HybridSearch (RRF + intent)  |  EnterpriseRetrievalService
         ├─ SessionService (YAML + git + session.lock)
         ├─ SpecService / NoteService / PRService  → documentation.writers
         └─ ContextEnricher / WorkItemService
  AutopilotService aplica PolicyEnforcer sobre SessionService
  Documenter Reconstructor → Persister (finish-session)
  ActionEngine Runner → action_log.jsonl (delega a los mismos servicios)
  WebGraphService → Flask + vis-network
```

## Listado de fichas

### `00-estructura.md/`

- [`00-estructura.md`](00-estructura.md)

### `action_engine/`

- [`action_engine/00-estructura.md`](action_engine/00-estructura.md)
- [`action_engine/__init__.md`](action_engine/__init__.md)
- [`action_engine/actions/00-estructura.md`](action_engine/actions/00-estructura.md)
- [`action_engine/actions/__init__.md`](action_engine/actions/__init__.md)
- [`action_engine/actions/catalog.md`](action_engine/actions/catalog.md)
- [`action_engine/context.md`](action_engine/context.md)
- [`action_engine/i18n.md`](action_engine/i18n.md)
- [`action_engine/learning.md`](action_engine/learning.md)
- [`action_engine/metrics.md`](action_engine/metrics.md)
- [`action_engine/models.md`](action_engine/models.md)
- [`action_engine/registry.md`](action_engine/registry.md)
- [`action_engine/runner.md`](action_engine/runner.md)
- [`action_engine/scheduler.md`](action_engine/scheduler.md)
- [`action_engine/signals.md`](action_engine/signals.md)
- [`action_engine/store.md`](action_engine/store.md)

### `autopilot/`

- [`autopilot/00-estructura.md`](autopilot/00-estructura.md)
- [`autopilot/__init__.md`](autopilot/__init__.md)
- [`autopilot/cli.md`](autopilot/cli.md)
- [`autopilot/config.md`](autopilot/config.md)
- [`autopilot/detectors/00-estructura.md`](autopilot/detectors/00-estructura.md)
- [`autopilot/detectors/ambiguous.md`](autopilot/detectors/ambiguous.md)
- [`autopilot/detectors/base.md`](autopilot/detectors/base.md)
- [`autopilot/detectors/default.md`](autopilot/detectors/default.md)
- [`autopilot/doctor.md`](autopilot/doctor.md)
- [`autopilot/errors.md`](autopilot/errors.md)
- [`autopilot/lifecycle.md`](autopilot/lifecycle.md)
- [`autopilot/mcp_tools.md`](autopilot/mcp_tools.md)
- [`autopilot/models.md`](autopilot/models.md)
- [`autopilot/policies.md`](autopilot/policies.md)
- [`autopilot/service.md`](autopilot/service.md)

### `brain/`

- [`brain/00-estructura.md`](brain/00-estructura.md)
- [`brain/__init__.md`](brain/__init__.md)
- [`brain/chat.md`](brain/chat.md)
- [`brain/cli.md`](brain/cli.md)
- [`brain/router.md`](brain/router.md)
- [`brain/tools.md`](brain/tools.md)

### `ci/`

- [`ci/00-estructura.md`](ci/00-estructura.md)
- [`ci/__init__.md`](ci/__init__.md)
- [`ci/diff_io.md`](ci/diff_io.md)
- [`ci/markdown_formatter.md`](ci/markdown_formatter.md)
- [`ci/result.md`](ci/result.md)
- [`ci/review_session.md`](ci/review_session.md)
- [`ci/session_matcher.md`](ci/session_matcher.md)
- [`ci/validator.md`](ci/validator.md)

### `cli/`

- [`cli/00-estructura.md`](cli/00-estructura.md)
- [`cli/__init__.md`](cli/__init__.md)
- [`cli/_search_filters.md`](cli/_search_filters.md)
- [`cli/_setup_helpers.md`](cli/_setup_helpers.md)
- [`cli/_unicode_fallback.md`](cli/_unicode_fallback.md)
- [`cli/ci.md`](cli/ci.md)
- [`cli/common.md`](cli/common.md)
- [`cli/docs_migrate.md`](cli/docs_migrate.md)
- [`cli/docs_search.md`](cli/docs_search.md)
- [`cli/docs_subcommand.md`](cli/docs_subcommand.md)
- [`cli/docs_vectorization.md`](cli/docs_vectorization.md)
- [`cli/documenting.md`](cli/documenting.md)
- [`cli/embedding.md`](cli/embedding.md)
- [`cli/hu.md`](cli/hu.md)
- [`cli/ide.md`](cli/ide.md)
- [`cli/main.md`](cli/main.md)
- [`cli/mcp_cmd.md`](cli/mcp_cmd.md)
- [`cli/next.md`](cli/next.md)
- [`cli/pr_context.md`](cli/pr_context.md)
- [`cli/review_knowledge.md`](cli/review_knowledge.md)
- [`cli/session.md`](cli/session.md)
- [`cli/session_tui.md`](cli/session_tui.md)

### `context_enricher/`

- [`context_enricher/00-estructura.md`](context_enricher/00-estructura.md)
- [`context_enricher/__init__.md`](context_enricher/__init__.md)
- [`context_enricher/async_enricher.md`](context_enricher/async_enricher.md)
- [`context_enricher/budget_resolver.md`](context_enricher/budget_resolver.md)
- [`context_enricher/co_occurrence.md`](context_enricher/co_occurrence.md)
- [`context_enricher/config.md`](context_enricher/config.md)
- [`context_enricher/doc_intent.md`](context_enricher/doc_intent.md)
- [`context_enricher/domain_detector.md`](context_enricher/domain_detector.md)
- [`context_enricher/enricher.md`](context_enricher/enricher.md)
- [`context_enricher/filters.md`](context_enricher/filters.md)
- [`context_enricher/observer.md`](context_enricher/observer.md)
- [`context_enricher/presenter.md`](context_enricher/presenter.md)
- [`context_enricher/telemetry.md`](context_enricher/telemetry.md)

### `documentation/`

- [`documentation/00-estructura.md`](documentation/00-estructura.md)
- [`documentation/__init__.md`](documentation/__init__.md)
- [`documentation/audit.md`](documentation/audit.md)
- [`documentation/backup.md`](documentation/backup.md)
- [`documentation/common.md`](documentation/common.md)
- [`documentation/data.md`](documentation/data.md)
- [`documentation/doc_type.md`](documentation/doc_type.md)
- [`documentation/errors.md`](documentation/errors.md)
- [`documentation/inventory.md`](documentation/inventory.md)
- [`documentation/migration.md`](documentation/migration.md)
- [`documentation/routing.md`](documentation/routing.md)
- [`documentation/schemas/00-estructura.md`](documentation/schemas/00-estructura.md)
- [`documentation/schemas/__init__.md`](documentation/schemas/__init__.md)
- [`documentation/schemas/adr.md`](documentation/schemas/adr.md)
- [`documentation/schemas/architecture.md`](documentation/schemas/architecture.md)
- [`documentation/schemas/base.md`](documentation/schemas/base.md)
- [`documentation/schemas/changelog.md`](documentation/schemas/changelog.md)
- [`documentation/schemas/decision.md`](documentation/schemas/decision.md)
- [`documentation/schemas/design.md`](documentation/schemas/design.md)
- [`documentation/schemas/glossary.md`](documentation/schemas/glossary.md)
- [`documentation/schemas/handoff.md`](documentation/schemas/handoff.md)
- [`documentation/schemas/hu.md`](documentation/schemas/hu.md)
- [`documentation/schemas/incident.md`](documentation/schemas/incident.md)
- [`documentation/schemas/postmortem.md`](documentation/schemas/postmortem.md)
- [`documentation/schemas/runbook.md`](documentation/schemas/runbook.md)
- [`documentation/schemas/session.md`](documentation/schemas/session.md)
- [`documentation/schemas/spec.md`](documentation/schemas/spec.md)
- [`documentation/templates_engine.md`](documentation/templates_engine.md)
- [`documentation/validation.md`](documentation/validation.md)
- [`documentation/writers.md`](documentation/writers.md)

### `documenter/`

- [`documenter/00-estructura.md`](documenter/00-estructura.md)
- [`documenter/__init__.md`](documenter/__init__.md)
- [`documenter/adr_evaluator.md`](documenter/adr_evaluator.md)
- [`documenter/contradiction_detector.md`](documenter/contradiction_detector.md)
- [`documenter/diff_parser.md`](documenter/diff_parser.md)
- [`documenter/interactive.md`](documenter/interactive.md)
- [`documenter/persistence.md`](documenter/persistence.md)
- [`documenter/reconstruction.md`](documenter/reconstruction.md)
- [`documenter/spec_loader.md`](documenter/spec_loader.md)

### `embedders/`

- [`embedders/00-estructura.md`](embedders/00-estructura.md)
- [`embedders/__init__.md`](embedders/__init__.md)
- [`embedders/base.md`](embedders/base.md)
- [`embedders/factory.md`](embedders/factory.md)
- [`embedders/fastembedder.md`](embedders/fastembedder.md)
- [`embedders/language.md`](embedders/language.md)
- [`embedders/local.md`](embedders/local.md)
- [`embedders/onnx.md`](embedders/onnx.md)
- [`embedders/openai.md`](embedders/openai.md)

### `enterprise/`

- [`enterprise/00-estructura.md`](enterprise/00-estructura.md)
- [`enterprise/__init__.md`](enterprise/__init__.md)
- [`enterprise/config.md`](enterprise/config.md)
- [`enterprise/governance.md`](enterprise/governance.md)
- [`enterprise/knowledge_promotion.md`](enterprise/knowledge_promotion.md)
- [`enterprise/maintenance.md`](enterprise/maintenance.md)
- [`enterprise/models.md`](enterprise/models.md)
- [`enterprise/promotion_doctype.md`](enterprise/promotion_doctype.md)
- [`enterprise/promotion_models.md`](enterprise/promotion_models.md)
- [`enterprise/reporting.md`](enterprise/reporting.md)
- [`enterprise/retrieval_service.md`](enterprise/retrieval_service.md)
- [`enterprise/sources.md`](enterprise/sources.md)

### `episodic/`

- [`episodic/00-estructura.md`](episodic/00-estructura.md)
- [`episodic/__init__.md`](episodic/__init__.md)
- [`episodic/embedder.md`](episodic/embedder.md)
- [`episodic/memory_store.md`](episodic/memory_store.md)
- [`episodic/summarizer.md`](episodic/summarizer.md)

### `hooks/`

- [`hooks/00-estructura.md`](hooks/00-estructura.md)
- [`hooks/__init__.md`](hooks/__init__.md)
- [`hooks/agent_hooks.md`](hooks/agent_hooks.md)

### `ide/`

- [`ide/00-estructura.md`](ide/00-estructura.md)
- [`ide/__init__.md`](ide/__init__.md)
- [`ide/adapters/00-estructura.md`](ide/adapters/00-estructura.md)
- [`ide/adapters/__init__.md`](ide/adapters/__init__.md)
- [`ide/adapters/antigravity.md`](ide/adapters/antigravity.md)
- [`ide/adapters/claude_code.md`](ide/adapters/claude_code.md)
- [`ide/adapters/claude_desktop.md`](ide/adapters/claude_desktop.md)
- [`ide/adapters/codex.md`](ide/adapters/codex.md)
- [`ide/adapters/cursor.md`](ide/adapters/cursor.md)
- [`ide/adapters/hermes.md`](ide/adapters/hermes.md)
- [`ide/adapters/opencode.md`](ide/adapters/opencode.md)
- [`ide/adapters/pi.md`](ide/adapters/pi.md)
- [`ide/adapters/vscode.md`](ide/adapters/vscode.md)
- [`ide/adapters/windsurf.md`](ide/adapters/windsurf.md)
- [`ide/adapters/zed.md`](ide/adapters/zed.md)
- [`ide/base.md`](ide/base.md)
- [`ide/canonical_tools.md`](ide/canonical_tools.md)
- [`ide/prompts.md`](ide/prompts.md)
- [`ide/registry.md`](ide/registry.md)

### `mcp/`

- [`mcp/00-estructura.md`](mcp/00-estructura.md)
- [`mcp/_subprocess.md`](mcp/_subprocess.md)
- [`mcp/schemas.md`](mcp/schemas.md)
- [`mcp/server.md`](mcp/server.md)
- [`mcp/tools/00-estructura.md`](mcp/tools/00-estructura.md)
- [`mcp/tools/__init__.md`](mcp/tools/__init__.md)
- [`mcp/tools/documenter.md`](mcp/tools/documenter.md)
- [`mcp/tools/search.md`](mcp/tools/search.md)
- [`mcp/tools/sessions.md`](mcp/tools/sessions.md)
- [`mcp/tools/workspace.md`](mcp/tools/workspace.md)
- [`mcp/vault_adapter.md`](mcp/vault_adapter.md)

### `pipeline/`

- [`pipeline/00-estructura.md`](pipeline/00-estructura.md)
- [`pipeline/__init__.md`](pipeline/__init__.md)
- [`pipeline/domain/00-estructura.md`](pipeline/domain/00-estructura.md)
- [`pipeline/domain/__init__.md`](pipeline/domain/__init__.md)
- [`pipeline/domain/context.md`](pipeline/domain/context.md)
- [`pipeline/domain/protocols.md`](pipeline/domain/protocols.md)
- [`pipeline/domain/types.md`](pipeline/domain/types.md)
- [`pipeline/orchestrator.md`](pipeline/orchestrator.md)
- [`pipeline/runners/00-estructura.md`](pipeline/runners/00-estructura.md)
- [`pipeline/runners/__init__.md`](pipeline/runners/__init__.md)
- [`pipeline/runners/github.md`](pipeline/runners/github.md)
- [`pipeline/stages/00-estructura.md`](pipeline/stages/00-estructura.md)
- [`pipeline/stages/__init__.md`](pipeline/stages/__init__.md)
- [`pipeline/stages/documentation.md`](pipeline/stages/documentation.md)
- [`pipeline/stages/lint.md`](pipeline/stages/lint.md)
- [`pipeline/stages/security.md`](pipeline/stages/security.md)
- [`pipeline/stages/test.md`](pipeline/stages/test.md)

### `raiz/`

- [`raiz/00-estructura.md`](raiz/00-estructura.md)
- [`raiz/__init__.md`](raiz/__init__.md)
- [`raiz/core.md`](raiz/core.md)
- [`raiz/doc_generator.md`](raiz/doc_generator.md)
- [`raiz/doc_validator.md`](raiz/doc_validator.md)
- [`raiz/doc_verifier.md`](raiz/doc_verifier.md)
- [`raiz/doctor.md`](raiz/doctor.md)
- [`raiz/feedback_loop.md`](raiz/feedback_loop.md)
- [`raiz/feedback_store.md`](raiz/feedback_store.md)
- [`raiz/git_policy.md`](raiz/git_policy.md)
- [`raiz/handoff.md`](raiz/handoff.md)
- [`raiz/memory_decay.md`](raiz/memory_decay.md)
- [`raiz/models.md`](raiz/models.md)
- [`raiz/pr_capture.md`](raiz/pr_capture.md)
- [`raiz/runtime_context.md`](raiz/runtime_context.md)

### `retrieval/`

- [`retrieval/00-estructura.md`](retrieval/00-estructura.md)
- [`retrieval/__init__.md`](retrieval/__init__.md)
- [`retrieval/hybrid_search.md`](retrieval/hybrid_search.md)
- [`retrieval/intent.md`](retrieval/intent.md)

### `security/`

- [`security/00-estructura.md`](security/00-estructura.md)
- [`security/__init__.md`](security/__init__.md)
- [`security/paths.md`](security/paths.md)

### `semantic/`

- [`semantic/00-estructura.md`](semantic/00-estructura.md)
- [`semantic/__init__.md`](semantic/__init__.md)
- [`semantic/chunker.md`](semantic/chunker.md)
- [`semantic/markdown_parser.md`](semantic/markdown_parser.md)
- [`semantic/native_vector_cache.md`](semantic/native_vector_cache.md)
- [`semantic/vault_reader.md`](semantic/vault_reader.md)
- [`semantic/vector_cache.md`](semantic/vector_cache.md)

### `services/`

- [`services/00-estructura.md`](services/00-estructura.md)
- [`services/__init__.md`](services/__init__.md)
- [`services/note_service.md`](services/note_service.md)
- [`services/pr_service.md`](services/pr_service.md)
- [`services/session_service.md`](services/session_service.md)
- [`services/spec_service.md`](services/spec_service.md)

### `session/`

- [`session/00-estructura.md`](session/00-estructura.md)
- [`session/__init__.md`](session/__init__.md)
- [`session/errors.md`](session/errors.md)
- [`session/git.md`](session/git.md)
- [`session/hooks/00-estructura.md`](session/hooks/00-estructura.md)
- [`session/hooks/__init__.md`](session/hooks/__init__.md)
- [`session/hooks/adapters/00-estructura.md`](session/hooks/adapters/00-estructura.md)
- [`session/hooks/adapters/__init__.md`](session/hooks/adapters/__init__.md)
- [`session/hooks/adapters/claude_code.md`](session/hooks/adapters/claude_code.md)
- [`session/hooks/adapters/cursor.md`](session/hooks/adapters/cursor.md)
- [`session/hooks/adapters/opencode.md`](session/hooks/adapters/opencode.md)
- [`session/hooks/adapters/pi.md`](session/hooks/adapters/pi.md)
- [`session/hooks/installer.md`](session/hooks/installer.md)
- [`session/models.md`](session/models.md)
- [`session/proposal.md`](session/proposal.md)
- [`session/quality_gates.md`](session/quality_gates.md)
- [`session/service.md`](session/service.md)
- [`session/storage.md`](session/storage.md)
- [`session/verification.md`](session/verification.md)

### `setup/`

- [`setup/00-estructura.md`](setup/00-estructura.md)
- [`setup/__init__.md`](setup/__init__.md)
- [`setup/cold_start.md`](setup/cold_start.md)
- [`setup/cortex_workspace.md`](setup/cortex_workspace.md)
- [`setup/detector.md`](setup/detector.md)
- [`setup/enterprise_presets.md`](setup/enterprise_presets.md)
- [`setup/enterprise_wizard.md`](setup/enterprise_wizard.md)
- [`setup/orchestrator.md`](setup/orchestrator.md)
- [`setup/templates.md`](setup/templates.md)

### `skills/`

- [`skills/00-estructura.md`](skills/00-estructura.md)
- [`skills/__init__.md`](skills/__init__.md)

### `tui/`

- [`tui/00-estructura.md`](tui/00-estructura.md)
- [`tui/__init__.md`](tui/__init__.md)
- [`tui/core.md`](tui/core.md)

### `tutor/`

- [`tutor/00-estructura.md`](tutor/00-estructura.md)
- [`tutor/__init__.md`](tutor/__init__.md)
- [`tutor/engine.md`](tutor/engine.md)
- [`tutor/hint.md`](tutor/hint.md)
- [`tutor/topics/00-estructura.md`](tutor/topics/00-estructura.md)
- [`tutor/topics/__init__.md`](tutor/topics/__init__.md)
- [`tutor/topics/commands.md`](tutor/topics/commands.md)
- [`tutor/topics/enterprise.md`](tutor/topics/enterprise.md)
- [`tutor/topics/getting_started.md`](tutor/topics/getting_started.md)
- [`tutor/topics/ide_integration.md`](tutor/topics/ide_integration.md)
- [`tutor/topics/pipeline.md`](tutor/topics/pipeline.md)
- [`tutor/topics/vault.md`](tutor/topics/vault.md)
- [`tutor/topics/workflow.md`](tutor/topics/workflow.md)

### `webgraph/`

- [`webgraph/00-estructura.md`](webgraph/00-estructura.md)
- [`webgraph/__init__.md`](webgraph/__init__.md)
- [`webgraph/cache.md`](webgraph/cache.md)
- [`webgraph/cli.md`](webgraph/cli.md)
- [`webgraph/config.md`](webgraph/config.md)
- [`webgraph/contracts.md`](webgraph/contracts.md)
- [`webgraph/episodic_source.md`](webgraph/episodic_source.md)
- [`webgraph/federation.md`](webgraph/federation.md)
- [`webgraph/graph_builder.md`](webgraph/graph_builder.md)
- [`webgraph/openers.md`](webgraph/openers.md)
- [`webgraph/relation_builder.md`](webgraph/relation_builder.md)
- [`webgraph/semantic_source.md`](webgraph/semantic_source.md)
- [`webgraph/server.md`](webgraph/server.md)
- [`webgraph/service.md`](webgraph/service.md)
- [`webgraph/setup.md`](webgraph/setup.md)
- [`webgraph/static_app.md`](webgraph/static_app.md)
- [`webgraph/static_style.md`](webgraph/static_style.md)
- [`webgraph/style.md`](webgraph/style.md)
- [`webgraph/templates_index.md`](webgraph/templates_index.md)

### `workitems/`

- [`workitems/00-estructura.md`](workitems/00-estructura.md)
- [`workitems/__init__.md`](workitems/__init__.md)
- [`workitems/models.md`](workitems/models.md)
- [`workitems/providers/00-estructura.md`](workitems/providers/00-estructura.md)
- [`workitems/providers/__init__.md`](workitems/providers/__init__.md)
- [`workitems/providers/base.md`](workitems/providers/base.md)
- [`workitems/providers/jira.md`](workitems/providers/jira.md)
- [`workitems/service.md`](workitems/service.md)

### `workspace/`

- [`workspace/00-estructura.md`](workspace/00-estructura.md)
- [`workspace/__init__.md`](workspace/__init__.md)
- [`workspace/layout.md`](workspace/layout.md)

---
Fuente: código `cortex/` + AST. Prohibido usar docs previas.