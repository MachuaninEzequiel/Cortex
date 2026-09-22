# Estructura — paquete `cortex/`

## Qué es esta carpeta

Paquete Python `cortex` (nombre de distribución `cortex-memory`). `cortex/__init__.py` declara `__version__ = "0.7.0"` y exporta la fachada pública (`AgentMemory`, stores, servicios, pipeline, modelos). Es la implementación Python del sistema de memoria híbrida: episódica (ChromaDB + embeddings) + semántica (vault Markdown) + fusión RRF, más CLI Typer, servidor MCP, sesiones, documenter, enterprise, webgraph, ActionEngine y setup de IDEs.

El script de consola en `pyproject.toml` es `cortex = "cortex.cli.main:app"`.

## Árbol interno (sin `__pycache__`)

```
cortex/
├── action_engine/
│   ├── actions/
│   │   ├── __init__.py
│   │   └── catalog.py
│   ├── __init__.py
│   ├── context.py
│   ├── i18n.py
│   ├── learning.py
│   ├── metrics.py
│   ├── models.py
│   ├── registry.py
│   ├── runner.py
│   ├── scheduler.py
│   ├── signals.py
│   └── store.py
├── autopilot/
│   ├── detectors/
│   │   ├── ambiguous.py
│   │   ├── base.py
│   │   └── default.py
│   ├── pi/
│   │   ├── extensions/
│   │   │   └── cortex-autopilot.ts
│   │   └── skills/
│   │       └── using-cortex-autopilot/
│   │           └── SKILL.md
│   ├── skills/
│   │   ├── cortex-autopilot-finish.md
│   │   └── using-cortex-autopilot.md
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── doctor.py
│   ├── errors.py
│   ├── lifecycle.py
│   ├── mcp_tools.py
│   ├── models.py
│   ├── policies.py
│   └── service.py
├── brain/
│   ├── __init__.py
│   ├── chat.py
│   ├── cli.py
│   ├── router.py
│   └── tools.py
├── ci/
│   ├── __init__.py
│   ├── diff_io.py
│   ├── markdown_formatter.py
│   ├── result.py
│   ├── review_session.py
│   ├── session_matcher.py
│   └── validator.py
├── cli/
│   ├── __init__.py
│   ├── _search_filters.py
│   ├── _setup_helpers.py
│   ├── _unicode_fallback.py
│   ├── ci.py
│   ├── common.py
│   ├── docs_migrate.py
│   ├── docs_search.py
│   ├── docs_subcommand.py
│   ├── docs_vectorization.py
│   ├── documenting.py
│   ├── embedding.py
│   ├── hu.py
│   ├── ide.py
│   ├── main.py
│   ├── mcp_cmd.py
│   ├── next.py
│   ├── pr_context.py
│   ├── review_knowledge.py
│   ├── session.py
│   └── session_tui.py
├── context_enricher/
│   ├── __init__.py
│   ├── async_enricher.py
│   ├── budget_resolver.py
│   ├── co_occurrence.py
│   ├── config.py
│   ├── doc_intent.py
│   ├── domain_detector.py
│   ├── enricher.py
│   ├── filters.py
│   ├── observer.py
│   ├── presenter.py
│   └── telemetry.py
├── documentation/
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── adr.py
│   │   ├── architecture.py
│   │   ├── base.py
│   │   ├── changelog.py
│   │   ├── decision.py
│   │   ├── design.py
│   │   ├── glossary.py
│   │   ├── handoff.py
│   │   ├── hu.py
│   │   ├── incident.py
│   │   ├── postmortem.py
│   │   ├── runbook.py
│   │   ├── session.py
│   │   └── spec.py
│   ├── templates/
│   │   ├── adr.md.j2
│   │   ├── architecture.md.j2
│   │   ├── changelog.md.j2
│   │   ├── decision.md.j2
│   │   ├── design.md.j2
│   │   ├── glossary.md.j2
│   │   ├── handoff.md.j2
│   │   ├── hu.md.j2
│   │   ├── incident.md.j2
│   │   ├── postmortem.md.j2
│   │   ├── runbook.md.j2
│   │   ├── session.md.j2
│   │   └── spec.md.j2
│   ├── __init__.py
│   ├── audit.py
│   ├── backup.py
│   ├── common.py
│   ├── data.py
│   ├── doc_type.py
│   ├── errors.py
│   ├── inventory.py
│   ├── migration.py
│   ├── routing.py
│   ├── templates_engine.py
│   ├── validation.py
│   └── writers.py
├── documenter/
│   ├── __init__.py
│   ├── adr_evaluator.py
│   ├── contradiction_detector.py
│   ├── diff_parser.py
│   ├── interactive.py
│   ├── persistence.py
│   ├── reconstruction.py
│   └── spec_loader.py
├── embedders/
│   ├── __init__.py
│   ├── base.py
│   ├── factory.py
│   ├── fastembedder.py
│   ├── language.py
│   ├── local.py
│   ├── onnx.py
│   └── openai.py
├── enterprise/
│   ├── __init__.py
│   ├── config.py
│   ├── governance.py
│   ├── knowledge_promotion.py
│   ├── maintenance.py
│   ├── models.py
│   ├── promotion_doctype.py
│   ├── promotion_models.py
│   ├── reporting.py
│   ├── retrieval_service.py
│   └── sources.py
├── episodic/
│   ├── __init__.py
│   ├── embedder.py
│   ├── memory_store.py
│   └── summarizer.py
├── hooks/
│   ├── __init__.py
│   └── agent_hooks.py
├── ide/
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── antigravity.py
│   │   ├── claude_code.py
│   │   ├── claude_desktop.py
│   │   ├── codex.py
│   │   ├── cursor.py
│   │   ├── hermes.py
│   │   ├── opencode.py
│   │   ├── pi.py
│   │   ├── vscode.py
│   │   ├── windsurf.py
│   │   └── zed.py
│   ├── __init__.py
│   ├── base.py
│   ├── canonical_tools.py
│   ├── prompts.py
│   └── registry.py
├── mcp/
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── documenter.py
│   │   ├── search.py
│   │   ├── sessions.py
│   │   └── workspace.py
│   ├── _subprocess.py
│   ├── schemas.py
│   ├── server.py
│   └── vault_adapter.py
├── pipeline/
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── context.py
│   │   ├── protocols.py
│   │   └── types.py
│   ├── runners/
│   │   ├── __init__.py
│   │   └── github.py
│   ├── stages/
│   │   ├── __init__.py
│   │   ├── documentation.py
│   │   ├── lint.py
│   │   ├── security.py
│   │   └── test.py
│   ├── __init__.py
│   └── orchestrator.py
├── retrieval/
│   ├── __init__.py
│   ├── hybrid_search.py
│   └── intent.py
├── security/
│   ├── __init__.py
│   └── paths.py
├── semantic/
│   ├── __init__.py
│   ├── chunker.py
│   ├── markdown_parser.py
│   ├── native_vector_cache.py
│   ├── vault_reader.py
│   └── vector_cache.py
├── services/
│   ├── __init__.py
│   ├── note_service.py
│   ├── pr_service.py
│   ├── session_service.py
│   └── spec_service.py
├── session/
│   ├── hooks/
│   │   ├── adapters/
│   │   │   ├── __init__.py
│   │   │   ├── claude_code.py
│   │   │   ├── cursor.py
│   │   │   ├── opencode.py
│   │   │   └── pi.py
│   │   ├── __init__.py
│   │   └── installer.py
│   ├── __init__.py
│   ├── errors.py
│   ├── git.py
│   ├── models.py
│   ├── proposal.py
│   ├── quality_gates.py
│   ├── service.py
│   ├── storage.py
│   └── verification.py
├── setup/
│   ├── workspace_files/
│   │   ├── agent-overview.md
│   │   ├── cortex-documenter-close-craft.md
│   │   ├── cortex-documenter.md
│   │   ├── cortex-SDDwork-implement-craft.md
│   │   ├── cortex-SDDwork.md
│   │   ├── cortex-sync-proposal-craft.md
│   │   ├── cortex-sync-spec-craft.md
│   │   ├── cortex-sync.md
│   │   ├── obsidian-defuddle.md
│   │   ├── obsidian-json_canvas.md
│   │   ├── obsidian-obsidian_bases.md
│   │   ├── obsidian-obsidian_index.md
│   │   ├── obsidian-obsidian_markdown.md
│   │   ├── subagent-cortex-code-designer.md
│   │   ├── subagent-cortex-code-explorer.md
│   │   ├── subagent-cortex-code-implementer.md
│   │   ├── subagent-cortex-documenter.md
│   │   └── system-prompt.md
│   ├── __init__.py
│   ├── cold_start.py
│   ├── cortex_workspace.py
│   ├── detector.py
│   ├── enterprise_presets.py
│   ├── enterprise_wizard.py
│   ├── orchestrator.py
│   └── templates.py
├── skills/
│   ├── defuddle/
│   │   └── SKILL.md
│   ├── json-canvas/
│   │   ├── references/
│   │   │   └── EXAMPLES.md
│   │   └── SKILL.md
│   ├── obsidian-bases/
│   │   ├── references/
│   │   │   └── FUNCTIONS_REFERENCE.md
│   │   └── SKILL.md
│   ├── obsidian-cli/
│   │   └── SKILL.md
│   ├── obsidian-markdown/
│   │   ├── references/
│   │   │   ├── CALLOUTS.md
│   │   │   ├── EMBEDS.md
│   │   │   └── PROPERTIES.md
│   │   └── SKILL.md
│   └── __init__.py
├── tui/
│   ├── __init__.py
│   └── core.py
├── tutor/
│   ├── topics/
│   │   ├── __init__.py
│   │   ├── commands.py
│   │   ├── enterprise.py
│   │   ├── getting_started.py
│   │   ├── ide_integration.py
│   │   ├── pipeline.py
│   │   ├── vault.py
│   │   └── workflow.py
│   ├── __init__.py
│   ├── engine.py
│   └── hint.py
├── webgraph/
│   ├── static/
│   │   ├── app.js
│   │   └── style.css
│   ├── templates/
│   │   └── index.html
│   ├── __init__.py
│   ├── cache.py
│   ├── cli.py
│   ├── config.py
│   ├── contracts.py
│   ├── episodic_source.py
│   ├── federation.py
│   ├── graph_builder.py
│   ├── openers.py
│   ├── relation_builder.py
│   ├── semantic_source.py
│   ├── server.py
│   ├── service.py
│   ├── setup.py
│   └── style.py
├── workitems/
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── jira.py
│   ├── __init__.py
│   ├── models.py
│   └── service.py
├── workspace/
│   ├── __init__.py
│   └── layout.py
├── __init__.py
├── agent_guidelines.md
├── agent_guidelines_work.md
├── core.py
├── doc_generator.py
├── doc_validator.py
├── doc_verifier.py
├── doctor.py
├── feedback_loop.py
├── feedback_store.py
├── git_policy.py
├── handoff.py
├── memory_decay.py
├── models.py
├── pr_capture.py
└── runtime_context.py
```

