---
title: Cortex — Save State Operativo del Agente
date: 2026-05-13
branch: feature/nuevo-modo-autonomo
agent: Cortex Agent
audience: Yo mismo (futuras sesiones) + futuros agentes que hereden el desarrollo
status: snapshot autoritativo del repo a esta fecha
---

# Cortex — Save State Operativo

Este documento existe para que pueda retomar el contexto completo de Cortex sin tener que releer el repo desde cero. Lo construí leyendo en orden: configs, runtime core, episodic/semantic/retrieval, services, enterprise, context_enricher, autopilot, MCP, IDEs, CLI, setup/templates, pipeline, workflows reales, webgraph, tutor, hooks, cortex-pi, docs estratégicos, tests y vault/architecture. Donde hay tensiones, las marco. Donde infiero algo no comprobado al 100%, lo digo. Donde un hallazgo histórico ya está resuelto, lo aclaro.

Convenciones internas de este documento:
- "verificado": leí el archivo directamente y confirmé con número de línea.
- "inferido": deduzco a partir de evidencia parcial.
- "incierto": no lo pude confirmar; lo dejo flagueado.
- Las rutas son relativas a `D:\DevSecDocOps\DevSecDocOps-3erCortex\cortex-repo\cortex`.

---

## 1. Resumen Ejecutivo

Cortex es un **sistema de memoria cognitiva, gobernanza DevSecDocOps y documentación viva** para agentes de IA. Combate la *amnesia de sesión*: persiste cada spec, sesión, decisión, PR, HU, incidente y aprendizaje en dos capas (episódica vectorial + semántica Markdown) más una capa enterprise federada. Expone su API por CLI (Typer), por servidor MCP, por adaptadores IDE y por una UI WebGraph. Opcionalmente incluye un módulo Autopilot que automatiza el ciclo sync → SDDwork → documenter.

Stack: Python ≥3.10, Pydantic v2, ChromaDB con ONNX MiniLM L6 v2 por defecto, Typer, Flask para WebGraph, MCP Python SDK. Empaquetado como `cortex-memory` con entrypoint `cortex = cortex.cli.main:app`.

Versionado:
- `pyproject.toml` y `cortex/__init__.py`: **0.3.0 Alpha** (normalizado recientemente, ver CHANGELOG "Unreleased").
- README y docs hablan de "v2.5" / "Release 2" como narrativa de roadmap, no como versión publicada.

---

## 2. Objetivo Estratégico

**Problema:** los agentes IA olvidan contexto entre sesiones. Los proyectos pierden trazabilidad de decisiones. La documentación se desfasa. El conocimiento queda atrapado por proyecto.

**Solución Cortex (la "promesa"):**
1. Persistir todo trabajo asistido por IA como memoria recuperable.
2. Forzar un ciclo disciplinado (sync → SDDwork → documenter) con guard rails reales en MCP.
3. Federar conocimiento entre proyectos (vault enterprise + retrieval multi-scope `local | enterprise | all`).
4. Materializar la documentación como subproducto automático del pipeline (DevSecOps → DevSecDocOps).
5. Hacer todo el grafo de conocimiento navegable visualmente (WebGraph).

**Visión a largo plazo (de `docs/vision/`):** transformar DevSecOps en DevSecDocOps — la documentación deja de ser fase final y se convierte en artefacto automático.

---

## 3. Mapa de Arquitectura por Capas

```
┌─────────────────────────────────────────────────────────┐
│  Superficies de usuario                                  │
│  CLI (Typer) │ MCP server │ IDE adapters │ WebGraph UI   │
├─────────────────────────────────────────────────────────┤
│  Autopilot (opcional, opt-in)                            │
│  start → preflight → checkpoint → finish → documented    │
├─────────────────────────────────────────────────────────┤
│  Façade  cortex.core.AgentMemory                         │
│   ├─ SpecService                                          │
│   ├─ SessionService                                       │
│   ├─ PRService                                            │
│   └─ WorkItemService (Jira read-only)                     │
├─────────────────────────────────────────────────────────┤
│  Retrieval & Context                                      │
│  HybridSearch (RRF adaptativo) │ ContextEnricher          │
│  EnterpriseRetrievalService (local/enterprise/all)        │
├──────────────────────┬──────────────────────────────────┤
│  Episodic            │  Semantic                         │
│  ChromaDB +          │  Vault Markdown (Obsidian)        │
│  ONNX MiniLM L6 v2   │  Frontmatter + wiki-links         │
├──────────────────────┴──────────────────────────────────┤
│  Workspace contract  WorkspaceLayout (dual layout)        │
├─────────────────────────────────────────────────────────┤
│  Pipeline (CI gates) Security · Lint · Test · Doc         │
└─────────────────────────────────────────────────────────┘
```

Concepto clave: **AgentMemory es un façade hexagonal**. Toda lógica de negocio vive en servicios. La infraestructura (Chroma, Vault, RRF) se inyecta. El CLI/MCP/IDE no tocan capas bajas: solo el façade.

---

## 4. Layout del Repo y Tensión Legacy / New Layout

`WorkspaceLayout` (`cortex/workspace/layout.py`) es **el contrato central de paths**. Soporta dos layouts:

**New layout (v2):**
```
<repo>/
  .cortex/
    config.yaml
    workspace.yaml      (layout_version: 2)
    vault/
    vault-enterprise/
    memory/
    enterprise-memory/
    org.yaml
    AGENT.md
    system-prompt.md
    skills/  subagents/  webgraph/  logs/  scripts/
  .github/workflows/
```

**Legacy layout (v1):**
```
<repo>/
  config.yaml
  vault/
  vault-enterprise/
  .memory/
  .cortex/
    org.yaml
    skills/  subagents/  AGENT.md  system-prompt.md  webgraph/  logs/
  scripts/
  .github/workflows/
```

`WorkspaceLayout.discover(start)` camina hacia arriba buscando (en orden):
1. `<repo>/.cortex/workspace.yaml` con `layout_version >= 2` → new.
2. `<repo>/.cortex/config.yaml` sin un `<repo>/config.yaml` paralelo → new.
3. `<repo>/config.yaml` o `<repo>/.cortex/` con `.git/` → legacy.
4. Bootstrap: git root o `start` mismo, asumido como new.

### Tensión real en este repo concreto (verificada)

Este repo está en **modo legacy**:
- `config.yaml` en raíz (no en `.cortex/`).
- `vault/` y `.memory/` en raíz.
- `.cortex/` solo tiene `AGENT.md`, `system-prompt.md`, `skills/`, `subagents/`, `logs/`, `webgraph/`.
- `.gitignore` ignora `.memory/`, `vault/sessions/`, `.cortex/logs/`.

Los **defaults del código** (`EpisodicConfig.persist_dir = "memory"`, `SemanticConfig.vault_path = "vault"` en `core.py:68,77`) asumen new layout. El **config.yaml de este repo** lo sobreescribe con `.memory/chroma` (legacy). Cuando se hace `AgentMemory("config.yaml")`, se carga el dict crudo y `resolve_episodic_persist_dir(workspace_root, raw)` lo resuelve relativo a workspace_root. En legacy, `workspace_root == repo_root`, así que `.memory/chroma` queda bien. En new layout sería `.cortex/.memory/chroma` — patológico, pero `setup` regenera config con `memory` plano. **Implicación: si alguna vez migrás este repo a new layout, hay que re-renderizar config.yaml.**

`AgentMemory.__init__` (core.py:137-154) tiene una sutileza: **carga `config.yaml` antes de descubrir el layout**. Toma el `config_path` que recibe (default `"config.yaml"` relativo a cwd). Esto significa que para que funcione en new layout sin pasar `--project-root`, hay que correr `cortex ...` desde `.cortex/` o pasar el path explícito. La discovery posterior solo afecta resolución de paths relativos, no la carga inicial del config. **Riesgo:** UX confusa si alguien corre `cortex search` desde el repo root de un new-layout sin `--project-root`. Lo más probable es que CLI resuelva esto explícitamente antes (verificable buscando uso de `_DEFAULT_CONFIG` y `WorkspaceLayout.discover` en `cortex/cli/main.py:1-200` cuando lo necesite).

### Convenciones runtime (verificadas en core.py)

- `self.repo_root` = git root o `start`.
- `self.workspace_root` = `repo_root` (legacy) o `repo_root/.cortex` (new).
- `self.project_root` = alias de `workspace_root` (compat).
- `self.project_id` = slug del nombre del repo root.
- `self.git_branch` = `git rev-parse --abbrev-ref HEAD` o `no-git-branch`.

