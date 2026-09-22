# cortex/core.py

## Qué tiene adentro

- **1065 líneas.** Fachada pública `AgentMemory` + modelos Pydantic de configuración.
- **Configuración:** `EpisodicConfig`, `SemanticConfig`, `EmbeddingLanguageConfig`, `EmbeddingConfig`, `RetrievalConfig`, `LLMConfig`, `JiraIntegrationConfig`, `IntegrationsConfig`, `DocumenterConfig`, `CortexConfig`.
- **Helpers de embeddings (Obra 04 Fase C):** `embedding_block_active`, `resolve_embedder`, `resolve_language_for_text`.
- **Fachada `AgentMemory`:** cablea infraestructura y delega lógica de negocio a servicios.

`CortexConfig` valida YAML. Si existe bloque top-level `embedding:` configurado **y** también `episodic.embedding_model/backend` distintos del default, emite `UserWarning` y gana el bloque nuevo.

`AgentMemory.__init__`:
1. Descubre `WorkspaceLayout` (CWD o padre del `config_path` explícito).
2. Exige que exista el YAML de config (si no: error pidiendo `cortex setup full --non-interactive`).
3. Carga YAML → `CortexConfig`.
4. Fija `workspace_root`, `repo_root`, `project_root` (= workspace_root, compat).
5. `load_enterprise_config` (opcional) + topología.
6. Resuelve directorio episódico con `resolve_episodic_persist_dir`.
7. Instancia `EpisodicMemoryStore`, `Summarizer`, `VaultReader`, `HybridSearch` con el par `(model, backend)` de `resolve_embedder`.
8. Instancia `SessionStorage` + `SessionService`.
9. Instancia `SpecService`, `NoteService`, `PRService`.
10. `WorkItemService` queda lazy (`_get_workitem_service`).

API pública observada: `remember`/`store_memory`, `retrieve` (scope local/enterprise/all + filtro de branch), `forget`, `stats`, `create_note`, `sync_vault`, `create_spec_note`, `save_session_note`, ciclo de sesión (`open_session`, `checkpoint_session`, `close_session`, `get_session`, `get_active_session`, `list_sessions`, tasks), PR (`store_pr_context`, `generate_pr_docs`, `write_pr_docs`, `get_pr_context`), work items (`import_work_item`, `get_work_item_note`, `list_work_item_notes`), `enrich` (observer + enricher).

## Para qué sirve

Única fachada estable para CLI, MCP y hooks: no reimplementa negocio; **inyecta** stores y **delega** a `SpecService` / `NoteService` / `PRService` / `SessionService` / `EnterpriseRetrievalService` / `ContextEnricher`.

## Relaciones

### Recibe de

- `WorkspaceLayout` (`cortex.workspace`) — paths.
- YAML de `config.yaml` / `.cortex/config.yaml`.
- `EpisodicMemoryStore`, `VaultReader`, `HybridSearch`.
- `SpecService`, `NoteService`, `PRService`, `SessionService`.
- `load_enterprise_config`, `EnterpriseRetrievalService`.
- `Summarizer`, `JiraProvider`/`WorkItemService` (si Jira enabled).
- `ContextObserver` + `ContextEnricher` (import diferido en `enrich`).
- `runtime_context` (slug, git branch/repo, persist dir).

### Envía a

- `cortex.__init__` (reexporta `AgentMemory`).
- `cortex.cli.common` (construye la fachada para comandos).
- `cortex.mcp.server` (el MCP instancia `AgentMemory`).
- `cortex.hooks.agent_hooks`.
- Vault (notas), Chroma (episódico), YAML de sesiones, enterprise vault si el scope no es local.

### Notas de implementación observadas en el código

- `retrieve`: si hay `enterprise_config` y no se pasa `scope`, usa `memory.retrieval_default_scope`. Scope ≠ local exige `org.yaml`.
- Filtro `namespace_mode == "branch"` recorta hits episódicos a la rama actual salvo `cross_branch=True`.
- `project_root` = `workspace_root` a propósito (legacy vs `.cortex/`).
- Embeddings: bloque `embedding:` inactivo → bit-idéntico a `episodic.embedding_*`.

---
Fuente: lectura de `cortex/core.py`. No se usó documentación previa.
