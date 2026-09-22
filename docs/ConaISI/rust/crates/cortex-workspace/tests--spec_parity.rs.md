# rust/crates/cortex-workspace/tests/spec_parity.rs

## Qué tiene adentro

Tests de integración/paridad del crate (layout, handoff YAML, gitignore, skills hashes, runtime_context). Usa `tempfile` y `sha2`.

## Para qué sirve

Fijar el contrato P12B-1 en `cargo test -p cortex-workspace` sin invocar el CLI.

## Relaciones

### Recibe de

- API de `cortex-workspace`.
- Bundles embebidos vs archivos en `cortex/skills/`.

### Envía a

- Resultado de cargo test.

### Notas de implementación observadas en el código

Los tests Python homólogos (`tests/unit/workspace`, `handoff.py`, `runtime_context.py`, `skills`) se nombran como especificación en `lib.rs`.
