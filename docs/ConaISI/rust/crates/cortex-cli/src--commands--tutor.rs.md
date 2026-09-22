# rust/crates/cortex-cli/src/commands/tutor.rs

## Qué tiene adentro

`tutor [TOPIC]`: muestra recurso embebido de cortex-tutor o menú interactivo (EOF → rc 0). `run_hint()`: tip contextual en `rich_panel` width 80.

## Para qué sirve

Guía offline zero-tokens.

## Relaciones

### Recibe de

- `cortex_tutor::{engine, topics, hint}`.
- Estado de proyecto para hint.

### Envía a

- stdout paneles.

### Notas de implementación observadas en el código

`tutor <slug>` es self-golden (~98 col cosmética). `hint` es paridad live vs Python pipado.
