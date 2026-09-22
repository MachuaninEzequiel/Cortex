# rust/crates/cortex-brain-app/src/lib.rs

## Qué tiene adentro

Shell Tauri + IPC + commands. `Role::{App, QueryClient, ProjectsList}` vía `from_argv` (`--query` gana, luego `--projects-list`, else App).

Commands Tauri registrados en `run()`:

- proyectos: `list_projects`, `refresh_projects`
- chat: `chat_turn`, `chat_turn_stream` (emite `chat-chunk`), `loaded_projects`, `reap_idle`
- modelos: `list_models`, `download_model` (emite `download-progress`, `HttpSource` en `spawn_blocking`), `set_active_model`
- historial: `load_chat_history`, `save_chat_message`, `clear_chat_history` (`<project>/.cortex/brain/history.jsonl`)
- ventana: `toggle_window`, `hide_window`, `show_window`, `set_always_on_top`
- grafo/salud: `get_project_graph`, `get_session_status`, `run_doctor_inspect`, `open_webgraph_browser`
- org: `get_org_memory`, `approve_org_candidate`, `reject_org_candidate`
- tools: `execute_cortex_tool` (`cortex-rs` luego `cortex`, fallback nativo session/doctor)
- debug: `log_to_terminal`

`handle_connection`: NDJSON; `kind=focus` trae la ventana; query → `respond_streaming` (chunks + done/error).

`run()`: `BrainEngine` compartido (Arc) entre IPC thread y estado Tauri; atajo global Ctrl+Shift+B; plugin shortcut.

## Para qué sirve

Unir GUI, cliente CLI `--query` y motor in-process en un solo binario con single-instance (socket).

## Relaciones

### Recibe de

- `chat::BrainEngine`, `ipc`, `projects`, `graph`, `org_memory`
- `cortex_brain::download` / `paths`
- Tauri AppHandle / Emitter / Manager

### Envía a

- webview (invoke + events)
- Unix socket (JSON-lines)
- stderr (`eprintln` de auditoría)

### Notas de implementación observadas en el código

Turnos serializados por Mutex del engine (chdir + i18n). `open_webgraph_browser` spawnea `cortex webgraph serve --project-root` y `xdg-open http://127.0.0.1:8765`.
