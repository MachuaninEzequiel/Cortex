# rust/crates/cortex-brain-app/src/chat.rs

## Qué tiene adentro

Motor in-process sobre `cortex_brain`:

- `ToolCall`, `ChatMessagePayload`, `ModelEntry`, `ChatTurn { text, tool_calls, backend }`
- Catálogo curado `CURATED_MODELS`: LFM2.5 1.2B Q4_K_M, Qwen 2.5 Coder 1.5B/3B, DeepSeek R1 Distill 1.5B + GGUF extra en `~/.cache/cortex/models/`
- `list_available_models()`
- `BrainEngine`: HashMap proyecto → backend, idle 90s, `BackendFactory`, `active_model`
- `SharedEngine = Arc<BrainEngine>`
- Load perezoso: feature `llama` + GGUF → `LlamaChatBackend`; si no → `DeterministicBackend`
- Read-tools (`Tier::Read`) se auto-ejecutan; `SafeAction` se deniega y viaja en `tool_calls` para el modal UI
- CWD: `chdir` al proyecto dentro del lock del engine; guard restaura
- `/quit` por IPC no mata la app (devuelve despedida)
- `set_active_model` vacía backends en RAM
- `reap_idle()` / `loaded_projects()`

## Para qué sirve

Un turno de chat por proyecto con el mismo protocolo TOOL del binario CLI, compartido entre GUI e IPC.

## Relaciones

### Recibe de

- `cortex_brain::{chat, i18n, tools, paths, llama?}`
- texto usuario + path de proyecto

### Envía a

- `ChatTurn` a commands Tauri / `handle_connection`
- `tools::dispatch` (con CWD del proyecto)
- stderr al cambiar modelo

### Notas de implementación observadas en el código

N proyectos activos = N copias del modelo en RAM (limitación v1). Historial del backend llama vive en RAM; la UI persiste JSONL aparte (`lib.rs`).
