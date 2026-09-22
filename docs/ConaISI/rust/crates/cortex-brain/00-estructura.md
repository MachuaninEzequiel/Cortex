# rust/crates/cortex-brain — estructura interna

Fuente: árbol de archivos del crate, `Cargo.toml` y `src/lib.rs`. No se documenta `target/` ni `.cache/` (artefactos de build/descarga).

```
cortex-brain/
├── Cargo.toml
├── src/
│   ├── lib.rs          # raíz de la librería
│   ├── main.rs         # binario CLI stdin/stdout
│   ├── chat.rs         # loop de chat, backends LLM, protocolo TOOL
│   ├── tools.rs        # catálogo READ/SAFE_ACTION + dispatch al CLI
│   ├── router.rs       # ruteo determinista de texto → intent
│   ├── download.rs     # descarga/copia de GGUF (HttpSource / LocalSource)
│   ├── llama.rs        # backend llama.cpp (feature `llama`)
│   ├── paths.rs        # rutas del modelo en ~/.cache/cortex/models
│   ├── i18n.rs         # chrome ES/EN
│   └── window.rs       # relanzar el binario en terminal dedicada
└── tests/
    ├── i18n.rs
    ├── spec_behavior.rs
    ├── tool_i18n.rs
    └── tool_protocol.rs
```

## Qué es este crate

Librería + binario `cortex-brain`: asistente local nativo. Modo default **determinista** (sin tokens, router + tools). Con `--features llama` y un GGUF en disco, usa llama.cpp.

## Dependencias observadas en Cargo.toml

- `regex`, `serde_json`, `encoding_rs`, `ureq`
- `cortex-branding` (banner)
- opcional: `llama-cpp-2` (feature `llama`)

## Relaciones de crate

- **Recibe de:** `cortex-branding` (banner ANSI), CLI `cortex` vía `std::process::Command` (tools), filesystem (`~/.cache/cortex/models`, `config.yaml`).
- **Envía a:** stdout del usuario; spawn detached de `cortex webgraph serve`; HuggingFace HTTP al descargar GGUF.
- **Consumido por:** `cortex-brain-app` (motor in-process), `cortex-companion` (brain_panel, feature llama).