## Subpaquetes

- `action_engine/` — 13 `.py`. cortex.action_engine — motor de acciones con aprendizaje (Obra 05).
- `autopilot/` — 13 `.py`. cortex.autopilot — Policy + hooks layer over the cortex.session primitive.
- `brain/` — 5 `.py`. cortex.brain — DEPRECATED (dueño, 2026-08-25 — doc 12 §4.2).
- `ci/` — 7 `.py`. cortex.ci — Phase 07 CI plugin (Pluggable Middle).
- `cli/` — 21 `.py`. (sin docstring de paquete; reexportes)
- `context_enricher/` — 12 `.py`. cortex.context_enricher ----------------------- Proactive context engine for AI agents.
- `documentation/` — 28 `.py`. cortex.documentation - Canonical documentation system.
- `documenter/` — 8 `.py`. cortex.documenter — Documenter Reconstruction Mode (Phase 01).
- `embedders/` — 8 `.py`. cortex.embedders ---------------- Strategy-based embedding backends for Cortex.
- `enterprise/` — 11 `.py`. (sin docstring de paquete; reexportes)
- `episodic/` — 4 `.py`. (sin docstring de paquete; reexportes)
- `hooks/` — 2 `.py`. (sin docstring de paquete; reexportes)
- `ide/` — 17 `.py`. cortex.ide ---------- IDE adapter layer for Cortex agent profile injection.
- `mcp/` — 9 `.py`. 
- `pipeline/` — 13 `.py`. cortex.pipeline --------------- DevSecDocOps Pipeline — formal Python abstraction for CI/CD stages.
- `retrieval/` — 3 `.py`. (sin docstring de paquete; reexportes)
- `security/` — 2 `.py`. Cortex security utilities.
- `semantic/` — 6 `.py`. (sin docstring de paquete; reexportes)
- `services/` — 5 `.py`. cortex.services --------------- Domain service layer for Cortex.
- `session/` — 16 `.py`. cortex.session — Session primitive for the Pluggable Middle architecture.
- `setup/` — 8 `.py`. cortex.setup ------------ Project setup and auto-detection utilities for the ``cortex setup`` command.
- `skills/` — 1 `.py`. cortex.skills ------------- Bundled Obsidian skills for Markdown documentation.
- `tui/` — 2 `.py`. cortex.tui — pantallas rich del Home/acciones/sesión/búsqueda (Obra 05 Fase D).
- `tutor/` — 11 `.py`. cortex.tutor ------------ Offline interactive tutorial and contextual hint system. Zero tokens consumed — all content is static and local.
- `webgraph/` — 15 `.py`. cortex.webgraph ---------------- Hybrid memory graph projection for Cortex.
- `workitems/` — 6 `.py`. cortex.workitems ---------------- Optional work item integration layer for Cortex.
- `workspace/` — 2 `.py`. cortex.workspace --------------- Workspace layout resolution for Cortex projects.

