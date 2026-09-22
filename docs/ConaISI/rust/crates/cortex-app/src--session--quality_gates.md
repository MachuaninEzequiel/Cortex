# src/session/quality_gates.rs

## Qué tiene adentro

Review de checkpoints en dos etapas, sin I/O.

Constantes: placeholders `tbd|fixme|???`; keywords test/build/lint/check/ci; claim mínimo 10 chars; prefijos de artefactos de proceso `.cortex/vault/<tipo>/`.

`ReviewAction`: accept/redelegate/warn. `ReviewVerdict { accepted, stage_1_passed, stage_2_passed, reason, action }`. `PhaseGateOutcome`. `check_phase_gate(checkpoint)`. `review_checkpoint(checkpoint, files_in_scope)`.

Stage 1: artefacts fuera de scope (excepto process artifacts) fallan; hace falta verified_claims o artifacts_touched.

Stage 2: placeholders en note; claims de test demasiado cortas.

## Para qué sirve

Aceptar o rechazar un checkpoint contra la spec.

## Relaciones

### Recibe de

- `session::Checkpoint` y `files_in_scope` de la spec/tasks.

### Envía a

- `SessionService` / CLI review / examples `verification_check`.

### Notas de implementación observadas en el código

Funciones puras. Paths se normalizan posix (`path_posix`).
