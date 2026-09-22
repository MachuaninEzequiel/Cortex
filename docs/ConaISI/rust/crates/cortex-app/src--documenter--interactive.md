# src/documenter/interactive.rs

## Qué tiene adentro

Máquina de estados finish-session. I/O inyectable: `InputProvider = Box<dyn FnMut(&str)->String>`, `EditorOpener`.

`InteractiveAction`, `InteractiveResult`, `InteractiveSession`, `seed_body_for_editor(reconstruction)`.

El rendering rich de Python no es contrato; transcript texto plano. Lo gateado es `prompt()` y el consumo exacto de input.

## Para qué sirve

Finish interactivo (humano elige status/edita body) testeable sin TTY.

## Relaciones

### Recibe de

- `ReconstructionOutput`; input/editor inyectados.

### Envía a

- Persister / CLI finish modo interactive.

### Notas de implementación observadas en el código

P12A-8 T4.1. Checker `p12a8_check`.
