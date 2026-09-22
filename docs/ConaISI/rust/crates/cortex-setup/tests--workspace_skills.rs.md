# rust/crates/cortex-setup/tests/workspace_skills.rs

## Qué tiene adentro

Paridad artefacto cortex-sync: SSoT `cortex/setup/workspace_files/` vs copia `.cortex/skills/` y referencia craft on-demand.

## Para qué sirve

G-A3a tríada thin+craft.

## Relaciones

### Recibe de

- workspace_files markdown.

### Envía a

- cargo test.

### Notas de implementación observadas en el código

Lee workspace_files como dato, no como código Python.
