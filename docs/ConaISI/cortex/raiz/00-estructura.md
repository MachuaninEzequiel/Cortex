# Estructura — `cortex/`

## Para qué existe esta carpeta

Módulos de primer nivel del paquete `cortex`: fachada `AgentMemory` (`core.py`), modelos Pydantic compartidos (`models.py`), diagnóstico (`doctor.py`), decay/feedback, captura de PRs, handoff legado YAML, y helpers de git/runtime.

## Árbol interno (código, sin `__pycache__`)

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

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/__init__.py` | 84 | Cortex — Hybrid Memory System for AI Agents. |
| `cortex/core.py` | 1066 | cortex.core ----------- ``AgentMemory`` — the unified public façade for the Cortex memory system. |
| `cortex/doc_generator.py` | 180 | cortex.doc_generator -------------------- **Fallback** documentation generator for PR context and pipeline results. |
| `cortex/doc_validator.py` | 208 | cortex.doc_validator -------------------- Validates agent-generated documentation in the vault. |
| `cortex/doc_verifier.py` | 205 | cortex.doc_verifier ------------------- Detects whether a PR includes agent-generated documentation in the vault. |
| `cortex/doctor.py` | 926 | DoctorCheck, DoctorReport, run_doctor, _validate_sessions, _validate_autopilot_policy, _validate_session_hooks, _validate_pluggable_middle_health, _is_writable, _validate_vault, _validate_enterprise, _validate_enterprise_vault, _validate_enterprise_promotion |
| `cortex/feedback_loop.py` | 527 | cortex.feedback_loop -------------------- Feedback Loop system for learning from context usefulness. |
| `cortex/feedback_store.py` | 85 | Persistencia de feedback en ``.cortex/feedback.jsonl`` (Obra 05 Fase A). |
| `cortex/git_policy.py` | 112 | cortex.git_policy ----------------- Git policy helpers for Cortex projects. |
| `cortex/handoff.py` | 122 | cortex.handoff — Structured agent handoff schema (Legacy YAML contract). |
| `cortex/memory_decay.py` | 189 | cortex.memory_decay ----------------- Memory Decay system for temporal relevance. |
| `cortex/models.py` | 408 | cortex.models ------------- Shared Pydantic models used across the cortex package. |
| `cortex/pr_capture.py` | 198 | cortex.pr_capture ----------------- Captures pull request metadata and git diff information into a PRContext. |
| `cortex/runtime_context.py` | 59 | slugify, _run_git_command, detect_git_branch, detect_git_repo_path, resolve_episodic_persist_dir |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.core`
- `cortex.doc_validator`
- `cortex.embedders`
- `cortex.enterprise.config`
- `cortex.enterprise.models`
- `cortex.enterprise.retrieval_service`
- `cortex.episodic.memory_store`
- `cortex.episodic.summarizer`
- `cortex.git_policy`
- `cortex.models`
- `cortex.pipeline`
- `cortex.retrieval.hybrid_search`
- `cortex.runtime_context`
- `cortex.semantic.vault_reader`
- `cortex.services`
- `cortex.services.note_service`
- `cortex.services.pr_service`
- `cortex.services.spec_service`
- `cortex.session`
- `cortex.session.service`
- `cortex.session.storage`
- `cortex.webgraph.setup`
- `cortex.workitems.providers.jira`
- `cortex.workitems.service`
- `cortex.workspace.layout`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.__init__`
- `cortex.cli.common`
- `cortex.context_enricher.async_enricher`
- `cortex.context_enricher.enricher`
- `cortex.context_enricher.filters`
- `cortex.core`
- `cortex.doc_generator`
- `cortex.doctor`
- `cortex.documenter.reconstruction`
- `cortex.enterprise.config`
- `cortex.enterprise.knowledge_promotion`
- `cortex.enterprise.models`
- `cortex.enterprise.reporting`
- `cortex.enterprise.retrieval_service`
- `cortex.enterprise.sources`
- `cortex.episodic.memory_store`
- `cortex.hooks.agent_hooks`
- `cortex.mcp.server`
- `cortex.mcp.tools.search`
- `cortex.pr_capture`
- `cortex.retrieval.hybrid_search`
- `cortex.semantic.markdown_parser`
- `cortex.semantic.vault_reader`
- `cortex.services.note_service`
- `cortex.services.pr_service`
- `cortex.services.spec_service`
- `cortex.setup.templates`
- `cortex.webgraph.episodic_source`
- `cortex.webgraph.service`
- `cortex.webgraph.setup`
- `cortex.workitems.service`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
