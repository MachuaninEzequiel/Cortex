# rust/crates/cortex-enterprise/Cargo.toml

## Qué tiene adentro

Archivo de 20 líneas.
Manifiesto Cargo. Líneas de deps Cortex observadas:
- `cortex-app = { path = "../cortex-app" }`
- `cortex-setup = { path = "../cortex-setup" }`
- `cortex-workspace = { path = "../cortex-workspace" }`
Nombres de package/bin: cortex-enterprise

## Para qué sirve

Archivo de soporte de `rust/crates/cortex-enterprise/Cargo.toml` (test, example, manifiesto o config).

## Relaciones

### Recibe de

- Sin imports Cortex en el extracto (manifiesto, lock, html, gitignore o JSON).

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-enterprise/Cargo.toml`. 20 líneas.
