# rust/crates/cortex-webgraph-server/Cargo.toml

## Qué tiene adentro

Archivo de 27 líneas.
Gate P12B-2: cliente HTTP mínimo sobre std para golpear el server real.
Manifiesto Cargo. Líneas de deps Cortex observadas:
- `cortex-core = { path = "../cortex-core" }`
- `cortex-app = { path = "../cortex-app" }`
- `cortex-workspace = { path = "../cortex-workspace" }`
- `cortex-setup = { path = "../cortex-setup" }`
Nombres de package/bin: cortex-webgraph-server

## Para qué sirve

Gate P12B-2: cliente HTTP mínimo sobre std para golpear el server real.

## Relaciones

### Recibe de

- Sin imports Cortex en el extracto (manifiesto, lock, html, gitignore o JSON).

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-webgraph-server/Cargo.toml`. 27 líneas.