---

## 5. Mapa Módulo por Módulo de `cortex/`

### 5.1 `cortex/core.py` — el façade
**Clase:** `AgentMemory` (706 líneas).
- Configs internos (Pydantic): `EpisodicConfig`, `SemanticConfig`, `RetrievalConfig`, `LLMConfig`, `JiraIntegrationConfig`, `IntegrationsConfig`, `CortexConfig`.
- Inyecta a init: `EpisodicMemoryStore`, `VaultReader`, `Summarizer`, `HybridSearch`, `SpecService`, `SessionService`, `PRService`, opcional `WorkItemService`. Carga enterprise opcional vía `load_enterprise_config(repo_root, required=False, workspace_layout)`.
- API pública:
  - `remember()`, `store_memory()` (alias), `retrieve()`, `forget()`, `stats()`.
  - `create_note()`, `sync_vault()`.
  - `create_spec_note()`, `save_session_note()`.
  - `store_pr_context()`, `generate_pr_docs()`, `write_pr_docs()`, `get_pr_context()`.
  - `import_work_item()`, `get_work_item_note()`, `list_work_item_notes()`.
  - `enrich()` → llama `ContextObserver` + `ContextEnricher`.
- `retrieve()` con `scope`: si scope ∈ {enterprise, all}, requiere `enterprise_config` y crea `EnterpriseRetrievalService` en demand. Si scope == local, usa `HybridSearch` directo.
- `namespace_mode == "branch"` filtra hits con `metadata['branch'] != git_branch` (post-search).

### 5.2 `cortex/models.py` — contratos cross-cutting
- `MemoryType` enum: general, session, hu, adr, incident, changelog, security, pr_summary, ci_failure, conversation.
- `MemoryEntry` (id, content, memory_type, tags, files, timestamp, metadata).
- `SemanticDocument` (path, title, content, links, tags, score, origin_scope/project_id/vault/persist_dir).
- `EpisodicHit` (entry, score, origin_*).
- `UnifiedHit` (source: episodic|semantic, score, entry|doc, metadata, display_title/content/path computed).
- `RetrievalResult` (query, episodic_hits, semantic_hits, **unified_hits**, source_breakdown, intent). **Tiene `to_prompt(max_chars=4000)`** — usa unified_hits si hay, sino fallback a listas separadas.
- `PRContext` (pr_number, title, body, author, source_branch, target_branch, commit_sha, files_changed, diff_summary, db_migrations, api_changes, labels, lint/audit/test_result). Helpers: `hu_references()`, `has_db_changes()`, `has_api_changes()`, `has_adr_label()`.
- `GeneratedDoc` (doc_type: session|hu|adr|incident|changelog|security, title, content, vault_subfolder, filename, full_path).
- `WorkContext`, `EnrichedItem`, `EnrichedContext`. **`EnrichedContext.to_prompt_format(compact, expand)`** — la API de presentación.

### 5.3 `cortex/runtime_context.py` — git + paths
Funciones: `slugify`, `_run_git_command`, `detect_git_branch`, `detect_git_repo_path`, `resolve_episodic_persist_dir`. Esta última aplica modos `project | branch | custom` de namespacing para Chroma.

### 5.4 `cortex/workspace/layout.py` — el contrato de paths
Ver sección 4. Properties relevantes: `config_path`, `org_config_path`, `vault_path`, `enterprise_vault_path`, `episodic_memory_path`, `enterprise_memory_path`, `skills_dir`, `subagents_dir`, `agent_guidelines_path`, `system_prompt_path`, `workspace_yaml_path`, `webgraph_dir/cache_dir/config_path/workspace_path`, `logs_dir`, `scripts_dir`, `workflows_dir`, `promotion_records_path/promotion_dir`, `vault_index_path`. Método clave: `resolve_workspace_relative(value)` para resolver paths relativos.

### 5.5 `cortex/episodic/`
- `memory_store.py` — `EpisodicMemoryStore`. Constructor inicia ChromaDB `PersistentClient` con HNSW cosine. `add()` extrae entidades (functions, classes, endpoints, errors, config_keys, dependencies, etc.), serializa a metadata plana, persiste, mantiene cache tokens. `search()`, `search_by_entity()`, `delete()`, `list_entries()`. **Hallazgo histórico:** `release-2-known-weaknesses` #1 menciona que entity persistence puede no round-trippear (entidades deserializadas mal). Hay que verificar antes de tocar.
- `embedder.py` — `Embedder` viejo, usado directamente por `EpisodicMemoryStore` y `VaultReader`. Soporta `onnx | local | openai`. Lazy load. Default ONNX usa el wrapper interno de Chroma `ONNXMiniLM_L6_V2` (~10MB descarga, sin PyTorch).
- `summarizer.py` — `Summarizer` para compresión LLM opcional (OpenAI/Anthropic/Ollama). Fallback: truncate 300 chars si provider=none.

### 5.6 `cortex/semantic/`
- `markdown_parser.py` — `MarkdownParser.parse()` extrae frontmatter YAML, contenido, wiki-links `[[...]]`, hashtags `#tag`.
- `vault_reader.py` — `VaultReader`. **Sí embebe documentos en `sync()`** (confirma CHANGELOG v2.0). Mantiene `.cortex_index.json` (BM25 metadata) + embeddings en RAM. API: `sync()`, `search()` (vector + BM25 fallback), `get()`, `count()`, `create_note()`, `update_note()`, `index_file()`. Lazy: si no se sincronizó, llama `sync()` al primer search.

### 5.7 `cortex/embedders/`
Factory paralelo "nuevo": `EmbedderProtocol` (base.py, runtime_checkable), `EmbedderFactory` (factory.py) con registry `onnx → OnnxEmbedder`, `local → LocalEmbedder`, `openai → OpenAIEmbedder`. **Tensión real:** ni `core.py` ni `EpisodicMemoryStore`/`VaultReader` invocan al factory; usan `cortex.episodic.embedder.Embedder`. Esto es coexistencia intencional (mismo vector space garantizado) pero deja al factory como "estructura preparada que aún no es usada". Probablemente parte de una migración Epica pendiente. Verificable con `grep -r "EmbedderFactory\b" cortex/` antes de cualquier refactor.

### 5.8 `cortex/retrieval/`
- `intent.py` — `QueryIntentDetector` lexicon-only (regex, <1ms). Clasifica query en EPISODIC / SEMANTIC / MIXED.
- `hybrid_search.py` — `HybridSearch`. `search()` over-fetch k*3 de cada fuente; fusiona con RRF (`K=60`). Si `adaptive_weights=True`, ajusta pesos según intent: EPISODIC→(2.0, 0.6), SEMANTIC→(0.6, 2.0), MIXED→(1.0, 1.0). Devuelve `RetrievalResult` con `unified_hits`.

### 5.9 `cortex/services/`
- `spec_service.py` — `SpecService.create()` genera frontmatter + body, escribe en `vault/specs/`, registra memoria episódica `memory_type=spec`, opcional `sync_vault`.
- `session_service.py` — `SessionService.create()` análogo, escribe en `vault/sessions/`, memoria `memory_type=session`.
- `pr_service.py` — `store_pr_context()` persiste como memoria, `generate_pr_docs()` produce `GeneratedDoc[]` fallback (session, hu, adr, changelog, security), `write_pr_docs()` los escribe en `vault/<subfolder>/`.

### 5.10 `cortex/workitems/`
- `service.py` — `WorkItemService.import_item(external_id, provider)`, `get_item_note(item_id)`, `list_item_notes()`. Escribe en `vault/hu/`.
- `providers/jira.py` — `JiraProvider` read-only (lee `JIRA_EMAIL`/`JIRA_API_TOKEN` env vars).
- `models.py` — `WorkItem`, etc.

### 5.11 `cortex/security/paths.py`
Helpers de validación de paths para evitar traversal. Es la superficie de seguridad central. Si voy a tocar cualquier escritura nueva al vault, **paso por aquí**.