## Archivos de raíz (`cortex/*.py`)

- `__init__.py`
- `core.py`
- `doc_generator.py`
- `doc_validator.py`
- `doc_verifier.py`
- `doctor.py`
- `feedback_loop.py`
- `feedback_store.py`
- `git_policy.py`
- `handoff.py`
- `memory_decay.py`
- `models.py`
- `pr_capture.py`
- `runtime_context.py`

Cada uno tiene ficha en `ConaISI/cortex/raiz/`.

## Assets de runtime (no Python)

- `agent_guidelines.md`, `agent_guidelines_work.md` — package-data. No se usaron como fuente de arquitectura.
- `documentation/templates/*.md.j2` — plantillas Jinja2 de writers canónicos.
- `setup/workspace_files/*.md` — copiados por setup; su prosa no se tomó como verdad del producto.
- `skills/**` — skills Obsidian embebidas; `cortex.skills.install_skills` las copia. La prosa de SKILL.md no se usó como arquitectura.
- `webgraph/templates/index.html`, `webgraph/static/{app.js,style.css}` — UI Flask del grafo (fichas en `webgraph/`).
- `autopilot/skills/`, `autopilot/pi/` — skills y extensión TypeScript para Pi.

## Relaciones observadas desde el código

- Lee config vía `WorkspaceLayout` + `CortexConfig` (`core.py`).
- Escribe vault Markdown, persistencia Chroma, YAML de sesiones, logs MCP, `action_log.jsonl`, `feedback.jsonl`.
- Expone CLI (`cortex.cli.main`) y MCP stdio (`cortex.mcp.server`).
- `semantic/vault_reader.py` puede usar `cortex_core._native` si `CORTEX_NATIVE=1`.
- `cortex.brain.__init__` marca el brain Python como **DEPRECATED** frente a `cortex-brain` (Rust).

---
Fuente: árbol y código de `cortex/`. No se usó documentación previa.
