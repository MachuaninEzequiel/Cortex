# Contexto: superficies de uso (código)

## 1. CLI nativo (`cortex-cli`)

Dispatch en `rust/crates/cortex-cli/src/main.rs`:

Sin args: TUI Home (`cortex_tui::app::run`, snapshot si stdout no es TTY).

Tokens wireados: `doctor`, `agent-guidelines`, `install-skills`, `tutor`, `hint`, `org-config`, `promote-knowledge`, `review-knowledge`, `memory-report`, `webgraph`, `autopilot`, `search`, `context`, `stats`, `session`, `next`, `hu`, `ide`, `remember`, `forget`, `docs`, `ci`, `setup`, `pr-context`, `mcp-server`/`mcp-serve`, `reindex`, `init`, `finish`/`finish-session`.

`--version`/`-V`/`--cli-version` → `cortex-cli 0.1.0`.

## 2. CLI Python (`cortex.cli.main`)

Typer `app`. Sub-CLIs: webgraph, autopilot, session, ide, pr-context, hu, ci, docs, setup, review-knowledge. Comandos sueltos incluyen init, doctor, context, search, remember, forget, stats, org-config, promote-knowledge, memory-report, inject/sync-ide, mcp-server, finish, next, verify/validate/index-docs, agent-guidelines, install-skills.

`pyproject.toml` instala este como comando `cortex`.

## 3. MCP — 32 tools

`cortex-mcp/src/tools_catalog.rs`, `SERVER_VERSION = "2.2"`:

`cortex_ping`, `cortex_search_vector`, `cortex_search`, `cortex_context`, `cortex_sync_ticket`, `cortex_create_spec`, `cortex_emit_proposal`, `cortex_save_session`, `cortex_validate_handoff`, `cortex_verify_session_claims`, `cortex_import_hu`, `cortex_get_hu`, `cortex_sync_vault`, `cortex_autopilot_start`, `cortex_autopilot_preflight`, `cortex_autopilot_checkpoint`, `cortex_autopilot_finish`, `cortex_autopilot_status`, `cortex_session_open`, `cortex_session_checkpoint`, `cortex_session_close`, `cortex_session_status`, `cortex_finish_session`, `cortex_documenter_briefing`, `cortex_close_session`, `cortex_session_list`, `cortex_self_review_note`, `cortex_write_doc`, `cortex_session_task_list`, `cortex_session_task_update`, `cortex_review_checkpoint`.

Servidor: `rmcp` stdio (`serve_stdio_blocking`). Backends nativos en `backends/{search,sessions,spec,docs,finish,autopilot}.rs`. Python equivalente: `cortex/mcp/server.py` (API mcp 1.x, pin `<2`).

## 4. TUI

`cortex-tui`: ratatui, pantallas Home/sessions/search, splash, branding. Lo abre el CLI sin argumentos. `cortex-companion` es otra TUI más grande (HUD, actions, brain panel, menú de catálogo, approval modal).

## 5. Companion / HERDR

Bins:

- `cortex-companion` — app completa
- `cortex-herdr-sidecar` — split pane
- `cortex-herdr-float` — HUD flotante
- `cortex-herdr-copilot` — copilot split

`herdr.rs` detecta el agente destino, manda texto al pane tmux, reporta status. `engine.rs` define `Backend` (sesiones, acciones, search, doctor, stats); `InProcessBackend` habla con los mismos servicios que el CLI. Approval: `run_guarded`. Brain panel reusa tools de `cortex-brain`.

## 6. Brain (asistente local)

`cortex-brain`: router determinista (porteo de `cortex/brain/router.py`), chat con protocolo TOOL + confirmación, i18n ES/EN, descarga GGUF (`ureq`), llama.cpp detrás de `--features llama`, ventana dedicada (`window.rs`).

Tools (`tools.rs`):

| Tool | Tier | Efecto |
|---|---|---|
| memory.search | Read | CLI search |
| docs.related | Read | docs relacionados |
| cortex.health | Read | `cortex doctor` |
| vault.stats | Read | conteos |
| session.current | Read | sesión activa |
| webgraph.serve | SafeAction | serve detached |
| actions.propose | Read | lista + comando, no ejecuta |

`cortex-brain-app`: Tauri. `chat.rs` arma el engine y `dispatch_tool`. `ipc.rs` socket JSON-line (Windows stub). `projects.rs` escanea repos. `graph.rs` extrae grafo + session status + doctor. `org_memory.rs` lista/approve/reject conocimiento org. Frontend: `apps/brain-ui` (React). `useTauri.ts` es el único puente.

## 7. Webgraph HTTP

Axum router (`create_app`). Endpoints construidos en `server.rs` sobre `WebGraphService` / `FederatedWebGraphService`. Openers resuelven paths dentro del vault. CLI `webgraph serve` lo levanta.

## 8. IDE adapters

`cortex-setup/src/ide/adapters/`: antigravity, claude_code, claude_desktop, codex, cursor, hermes, opencode, pi, vscode, windsurf, zed. Escriben bloques marcados `BEGIN CORTEX SECTION`. Hooks de sesión: claude_code (settings.json Edit|Write|MultiEdit → `cortex session checkpoint`), cursor (git post-commit), opencode (hooks.md), pi (justfile). `CANONICAL_TOOLS` se traducen por IDE (`canonical_tools.rs`). `VALIDATED_IDES = ["claude_code", "opencode"]`.

## 9. ActionEngine / `cortex next`

Catálogo (`cortex-actions/src/catalog.rs`): setup_finish_bootstrap, session_close_stale, session_checkpoint_now, vault_reindex, vault_validate_docs, quality_run_gates, learn_topic, knowledge_promote, memory_prune, ide_resync, session_suggest_next_phase. Scheduler top-N (default 5). Runner registra ejecución. Learning + signals de memoria (ventana 14 días).

## 10. Tutor / Doctor / Pipeline

Tutor: menú + topics embebidos (`content/*.txt`) + `get_hint(ProjectState)`. Doctor: scopes y checks nativos. Pipeline: stages security/lint/test/documentation, `abort_early`, runner GitHub Actions YAML.