### 5.12 `cortex/enterprise/`
- `models.py` — Pydantic schema completo: `OrganizationConfig` (slug, profile: small-company | multi-project-team | regulated-organization | custom), `MemoryConfig` (vault/memory paths, semantic/episodic enabled, project_memory_mode, branch_isolation, retrieval_default_scope, retrieval_local_weight, retrieval_enterprise_weight), `PromotionConfig`, `GovernanceConfig` (git_policy, ci_profile: observability | advisory | enforced, version_sessions_in_git), `IntegrationConfig`, `EnterpriseOrgConfig` (schema_version, agregados, `resolve_*_path()` con WorkspaceLayout).
- `config.py` — `discover_enterprise_config_path()`, `load_enterprise_config()`, `write_enterprise_config()`, `build_enterprise_org_config()`, `describe_enterprise_topology()`. **Soporta layout dual.**
- `retrieval_service.py` + `sources.py` — `EnterpriseRetrievalService.search(scope, top_k, ...)` construye `VaultSource[]` y `EpisodicSource[]` según scope; usa `MultiVaultReader` y `MultiEpisodicReader` para enriquecer hits con `origin_scope/project_id/vault/persist_dir`; aplica RRF cross-source con pesos de config.
- `knowledge_promotion.py` — `PromotionRepository` (JSONL append-only), `PromotionRulesEngine` (allowed doc_types, no `.cortex/*`), `KnowledgePromotionService` (discover candidates con fingerprint SHA256 del body normalizado, review, plan, apply: copia a enterprise_vault y mete frontmatter `promotion_status/origin_id/fingerprint/timestamp`).
- `reporting.py` — `MemoryReportPayload`, `PromotionReport`, `MemorySourceReport`, `build_memory_report(scope)`. Doctor enterprise se ejecuta si scope ∈ {enterprise, all}.
- `promotion_models.py` — modelos auxiliares de promoción.

### 5.13 `cortex/context_enricher/`
- `observer.py` — `ContextObserver`. `observe_from_git()`, `observe_from_pr()`, `observe_from_files()`. Extrae imports/functions/classes vía regex, frecuencia de identificadores, keywords del PR title/body, dominio detectado, search_queries (topic / file / keyword / pr_title).
- `domain_detector.py` — `DOMAIN_RULES` hardcoded (auth, database, api, security, payments, ui, testing, infrastructure, data, i18n, logging, configuration). Score = file_score×0.6 + keyword_score×0.4. Si <0.5, fallback embedding-based usando centroides pre-computados. **No extensible por config**, sería un dial obvio para mejora futura.
- `enricher.py` — `ContextEnricher.enrich(work, top_k)`. 6 fases: (1) estrategias paralelas → strategy_results; (2) dedup por source_id; (3) multi-match boost 1.5^(strategies-1); (4) co-occurrence boost (legacy + typed graph); (5) temporal decay (`MemoryDecay`, half_life_hours=168 default); (6) feedback loop (boost 0.15× si útil). Filtra por `min_score`, ordena, aplica budget (`max_items=8`, `max_chars=2000`).
- `async_enricher.py` — `AsyncContextEnricher.enrich_async()` con `ThreadPoolExecutor` (default 4 workers); fallback sync si no hay loop.
- `co_occurrence.py` — `TypedCooccurrenceGraph` con relación types: IMPORTED_BY (1.0), TESTED_BY (0.9), EXTENDS/IMPLEMENTS (0.8), USES (0.7), DEFINES (0.7), CONFIGURES (0.6), REFERENCES (0.5). `build_from_memories()` y `build_from_ast()` (Python AST + regex JS/TS).
- `memory_decay.py` — decaimiento temporal.
- `feedback_loop.py` — boost por feedback implícito/explícito.
- `presenter.py` — `to_markdown`, `to_compact`, `to_json`. (No HTML directo; el HTML lo arma WebGraph aparte.)
- `config.py` — `ContextEnricherConfig` Pydantic con thresholds, budget, scoring, strategies, decay, feedback.

### 5.14 `cortex/autopilot/`
- `service.py` — `AutopilotService`. Métodos: `start(StartRequest)`, `preflight(PreflightRequest)`, `checkpoint(CheckpointRequest)`, `finish(FinishRequest)`, `status(session_id=None)`, `build_context(session_id)`, `review_delegation(DelegationResult)`. **De `from_project_root(...)` usa `WorkspaceLayout.discover()`.**
- `models.py` — `AutopilotSessionState` (session_id, project_root, workspace_root, status: started/preflight_done/implementation_seen/documented/finished/failed, mode, detected_task_type, complexity, spec_path, **session_note_path**, checkpoints, budget, warnings), `AutopilotEvent`, `SessionDraft` (title, body, confidence: high/medium/auto-draft, warnings, source_events).
- `state_store.py` — persistencia JSON + JSONL en `<workspace>/run/autopilot/sessions/<sid>.json` y `events/<sid>.jsonl`.
- `lifecycle.py` — DTOs request/result.
- `detectors/` — AmbiguousRequest, QuestionOnly, DocsOnly, SecuritySensitive, LargeRefactor, CodeChange, Noop. Retornan `DetectionResult(task_type, suggested_complexity)`.
- `policies/default.py` — BudgetPolicy, SpecRequiredPolicy, DocumentationRequiredPolicy, HumanApprovalPolicy. Retornan `PolicyDecision(allowed, action: proceed/warn/degrade/block, degrade_to, reason)`.
- `policies/base.py` — `evaluate_policies`, `most_restrictive`.
- `session_builder.py` — `SessionBuilder.build(state)` selecciona renderer + self-review (placeholder scan, file consistency, evidence verification). Degrada confidence a "auto-draft" si encuentra problemas.
- `renderers/` — Minimal, DocsOnly, Implementation, FallbackDraft.
- `adapters/`, `hooks/`, `mcp_tools.py`, `cli.py`, `doctor.py`, `packaging.py`, `pi/`, `skills/`, `registry.py`, `reporting.py`, `context.py`, `context_budget.py`, `budget_profiles.py`, `delegation.py`.

### 5.15 `cortex/mcp/server.py` (908 líneas)
**Servidor MCP** que expone:
- Memory tools: `cortex_search`, `cortex_search_vector`, `cortex_context`, `cortex_sync_vault`.
- Workflow tools: `cortex_sync_ticket`, `cortex_create_spec`, `cortex_save_session`.
- Work items: `cortex_import_hu`, `cortex_get_hu`.
- Autopilot: `cortex_autopilot_start/preflight/checkpoint/finish/status`.
- Delegation (experimental): `cortex_delegate_task`, `cortex_delegate_batch`, `cortex_get_task_result`.

**Guard de gobernanza (verificado):** mantiene `self._called_tools: set[str]` (server.py:43). En `handle_call_tool`, cuando llega `cortex_create_spec`, valida en server.py:410: si `"cortex_sync_ticket" not in self._called_tools`, **bloquea con error y retorna** ("❌ VIOLACIÓN DE GOBERNANZA: cortex_create_spec fue llamado sin ejecutar primero cortex_sync_ticket"). Es bloqueo total, no advertencia.

### 5.16 `cortex/cli/main.py` (1738 líneas)
Typer monolítico con tres sub-apps: `webgraph`, `autopilot`, `pr-context`, `hu`. Comandos top-level (verificado por grep `@app.command`):
`init`, `setup`, `context`, `save-session`, `create-spec`, `verify-docs`, `validate-docs`, `index-docs`, `doctor`, `org-config`, `promote-knowledge`, `review-knowledge`, `sync-enterprise-vault`, `agent-guidelines`, `install-skills`, `remember`, `search`, `sync-vault`, `forget`, `stats`, `inject`, `sync-ide`, `mcp-server`, `mcp-serve` (hidden alias), `memory-report`, `hu` sub-app, `pr-context` sub-app.

**`cortex remember`** acepta `--branch`, `--commit`, `--repo` (líneas 1064-1066). Esto **invalida el release-2 weakness #5** (que decía que templates generaban flags no soportados).

`_DEFAULT_CONFIG` está hardcodeado al estilo legacy (`.memory/chroma`). Eso es lo que `cortex init` escribiría si lo usa directamente.

### 5.17 `cortex/ide/`
- `base.py` — `IDEAdapter` protocol (name, display_name, get_config_paths, inject_profiles, inject_mcp, validate).
- `registry.py` — discovery automático.
- `adapters/` — cursor, vscode, claude_code, claude_desktop, opencode, zed, windsurf, pi. Experimental: antigravity, hermes.
- `prompts.py` — prompts compartidos.

