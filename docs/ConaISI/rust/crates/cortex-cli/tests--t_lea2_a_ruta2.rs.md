# rust/crates/cortex-cli/tests/t_lea2_a_ruta2.rs

## Qué tiene adentro

`autopilot doctor` nativo (6 checks, payload del oráculo) + rechazo de install/uninstall (Fase 04).

## Para qué sirve

MITAD A ruta 2.

## Relaciones

### Recibe de

- autopilot.rs + AutopilotService.

### Envía a

- cargo test.

### Notas de implementación observadas en el código

Bytes capturados de `python -m cortex.cli.main autopilot doctor`.
