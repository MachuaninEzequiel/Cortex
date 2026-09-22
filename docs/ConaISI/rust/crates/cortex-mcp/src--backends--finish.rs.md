# rust/crates/cortex-mcp/src/backends/finish.rs

## Qué tiene adentro

`NativeFinishBackend`. `git rev-parse HEAD`, `git diff --name-status start..end`. Reconstrucción y cierre con datos persistidos. `run_hooks=true` y sugerencia ADR: wiring P12 incompleto — se reporta lo persistido con honestidad.

## Para qué sirve

Finish/briefing reales. También lo usa `cortex-cli finish`.

## Relaciones

### Recibe de

- SessionService + git en repo_root.

### Envía a

- ReconstructionMirror / FinishResultMirror.

### Notas de implementación observadas en el código

No re-ejecuta hooks pesados por default.
