# rust/crates/cortex-workspace/examples/workspace_check.rs

## Qué tiene adentro

Binario de ejemplo/checker P12B-1. Uso: `workspace_check <fixtures_dir> <golden_dir>`. Copia fixtures a workdir temporal, reproduce la secuencia del oráculo Python y compara bytes normalizando `{{ROOT}}`.

## Para qué sirve

Verificar paridad de layout/handoff/gitignore/skills/runtime_context contra goldens capturados.

## Relaciones

### Recibe de

- Directorios de fixtures y goldens en disco.
- API pública de `cortex-workspace`.

### Envía a

- stdout/stderr de PASS/FAIL y código de salida.

### Notas de implementación observadas en el código

No es parte del binario `cortex-cli`; se corre con `cargo run -p cortex-workspace --example workspace_check`.
