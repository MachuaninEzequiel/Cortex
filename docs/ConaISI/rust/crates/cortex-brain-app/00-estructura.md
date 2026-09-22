# rust/crates/cortex-brain-app — estructura interna

Binario unificado `cortex-brain` (GUI Tauri). El frontend vive en `apps/brain-ui/` (`tauri.conf.json` → `frontendDist: ../../../apps/brain-ui/dist`).

```
cortex-brain-app/
├── Cargo.toml
├── build.rs                 # tauri_build::build()
├── tauri.conf.json
├── capabilities/default.json
├── .gitignore
├── icons/                   # 32/128 png, icns, ico (binarios; no se documentan uno a uno)
├── gen/schemas/             # JSON generados por Tauri (acl, capabilities, desktop/linux)
├── src/
│   ├── lib.rs               # Role, commands Tauri, run(), handle_connection IPC
│   ├── main.rs              # argv → App | QueryClient | ProjectsList
│   ├── chat.rs              # BrainEngine in-process (llama o determinista)
│   ├── ipc.rs               # Unix socket JSON-lines
│   ├── projects.rs          # scan HOME + cache brain-projects.json
│   ├── graph.rs             # grafo/sesión/doctor locales para la UI
│   └── org_memory.rs        # candidatos enterprise vault
└── tests/
    ├── smoke.rs
    └── eval_governance_model.rs
```

No se documenta `.cache/` ni `dest.gguf`.

## Dependencias (Cargo.toml)

`tauri` 2, `tauri-plugin-global-shortcut`, serde/yaml/json, sha2, chrono, `cortex-brain`, `cortex-enterprise`, `cortex-workspace`, `libc` (Linux). Feature `llama` reexporta `cortex-brain/llama`.

## Relaciones

- **Recibe de:** `cortex-brain` (motor, download, paths, tools), layout workspace, vault/sessions en disco, UI React empaquetada.
- **Envía a:** webview (commands + eventos `chat-chunk`/`download-progress`), socket IPC, CLI `--query`/`--projects-list`, proceso `cortex webgraph serve`.
