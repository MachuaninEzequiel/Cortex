# tests/compute_diff.rs

## Qué tiene adentro

Test de integración: `SessionService::compute_diff` vs git real (repo 2 commits con tempfile) y que `SessionService` es `Clone` (TUI carga detalle en otro thread). Fija `start_commit` por YAML. Cubre gitless → string vacío (`GITLESS_COMMIT_PLACEHOLDER`).

## Para qué sirve

Gate del port `compute_diff` (oráculo `session/service.py:476`).

## Relaciones

### Recibe de

- `SessionService`, `SessionStorage`, git del entorno.

### Envía a

- `cargo test -p cortex-app`.

### Notas de implementación observadas en el código

Único test file del crate (el resto de paridad está en examples).
