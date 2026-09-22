# rust/crates/cortex-services/Cargo.toml

## Qué tiene adentro

Manifiesto `cortex-services`. Deps: `chrono`, `cortex-app`, `cortex-setup`, `serde`, `serde_json`, `serde_yaml`, `regex`, `uuid` (default-features=false, feature `v4`).

## Para qué sirve

Enlaza el crate de servicios de dominio a writers (setup) y Session (app).

## Relaciones

### Recibe de

- Workspace Cargo y crates `cortex-app`, `cortex-setup`.

### Envía a

- `cortex-cli`, `cortex-mcp`, `cortex-pipeline` (según workspace).

### Notas de implementación observadas en el código

`uuid` sin default-features para no arrastrar RNG extra innecesario.