### 5.18 `cortex/setup/`
- `orchestrator.py` — `SetupOrchestrator` con `SetupMode` enum: AGENT, PIPELINE, FULL, WEBGRAPH, ENTERPRISE. Cada modo usa `WorkspaceLayout` para escribir.
- `templates.py` (1205 líneas) — `render_config_yaml` (con `embedding_backend: onnx`, **verificado en línea 60**: invalida weakness #4), `render_org_yaml`, `render_ci_pull_request` (invoca `cortex doctor`, `cortex pr-context capture/store/search/generate`, `cortex verify-docs`, `cortex index-docs`, `cortex validate-docs`, `cortex sync-vault`), `render_ci_enterprise_governance` (invoca `cortex doctor --scope enterprise`, `cortex promote-knowledge --dry-run`, `cortex sync-enterprise-vault`), `render_*_md` (vault docs), `render_devsecdocops_sh`.
- `cold_start.py` — preseed vault, git history mining (`grep "decision\|ADR"`), README fallback.
- `enterprise_wizard.py` — TUI preset + override.
- `enterprise_presets.py` — `resolve_enterprise_setup(preset, overrides)` con deep_merge.
- `cortex_workspace.py` — utilidades sobre `workspace.yaml`.
- `detector.py` — `ProjectDetector` detecta stack (Python, JS, Go, Rust), CI, env vars de LLM.

### 5.19 `cortex/pipeline/`
- `orchestrator.py` — `PipelineOrchestrator` ejecuta stages en orden, abort early si bloqueante, agrega outputs a `ctx.stage_outputs`.
- `domain/context.py` — `PipelineContext.from_pr_context(pr_ctx)`.
- `stages/` — `lint.py` (ruff), `test.py` (pytest), `security.py` (gitleaks, safety), `documentation.py` (verify/generate docs).
- `runners/` — adaptador GitHub Actions.
Cada stage retorna `StageResult(status, passed, artifacts, message)`.

### 5.20 `cortex/webgraph/`
- `server.py` — Flask `create_app()`. **Verifica header `X-Cortex-WebGraph: 1` en todas las rutas `/api/*` y `abort(403)` si falta.** Endpoints: GET `/api/snapshot`, GET `/api/node/<id>`, GET `/api/subgraph`, POST `/api/open` (resuelve + OS opener).
- `service.py` — `WebGraphService` con cache fingerprint-based. Usa `WorkspaceLayout`.
- `openers.py` — `resolve_safe_vault_path` valida que el resolved path no escape del vault root (path traversal guard).
- `graph_builder.py`, `relation_builder.py`, `semantic_source.py`, `episodic_source.py`, `federation.py` (multi-proyecto via `workspace.yaml`), `cache.py`, `contracts.py`, `cli.py`, `setup.py`, `config.py`.
- `static/`, `templates/` — UI estática.

### 5.21 `cortex/tutor/`
Tutor TUI interactivo. `engine.py` (TutorTopic protocol con `render(console)`), `hint.py`, `topics/`. Maneja UTF-8 en Windows con `_safe_console()`.

### 5.22 `cortex/hooks/agent_hooks.py`
- `CortexHook` decorator (`@hook.capture()`) con `functools.wraps` + `inspect.signature`.
- `CortexLangChainCallback` (BaseCallbackHandler de LangChain).
- `CortexCrewAIHook` (monkey-patch style).

### 5.23 `cortex/skills/`
Skills bundled para Obsidian (defuddle, json-canvas, obsidian-bases, obsidian-cli, obsidian-markdown). `install_skills()` los copia desde `importlib.resources` a `layout.skills_dir`.

### 5.24 `cortex-pi/`
Entorno paralelo de Pi Coding Agent. Tiene `.pi/agents/` (cortex-code-explorer, cortex-code-implementer, cortex-documenter, cortex-security-auditor, cortex-test-verifier, cortex-sync, plus agent-chain.yaml, teams.yaml), `.pi/skills/`, `mcp.json`, `settings.json`, `system.md`, `damage-control-rules.yaml`. **Tiene Justfile** para automatización (`just cortex`, `just sdd`, `just hotfix`, `just audit`).

**Atención:** los agentes `cortex-code-explorer`, `cortex-code-implementer`, `cortex-documenter`, `cortex-sync` están duplicados entre `.cortex/subagents/` y `cortex-pi/.pi/agents/`. Confirmar si son idénticos o divergentes antes de editar uno.

---

## 6. Flujos Principales

### 6.1 Setup (`cortex setup ...`)
1. `WorkspaceLayout.discover()` → decide new vs legacy.
2. `SetupOrchestrator` despacha por modo:
   - **agent:** crea dirs + config.yaml + org.yaml (opt) + vault skeleton + AGENT.md/system-prompt.md + skills + memory dir.
   - **pipeline:** + workflows + devsecdocops.sh.
   - **full:** agent + pipeline + IDE profiles.
   - **webgraph:** solo `.cortex/webgraph/`.
   - **enterprise:** preset/wizard + force-write org.yaml.
3. Templates resuelven comandos según stack detectado (`test_cmd`, `lint_cmd`, etc.).

### 6.2 Retrieval
1. `AgentMemory.retrieve(query, scope=...)`.
2. scope=local → `HybridSearch.search(query, top_k, use_embeddings)`:
   - QueryIntentDetector clasifica intent (lexicon).
   - Over-fetch k*3 episodic + k*3 semantic.
   - RRF cross-source con pesos adaptativos.
   - Devuelve unified_hits ordenado.
3. scope ∈ {enterprise, all} → `EnterpriseRetrievalService.search(...)`:
   - Construye sources según scope desde org.yaml.
   - `MultiVaultReader` + `MultiEpisodicReader` enriquecen hits con origin.
   - RRF cross-source con pesos local/enterprise.
4. Si `namespace_mode=branch`, filtra hits con branch != current.

### 6.3 Context Enrichment
1. `AgentMemory.enrich(changed_files, keywords, pr_title, pr_body, pr_labels)`.
2. `ContextObserver` construye `WorkContext` (imports, funcs, classes, dominio, search_queries).
3. `ContextEnricher.enrich(work)`:
   - Lanza estrategias (topic, files, keywords, pr_title, entity_search) — async si `AsyncContextEnricher`.
   - Dedup → multi-match boost → co-occurrence (typed graph) → temporal decay → feedback loop.
   - Filtra min_score, ordena, aplica budget.
4. Devuelve `EnrichedContext`. Presenter formatea (`to_prompt_format`, `to_markdown`, `to_json`).

### 6.4 MCP / IDE
1. Editor llama `cortex mcp-server --project-root <dir>` (típico) o el IDE lo lanza via stdio.
2. MCP tools delegan a `AgentMemory` y sus servicios.
3. Guard ordering: `cortex_sync_ticket` debe llamarse antes que `cortex_create_spec`. Si no, el server **bloquea** con mensaje de "VIOLACIÓN DE GOBERNANZA".
4. `cortex inject --ide <name>` o `cortex sync-ide` despachan a `IDEAdapter` que escribe configs MCP + skills/profiles dentro del IDE.

### 6.5 Spec / Session Workflow
1. **Spec:** `cortex create-spec` → `SpecService.create()` escribe `vault/specs/<slug>.md`, registra memoria `memory_type=spec`.
2. **Session:** `cortex save-session` → `SessionService.create()` escribe `vault/sessions/<date>-<slug>.md`, registra memoria `memory_type=session`.

### 6.6 PR Documentation (DevSecDocOps)
1. CI: `cortex pr-context capture --title ... --body ... --branch ... --commit ... --pr-number ... --output .pr-context.json` (verificado en workflow real).
2. `cortex pr-context search --context-file .pr-context.json --output .past-context.json`.
3. `cortex verify-docs --vault vault --output .doc-status.json --quiet` → set `has_agent_docs`.
4. Si NO hay docs del agente: `cortex pr-context generate --context-file .pr-context.json --vault vault` (fallback determinístico).
5. Si SÍ hay docs: `cortex index-docs --vault vault`.
6. `cortex validate-docs --vault vault --output .doc-validation.json`.
7. `cortex pr-context store --context-file .pr-context.json --lint-result ... --audit-result ... --test-result ...`.
8. `cortex sync-vault`.

### 6.7 Enterprise Promotion
1. `cortex promote-knowledge --dry-run` → `KnowledgePromotionService.discover_candidates()` escanea `local_vault/*.md`, calcula fingerprint SHA256 del body normalizado, compara con `PromotionRepository.load_latest_by_origin_id()`.
2. `cortex review-knowledge --approve|--reject <id>` → graba `PromotionRecord` event.
3. `cortex promote-knowledge --apply` → copia archivos al enterprise vault, upserta frontmatter `promotion_status/origin_id/fingerprint/timestamp`.
4. CI gobernanza: `ci-enterprise-governance.yml` ejecuta `cortex doctor --scope enterprise`, `cortex promote-knowledge --dry-run --json`, `cortex sync-enterprise-vault --json --output ...`. El comportamiento (continuar / fallar) depende de `governance.ci_profile`: observability (todo continue-on-error), advisory (sync continúa, otros no), enforced (todo falla si hay errors). En enforced mode, **si hay candidatos planificados o errors en validación, el job aborta con SystemExit**.

### 6.8 Autopilot Lifecycle
1. `cortex autopilot start --mode observe|assist|autopilot --request "..." --title-hint ...` → `AutopilotService.start()` crea state, guarda en `<workspace>/run/autopilot/sessions/<sid>.json`.
2. `cortex autopilot preflight --session-id ... --request ... --file ...` → detectors clasifican, policies evalúan, modo puede degradar.
3. `cortex autopilot checkpoint --session-id ... --summary ... --file ... --verified` → registra `AutopilotCheckpoint`.
4. `cortex autopilot finish --session-id ... --auto` → **(ver hallazgo crítico abajo en sección 11)**.
5. `cortex autopilot status [--session-id ...]`, `doctor`, `report --last N`, `cleanup --older-than DAYS`.
6. `cortex autopilot install --ide <name>` instala hooks IDE-side.

### 6.9 WebGraph
1. `cortex webgraph setup` (provisión).
2. `cortex webgraph serve` levanta Flask. Front-end consume `/api/*` con header `X-Cortex-WebGraph: 1`.
3. `WebGraphService.build_snapshot(mode)` cachea por fingerprint, retorna nodos + arcos (semantic links, co-occurrence, episodic→semantic, federation).
4. `/api/subgraph` permite BFS con depth + edge_types filter.
5. `cortex webgraph export` snapshot a JSON.

### 6.10 Pipeline CI
Cada workflow en `.github/workflows/` (5 actuales):
- `ci-pull-request.yml`: observability mode, todos continue-on-error. Cachea `.memory/chroma` (**hardcoded legacy path**).
- `ci-enterprise-governance.yml`: lee `.cortex/org.yaml`, ejecuta doctor/promote/sync con `continue-on-error` dinámico según ci_profile. Sube artefactos. En enforced, falla si hay candidatos planificados o errors.
- `ci-e2e.yml`, `ci-release.yml`, `ci-security.yml`: leídos por inventario, no verificados en detalle aquí.

---

## 7. Modelos de Datos y Contratos Importantes

| Modelo | Archivo | Para qué sirve |
|---|---|---|
| `MemoryEntry` | models.py | Unidad atómica de memoria episódica |
| `SemanticDocument` | models.py | Documento markdown del vault |
| `RetrievalResult` | models.py | Resultado de hybrid search, expone `to_prompt()` |
| `UnifiedHit` | models.py | Hit fusionado RRF cross-source |
| `PRContext` | models.py | Contrato PR DevSecDocOps |
| `GeneratedDoc` | models.py | Doc generado por fallback |
| `WorkContext` / `EnrichedItem` / `EnrichedContext` | models.py | Contratos de context_enricher |
| `CortexConfig` (+sub) | core.py | Schema Pydantic del config.yaml |
| `EnterpriseOrgConfig` (+sub) | enterprise/models.py | Schema Pydantic de org.yaml |
| `AutopilotSessionState`, `AutopilotEvent`, `SessionDraft` | autopilot/models.py | Estado y eventos del modo autonomo |
| `WorkspaceLayout` | workspace/layout.py | Contrato de paths |
| `PromotionRecord` | enterprise/promotion_models.py | Append-only JSONL del pipeline de promoción |

Reglas duras:
- Cualquier path que se escriba en el filesystem por servicios o setup debe pasar por `WorkspaceLayout` o `cortex/security/paths.py`.
- Cualquier change al schema de `org.yaml` o `config.yaml` debe pasar por su Pydantic; nunca leer YAML directo en lógica de negocio.
- Cualquier MCP tool nueva debe registrarse en `cortex/mcp/server.py` y considerar tracking de orden si introduce flujo obligatorio.

---

## 8. Configuración y Archivos de Estado

- `config.yaml` — config principal. Schema validado por `CortexConfig`. En este repo: legacy paths.
- `.cortex/workspace.yaml` — layout_version (v2 indica new layout).
- `.cortex/org.yaml` — config enterprise (organization, memory, promotion, governance, integration).
- `.cortex_index.json` (dentro del vault) — índice BM25 metadata del semántico.
- `.memory/` o `.cortex/memory/` — ChromaDB persistente (sqlite + binarios HNSW). **Ignorado en git.**
- `vault/sessions/` — session notes locales. **Ignorado en git** (la promotion al enterprise sí queda versionada).
- `vault-enterprise/promotion/records.jsonl` (new) o `vault-enterprise/.cortex/promotion/records.jsonl` (legacy) — append-only de eventos de promoción.
- `<workspace>/run/autopilot/sessions/<sid>.json` — estado autopilot.
- `<workspace>/run/autopilot/events/<sid>.jsonl` — eventos autopilot.
- `.cortex/logs/` — logs MCP. **Ignorado en git.**
- `.cortex/webgraph/cache/` — cache de snapshots.

Secrets esperados (env vars):
- `JIRA_EMAIL`, `JIRA_API_TOKEN` para work items.
- `OPENAI_API_KEY` para `embedding_backend=openai` o LLM provider OpenAI.
- `ANTHROPIC_API_KEY`, host de Ollama para sus providers.

---

## 9. Tests: Qué Cubren y Gaps

**Estructura (verificada):**
- `tests/unit/` con sub-carpetas: `autopilot/`, `cli/`, `context_enricher/`, `embedders/`, `enterprise/`, `episodic/`, `pr/`, `retrieval/`, `security/`, `semantic/`, `webgraph/`, `workspace/`, + archivos sueltos (`test_doc_validator.py`, `test_doc_verifier.py`, `test_doctor_enterprise_governance.py`, `test_documentation.py`, `test_ide_adapters.py`, `test_ide_module.py`, `test_mcp_server.py`, `test_runtime_context.py`).
- `tests/integration/` con `enterprise/`, `mcp/`, `setup/`.
- `tests/e2e/` con `scenarios/` (setup_basic, setup_full, memory_lifecycle, pr_devsecdocops, enterprise_setup, autopilot_*), `fixtures/`, `helpers.py`, `test_artefact_integrity.py`.
- `tests/smoke/` — placeholder con Dockerfile/entrypoint, sin tests activos.
- Total ~739 funciones `def test_*` en ~93 archivos según el inventario.

**Contratos críticos cubiertos:**
- RRF math + adaptive weights (tests/unit/retrieval/test_rrf_properties.py, Hypothesis).
- Embedder protocol contract (tests/unit/embedders/test_embedder_contract.py).
- WorkspaceLayout discovery dual (tests/unit/workspace/test_layout.py).
- Autopilot lifecycle, finish safety, budget (tests/unit/autopilot/* + tests/e2e/scenarios/test_autopilot_*).
- Enterprise promotion pipeline, schema, multi-scope retrieval (tests/unit/enterprise/* + integration/enterprise/).
- Doctor enterprise governance (test_doctor_enterprise_governance.py).
- Path safety (tests/unit/security/test_paths.py).
- WebGraph server/openers/federation (tests/unit/webgraph/).

**Gaps reales (inferidos):**
- MCP server: `test_mcp_server.py` existe pero según `release-2-known-weaknesses` históricamente fallaba por `to_prompt`/`to_prompt_format`. **Verifiqué que ese problema ya está resuelto** (`mcp/server.py:651` usa `related.to_prompt()` que es válido para `RetrievalResult`, y `:654` usa `enriched.to_prompt_format()` válido para `EnrichedContext`). Aún así, no tengo evidencia de que la suite MCP cubra el guard ordering (`cortex_create_spec` sin `cortex_sync_ticket` debería ser un test obvio).
- `cortex/ide/installer.py` y adapters: hay `test_ide_adapters.py` y `test_ide_module.py` pero no sé qué cobertura tienen end-to-end.
- `cortex/hooks/agent_hooks.py` (LangChain/CrewAI): incierto.
- `cortex/setup/cold_start.py`: bajo coverage según `release-2-known-weaknesses`.
- `cortex/cli/main.py` (1738 líneas, 30+ comandos): `tests/unit/cli/test_main.py` existe pero la centralidad del CLI sugiere que la cobertura puede no ser exhaustiva.
- Suite `tests/smoke/` está vacía.

---

## 10. Documentación: Vigente / Obsoleta / Parcialmente Resuelta

**Vigente y autoritativa:**
- `README.md` — manifiesto, CLI reference, instalación. Está actualizado al modelo new-layout (aunque el repo es legacy).
- `CONTRIBUTING.md` — estándares, áreas de contribución, roadmap Enterprise.
- `CHANGELOG.md` — sección "Unreleased" describe normalización 0.3.0 Alpha; secciones 2.0/2.4/2.5 son narrativa histórica.
- `.cortex/AGENT.md` y `.cortex/system-prompt.md` — reglas de gobernanza (tripartito + tools aislados).
- `docs/enterprise/MANIFIESTO-CORTEX-ENTERPRISE.md` — descrito en README como exhaustivo.
- `docs/autopilot/contracts.md` — contratos v1.0 estables.
- `docs/refact/REFAC-WORKSPACE-STRUCT.md` — propuesta lista para implementar de consolidación en `.cortex/`. **Aún no aplicada en este repo.**

**Parcialmente resuelta / Roadmap:**
- `docs/enterprise/PLAN-EPIC-2..7` y `AVANCE-EPIC-*` — describen ondas en progreso.
- `docs/refact/REFAC-WEBGRAPH.md` — propuesta de fases; algunas piezas (X-Cortex-WebGraph header, paths seguros) ya están en código.
- `docs/BusinessSignal/` — **propuesta + plan faseado**, no implementación. No hay módulo `cortex/business_signal/` ni similar.
- `docs/agents/` (untracked) — `MEJORA-TRIPARTITO.md` propone 5+ mejoras concretas para cortex-documenter (Signal>Noise, ADR 3 criterios, CONTEXT.md como tercera capa, verification gate, handoff mode, progressive disclosure, lexical boost RRF, contradiction detection). `ANALISIS-MEJORA-TRIPARTITO.md` critica/refina la propuesta. No están aplicadas. **Importante: leer y considerar antes de tocar el documenter.**

**Posiblemente obsoleta:**
- `vault/architecture/release-2-known-weaknesses.md` — 7 hallazgos. **Reverifiqué cada uno contra el código actual:**

| # | Hallazgo histórico | Estado real verificado |
|---|---|---|
| 1 | Entity search no persiste round-trip | **Probablemente activo**: episodic/memory_store.py serializa entidades pero no comprobé deserialización en detalle. Pendiente test round-trip. |
| 2 | Co-occurrence/typed-graph se deshabilita silenciosamente (empty-query transport) | **Probablemente activo**: el typed graph se construye desde memorias listadas; si el path "list all" usa search con query vacío, puede fallar silenciosamente. Pendiente verificación. |
| 3 | MCP `cortex_context()` llama `.to_prompt()` inexistente | **RESUELTO**: server.py:651 usa `related.to_prompt()` que sí existe en `RetrievalResult` (models.py:132). server.py:654 usa `enriched.to_prompt_format()` que sí existe en `EnrichedContext` (models.py:320). budget_profiles.py:51-63 tiene fallback defensivo. |
| 4 | Setup defaults `embedding_backend: local` vs ONNX-first | **RESUELTO**: templates.py:60 emite `embedding_backend: onnx`. main.py:78 `_DEFAULT_CONFIG` también `onnx`. |
| 5 | Templates generan flags `--branch`/`--commit` no soportados | **RESUELTO**: `cortex remember` en main.py:1064-1066 acepta `--branch`, `--commit`, `--repo`. Workflow real usa `cortex pr-context capture --branch ... --commit ...` que también está soportado en su sub-app. |
| 6 | `cortex context --output` siempre escribe markdown, ignora --format json | **Estado incierto**: en main.py:712-714 el output a archivo siempre llama `to_prompt_format()`. Si el comando expone `--format json`, esto sería bug vigente. Necesito leer la firma completa antes de cambiar. |
| 7 | Doc verification con clasificación inconsistente para vault files | **Probablemente activo**: no verifiqué doc_verifier.py al detalle. Tests de doc_verifier existen, podrían no cubrir el caso. |

**Conclusión sobre `release-2-known-weaknesses.md`:** 3 de 7 ya resueltos (3, 4, 5). 4 vigentes o inciertos (1, 2, 6, 7). El doc debería marcarse como "parcialmente resuelto" — pero NO lo edito sin instrucción explícita.

---

## 11. Riesgos Técnicos, Contradicciones y Deuda

### 11.1 ~~Hallazgo crítico~~ — `cortex autopilot finish --auto` NO escribe la session note **(RESUELTO 2026-05-13)**

**Estado:** Resuelto. Contrato actual: `status == "documented"` ⇒ archivo existe en disco.

**Lo que cambió:**
- Nuevo módulo `cortex/autopilot/session_writer.py`:
  - `SessionWriter` Protocol (`write(state, draft) -> Path`).
  - `VaultSessionWriter` (default) escribe a `<vault>/sessions/<YYYY-MM-DD>_<session_id>_<slug>.md` con frontmatter + draft body + sección Warnings.
  - Paths resueltos vía `cortex.security.paths.resolve_safe` + `validate_under_root` (path-traversal seguro).
- `cortex/autopilot/service.py`:
  - Constructor recibe `session_writer: SessionWriter | None = None`.
  - `from_project_root(project_root)` cablea `VaultSessionWriter(layout.vault_path)` por default — todas las invocaciones reales (CLI, MCP server, hooks) traen writer automáticamente.
  - Nuevo helper privado `_persist_draft(state, draft)` aísla la lógica de persistencia.
  - `finish()`: si hay writer y la persistencia funciona → `status = "documented"`, `saved = True`, `session_note_path` apunta al archivo real. Si no hay writer o falla la escritura → `status = "finished"`, `saved = False`, warning agregado al state. **Invariante nuevo:** "documented" implica archivo en disco.
  - Evento `finish` ahora incluye `session_note_path` en el payload para telemetría.
- Tests:
  - `tests/unit/autopilot/test_session_writer.py` — 12 tests del writer (frontmatter, tags, slug, escaping YAML, collisions, path safety).
  - `tests/unit/autopilot/test_service.py` — fixture default ahora trae writer real; nuevos tests `test_auto_finish_persists_to_disk`, `test_finish_auto_no_writer_does_not_claim_documented`, `test_event_records_session_note_path`.
  - `tests/e2e/scenarios/test_autopilot_finish.py` — nuevo `TestFinishPersistsToDisk.test_session_note_file_exists_after_finish_auto` valida flow CLI completo.
  - `tests/e2e/scenarios/test_autopilot_basic.py::TestFastCode::test_fast_track_draft_on_finish` — actualizado: ahora afirma que el archivo SÍ existe (antes verificaba la presencia del bug).
  - `tests/unit/autopilot/test_mcp_tools.py` — fixture actualizado a writer real, refleja wiring de producción.

**Resultado de regression:** `tests/unit/` + `tests/integration/` = **701 passed, 0 failed, 6 skipped**. Suite completa de autopilot (`tests/unit/autopilot/` + `test_autopilot_basic.py` + `test_autopilot_budget.py` + `test_autopilot_finish.py`) = 348 passed.

**Indexing mandatorio (2026-05-13 — fix follow-up):**
- Nuevo decorator `IndexingSessionWriter` (en `cortex/autopilot/session_writer.py`) envuelve cualquier `SessionWriter` y agrega indexing **transaccional**: tras persistir, hace `semantic.index_file(rel)` + `episodic.add(...)`. Si cualquiera de los dos pasos falla, **rollback**: borra el archivo recién creado y propaga la excepción. No quedan archivos huérfanos.
- `AutopilotService.from_project_root()` ahora cablea `IndexingSessionWriter` por default: construye `AgentMemory` desde `layout.config_path` y le pasa `semantic` + `episodic` al writer. Si la construcción de AgentMemory falla (workspace sin setup), cae a `VaultSessionWriter` solo y loguea warning explícito.
- Nuevo check `_check_session_indexing` en `cortex autopilot doctor`: verifica que el writer del service sea `IndexingSessionWriter`. Si no, reporta falla con remediación (`cortex setup agent`).
- Cobertura: 6 tests nuevos del decorator (`test_session_writer.py` ahora 18 verdes) incluyen rollback semantic-fail, rollback episodic-fail, propagación de tags `auto-draft`, metadata correcta. Nuevo E2E `TestFinishIndexesAutomatically.test_finished_note_appears_in_search` valida flow completo: tras `finish --auto`, una `AgentMemory` fresca encuentra la nota en `retrieve()` tanto en semantic_hits como en episodic_hits.
- `PRService.write_pr_docs` también indexa cada doc generado (selective `index_file` por archivo escrito). `core.py` ahora le pasa `semantic=self.semantic` al construir `PRService`.

**Contrato vigente:** "archivo en disco ⇒ archivo indexado" (transaccional). `cortex search` encuentra inmediatamente cualquier nota escrita por SessionService, SpecService, PRService.write_pr_docs, o `autopilot finish --auto`. No hace falta `cortex sync-vault` manual.

**Cierre del módulo Autopilot (2026-05-13):** Tras los fixes de persistencia + indexing mandatorio, se cerró el módulo completo eliminando la deuda derivada:
- `tests/e2e/test_artefact_integrity.py` `MCP_TO_CLI` ahora cubre las 8 tools que faltaban: 5 autopilot lifecycle (`cortex_autopilot_start/preflight/checkpoint/finish/status`) mapeadas a su sub-CLI `cortex autopilot <sub>`, y 3 delegation experimentales (`cortex_delegate_task/batch`, `cortex_get_task_result`) explícitamente marcadas como `None` (sin CLI por diseño).
- `tests/unit/autopilot/test_doctor.py` actualizado para incluir el check `session_indexing` en `test_run_diagnosis_basic`. Dos tests nuevos validan el comportamiento degraded (sin config.yaml) vs. full workspace.
- `cortex/autopilot/mcp_tools.py::finish()` ahora incluye `Note: <path>` en la respuesta MCP cuando `saved=True`, exponiendo el path real persistido + indexado para que el IDE consumidor lo pueda abrir directamente.
- Bonus cierre cross-módulo: `tests/e2e/scenarios/test_enterprise_setup.py::test_enterprise_setup_multi_project_team` arreglado — leía `org_data["profile"]` cuando el schema (cortex/enterprise/models.py) ubica `profile` dentro de `organization`. Cambiado a `org_data["organization"]["profile"]`.

**Suite final con todo aplicado:** 789 passed, 6 skipped, 0 failed (unit + integration + e2e). Cero deuda residual en el módulo Autopilot.

### 11.2 Embedder paralelo no usado

`cortex/embedders/` (factory + Protocol) existe pero el runtime principal sigue usando `cortex/episodic/embedder.py` (Embedder viejo). Coexistencia intencional pero confusa. Si alguien refactoriza pensando que el factory ya está en uso, va a romper el contrato de vector space común episodic+semantic. **Antes de tocar embeddings, leer ambos archivos y verificar quién importa qué.**

### 11.3 Workflows hardcodean rutas legacy

`.github/workflows/ci-pull-request.yml:70,137` cachea `path: .memory/chroma` directamente. En new layout debería ser `.cortex/memory`. Si el repo migra a v2 antes que los workflows, el cache deja de funcionar (no es fatal — cache miss — pero ya no acelera). Templates probablemente generan el path correcto según layout; el workflow real de este repo está congelado en legacy.

### 11.4 Carga de config antes de discovery

`AgentMemory.__init__` carga `config.yaml` desde el path explícito antes de descubrir layout (core.py:138-154). Esto significa: si corrés `cortex search` en new layout sin `--project-root` y sin estar parado dentro de `.cortex/`, falla con FileNotFoundError. El CLI puede compensar resolviendo paths antes de instanciar `AgentMemory`. Verificar antes de afirmar que es problema o no.

### 11.5 `docs/agents/` no trackeado en Git

El usuario tiene trabajo no commiteado en `docs/agents/` (5 PNGs, MEJORA-TRIPARTITO.md, ANALISIS-MEJORA-TRIPARTITO.md). Es contenido sustantivo (propuesta crítica para cortex-documenter). **No pisarlo. Si voy a tocar el documenter, primero releer ambos .md.**

### 11.6 Versionado inconsistente en narrativa

pyproject = 0.3.0 Alpha. CHANGELOG habla de v2.0/2.4/2.5. README usa "Release 2". Eso ya fue normalizado en "Unreleased" del CHANGELOG, pero docs viejos pueden seguir mencionando 2.x. **No es un bug, pero genera confusión.**

### 11.7 Domain detection no extensible

`DOMAIN_RULES` en `context_enricher/domain_detector.py` es un dict hardcoded de 12 dominios. Para proyectos no estándar (fintech, healthcare, agro) el dominio cae siempre en el embedding fallback. Mejora obvia: exponer en config.yaml `domain_rules:` extensibles.

### 11.8 CLI monolítico

`cortex/cli/main.py` tiene 1738 líneas con 30+ comandos. Sub-apps existen (webgraph, autopilot, pr-context, hu) pero muchos comandos top-level podrían splitearse. Es deuda, no urgencia.

### 11.9 Duplicación de agentes Cortex / cortex-pi

Agentes con el mismo nombre viven en `.cortex/subagents/` y `cortex-pi/.pi/agents/`. Antes de editar uno, verificar si son idénticos o si divergieron por target (Cortex MCP vs Pi runtime).

### 11.10 Suite smoke vacía

`tests/smoke/` tiene infraestructura (Dockerfile, entrypoint) pero no tests. Si el roadmap pide smoke nightly, está pendiente.

---

## 12. Reglas Prácticas para Desarrollar en Cortex sin Romper Arquitectura

1. **Todo path va por `WorkspaceLayout`.** No hardcodear `.memory/` o `vault/` en código nuevo. Si necesitás un path no expuesto, agregarlo como property a `WorkspaceLayout` y testearlo en `tests/unit/workspace/test_layout.py`.
2. **Todo write al filesystem pasa por `cortex/security/paths.py`.** Path traversal es real y crítico, sobre todo en WebGraph y MCP tools.
3. **`AgentMemory` es façade puro.** Lógica nueva → service nuevo en `cortex/services/`. Inyectar infraestructura en `__init__`.
4. **Validar configs con Pydantic.** Nunca leer YAML directo en lógica. Si añadís key nueva, extender el modelo.
5. **Episodic + Semantic comparten el mismo `Embedder`.** Si introducís otro backend, hacerlo a través del factory **y** convertir core.py al mismo factory simultáneamente. Cambios parciales rompen el vector space.
6. **RRF con `K=60` y over-fetch `k*3`.** No cambiar estas constantes sin tests de propiedades (Hypothesis ya cubre).
7. **MCP tool nueva → registrar en `cortex/mcp/server.py` + tests.** Si la tool introduce un orden requerido, sumarlo al guard `_called_tools`.
8. **Toda nueva session/spec/PR doc escribe via `SpecService`/`SessionService`/`PRService`**, no escribiendo `.md` manualmente.
9. **Toda persistencia enterprise pasa por `EnterpriseOrgConfig` y `KnowledgePromotionService`**, jamás escribir `vault-enterprise/` a mano.
10. **Pipeline stages implementan `PipelineStage` protocol** y leen su config desde `ctx.config["pipeline"][<name>]`. No hacer `subprocess.run` directo desde core/services.
11. **Templates y CLI deben estar alineados.** Si añadís un comando o flag, actualizar `cortex/setup/templates.py` si los workflows generados lo usan. Y al revés: si los workflows lo usan, el CLI lo debe soportar.
12. **WebGraph siempre valida `X-Cortex-WebGraph: 1`** y resuelve paths via `resolve_safe_vault_path()`. Endpoints nuevos respetan la misma convención.
13. **`docs/agents/` es WIP del usuario, intocable.** Leer para entender, no pisar.
14. **Convención de commits:** Conventional Commits (feat/fix/docs/test/refactor con scope). Lo dice CONTRIBUTING.md.
15. **Coverage target >85%.** Mantener.

---

## 13. Backlog Recomendado para el Próximo Trabajo

Ordenado por valor / riesgo / esfuerzo. Cada item incluye archivos a tocar.

### Tier S — bloqueos de la promesa Cortex
1. ~~**Hacer que `autopilot finish --auto` escriba la session note en disco.**~~ **DONE 2026-05-13.** Ver §11.1 para detalle del fix (`cortex/autopilot/session_writer.py`, contrato `documented ⇒ file on disk`, 348 tests autopilot pasan).
2. **Cubrir con test el guard MCP `cortex_create_spec` sin `cortex_sync_ticket`.**
   Archivos: `tests/unit/test_mcp_server.py`. Verificar que retorna error y no persiste spec.

### Tier A — correcciones del release-2-known-weaknesses aún vigentes
3. **Persistencia round-trip de entities en episodic.** Test que crea memoria con entities, recarga store, valida igualdad. Archivos: `cortex/episodic/memory_store.py`, `tests/unit/episodic/test_memory_store.py`.
4. **Co-occurrence / typed-graph: introducir un path "list all memories" explícito** en lugar del empty-query search. Archivos: `cortex/episodic/memory_store.py`, `cortex/context_enricher/co_occurrence.py`.
5. **`cortex context --output` honorar `--format json` también en file output.** Archivos: `cortex/cli/main.py:712-714`. Reusar el mismo formatter que stdout.
6. **Doc verifier: simplificar clasificación.** Archivos: `cortex/doc_verifier.py`, `tests/unit/test_doc_verifier.py`.

### Tier B — alineación new-layout
7. **Decidir cuándo migrar este repo a new layout** (`.cortex/config.yaml`, `.cortex/vault`, `.cortex/memory`). Actualizar workflows para cachear `.cortex/memory` en lugar de `.memory/chroma`. Archivos: `.github/workflows/ci-pull-request.yml`, `cortex/setup/templates.py` (verificar que ya emite la versión nueva).
8. **Resolver carga de config antes de discovery.** `AgentMemory.__init__` debería poder bootstrapear con `WorkspaceLayout.discover(cwd)` y leer `layout.config_path` si no se pasó `config_path` explícito. Archivos: `cortex/core.py`, `tests/unit/workspace/`.

### Tier B — mejoras de `cortex-documenter` (basadas en `docs/agents/MEJORA-TRIPARTITO.md`)
9. **Reescribir `.cortex/subagents/cortex-documenter.md`** con Signal>Noise, ADR 3-criterios, verification gate, handoff mode.
10. **Introducir `CONTEXT.md` como tercera capa léxica** y lexical boost en RRF. Diseño primero (spec en `docs/refact/`), implementación después.
11. **Modo handoff** con frontmatter `status: handoff` en session notes interrumpidas.

### Tier C — calidad de vida
12. **Splittear `cortex/cli/main.py` en sub-módulos** (`cli/memory.py`, `cli/enterprise.py`, `cli/setup_cli.py`, `cli/pr.py`).
13. **Domain detection extensible por config**. Permitir `domain_rules:` en config.yaml.
14. **Adoptar `EmbedderFactory` en runtime principal** (decisión Epic). Migrar `EpisodicMemoryStore` y `VaultReader` a recibir un `EmbedderProtocol`. Eliminar `cortex/episodic/embedder.py` o convertirlo en wrapper deprecated.
15. **Smoke suite real.** Llenar `tests/smoke/` con escenarios mínimos por componente.

### Tier C — BusinessSignal
16. **Decidir si BusinessSignal entra al backlog ejecutable o queda como propuesta.** Si entra, mover `docs/BusinessSignal/plan/` a Epic concreta y crear `cortex/business_signal/` esqueleto.

---

## 14. Cómo Retomar Rápido — Lista de Archivos por Tarea

Antes de cualquier tarea, **leer este documento primero**. Luego, según tarea:

**Si me piden tocar retrieval o RRF:**
- `cortex/retrieval/hybrid_search.py`, `cortex/retrieval/intent.py`.
- `cortex/models.py` (RetrievalResult, UnifiedHit).
- `tests/unit/retrieval/`.

**Si me piden tocar memoria episódica:**
- `cortex/episodic/memory_store.py`, `cortex/episodic/embedder.py`.
- `cortex/runtime_context.py` (namespace).
- `cortex/workspace/layout.py` (persist paths).
- `tests/unit/episodic/`.

**Si me piden tocar vault / semantic:**
- `cortex/semantic/vault_reader.py`, `cortex/semantic/markdown_parser.py`.
- `tests/unit/semantic/`.

**Si me piden tocar specs/sessions/PRs:**
- `cortex/services/spec_service.py | session_service.py | pr_service.py`.
- `cortex/pr_capture.py`, `cortex/doc_generator.py`, `cortex/doc_verifier.py`, `cortex/doc_validator.py`, `cortex/documentation.py`.
- `tests/unit/pr/`, `tests/unit/test_doc_*.py`.

**Si me piden tocar enterprise:**
- `cortex/enterprise/models.py | config.py | retrieval_service.py | sources.py | knowledge_promotion.py | reporting.py | promotion_models.py`.
- `cortex/setup/enterprise_presets.py | enterprise_wizard.py`.
- `tests/unit/enterprise/`, `tests/integration/enterprise/`.

**Si me piden tocar context enricher:**
- `cortex/context_enricher/observer.py | enricher.py | async_enricher.py | domain_detector.py | co_occurrence.py | memory_decay.py | feedback_loop.py | presenter.py | config.py`.
- `cortex/models.py` (WorkContext, EnrichedItem, EnrichedContext).
- `tests/unit/context_enricher/`.

**Si me piden tocar autopilot:**
- `cortex/autopilot/service.py` (mirar finish() en :278-282 primero).
- `cortex/autopilot/models.py | state_store.py | lifecycle.py | cli.py | mcp_tools.py | session_builder.py | renderers/ | detectors/ | policies/`.
- `docs/autopilot/contracts.md`.
- `tests/unit/autopilot/`, `tests/e2e/scenarios/test_autopilot_*.py`.

**Si me piden tocar MCP / IDE:**
- `cortex/mcp/server.py` (guard ordering en :410).
- `cortex/ide/base.py | registry.py | adapters/`.
- `tests/unit/test_mcp_server.py | test_ide_*.py`.

**Si me piden tocar CLI:**
- `cortex/cli/main.py` (mirar `@app.command()` y sub-apps al inicio).
- `tests/unit/cli/`.

**Si me piden tocar setup / templates / workflows:**
- `cortex/setup/orchestrator.py | templates.py | cold_start.py | detector.py | cortex_workspace.py`.
- `.github/workflows/*.yml`.
- `tests/integration/setup/`.

**Si me piden tocar WebGraph:**
- `cortex/webgraph/server.py | service.py | openers.py | graph_builder.py | relation_builder.py | semantic_source.py | episodic_source.py | federation.py | cache.py | cli.py | setup.py | config.py | contracts.py`.
- `docs/refact/REFAC-WEBGRAPH.md`.
- `tests/unit/webgraph/`.

**Si me piden tocar el documenter o el ciclo tripartito:**
- `.cortex/subagents/cortex-documenter.md`, `cortex-sync.md`, `cortex-SDDwork.md`.
- `docs/agents/MEJORA-TRIPARTITO.md`, `docs/agents/ANALISIS-MEJORA-TRIPARTITO.md` (untracked, no pisar).
- `cortex/services/session_service.py`, `cortex/autopilot/session_builder.py`.

**Si me piden tocar layout / workspace:**
- `cortex/workspace/layout.py`.
- `docs/refact/REFAC-WORKSPACE-STRUCT.md`.
- `tests/unit/workspace/test_layout.py`.

---

## Apéndice — qué no comprobé al 100%

- Tests reales que se rompen hoy (no corrí pytest). Inferí estado a partir de inventario y release-2-known-weaknesses.
- `cortex/cli/main.py` líneas 200-1700 no las leí enteras, solo grep de decoradores. Si una tarea pide modificar un comando, **leerlo entero antes**.
- Workflows `ci-e2e.yml`, `ci-release.yml`, `ci-security.yml` solo los inventaríé, no los leí.
- `cortex-pi/` solo lo inventaríé. Si la tarea toca Pi, abrir `AGENTS.md`, `system.md`, `mcp.json` y comparar con `.cortex/` antes.
- BusinessSignal solo lo identifiqué como propuesta. Si la tarea pide implementarlo, leer `docs/BusinessSignal/plan/fase-*` antes.
- Doc verifier weakness #7: no lo leí en detalle.
- `cortex context --output` weakness #6: no leí la firma del comando entero, solo el write_text.

---

Cuando retome trabajo de desarrollo, **mi paso 0 siempre debe ser**: releer la sección 11 (riesgos) y la sección 14 (archivos por tarea) de este documento. Si la tarea toca un módulo que dije "incierto" o "inferido", confirmarlo abriendo el archivo antes de proponer cambios.

Fin del save state.
