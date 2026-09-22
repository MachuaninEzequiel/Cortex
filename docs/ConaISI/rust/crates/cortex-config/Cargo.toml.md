# Cargo.toml

## Qué tiene adentro

Paquete `cortex-config`. Deps workspace: `serde` (derive), `serde_json`, `serde_yaml`. Sin `[lib]` especial (lib default). `forbid(unsafe_code)` está en `src/lib.rs`, no aquí.

## Para qué sirve

Declarar el crate de config YAML↔JSON canónico.

## Relaciones

### Recibe de

- Workspace serde.

### Envía a

- `cortex-app` y `cortex-cli` lo dependen por path.

### Notas de implementación observadas en el código

No hay features. Dev-dependencies vacío.
