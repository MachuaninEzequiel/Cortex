# apps/brain-ui/src/App.tsx

## Qué tiene adentro

Componente raíz. Estado: proyectos, modelo, mensajes por proyecto, download, RAM/idle, modales (settings, tool approval, webgraph, doctor, org memory), idioma, always-on-top, nodos pineados.

Efectos: `list_projects`/`list_models` al montar; ticker 5s `reap_idle` + `loaded_projects`; listeners `chat-chunk` / `download-progress`.

Handlers: refresh scan, `set_active_model`, `download_model`, chat stream, persistencia historial, aprobación de tools (`execute_cortex_tool`), grafo/doctor/org.

## Para qué sirve

Orquestar la UI desktop contra el engine Tauri.

## Relaciones

### Recibe de

- `./types`, `./hooks/useTauri`, `./i18n`, todos los components listados en imports
- payloads Rust (`ProjectEntry`, `ChatTurn`, `DownloadProgressPayload`, …)

### Envía a

- `tauriInvoke` / `tauriListen` (mismos nombres de command que `lib.rs`)
- props a TopBar, Sidebar, Chat, StatusBar, modales

### Notas de implementación observadas en el código

Fuera de Tauri (tests/web) los invoke fallan y se loguean; el ticker de reap traga errores.
