# rust/crates/cortex-brain/Cargo.toml

## Qué tiene adentro

Manifiesto del crate `cortex-brain` 0.1.0. Declara:

- binario `cortex-brain` en `src/main.rs`
- dependencias: `regex`, `serde_json`, `encoding_rs`, `cortex-branding`, `ureq`
- dependencia opcional `llama-cpp-2` 0.1.154
- feature `llama = ["dep:llama-cpp-2"]`
- `dev-dependencies` vacío (tests usan `CORTEX_BIN` o stubs)

## Para qué sirve

Define cómo se construye el asistente local: build liviano sin llama.cpp por default; cmake + GGUF solo si se pide `--features llama`.

## Relaciones

### Recibe de

- Workspace (`version`, `edition`, `license`, `ureq`)
- Crate vecino `cortex-branding`

### Envía a

- Cargo/workspace: el binario y la lib que `cortex-brain-app` y `cortex-companion` dependen

### Notas de implementación observadas en el código

El comentario indica que `ureq` se usa para descarga GGUF. Tests no agregan crates extra: stubean el CLI con env.
