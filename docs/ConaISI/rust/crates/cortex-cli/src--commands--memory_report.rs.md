# rust/crates/cortex-cli/src/commands/memory_report.rs

## Qué tiene adentro

`memory-report --scope local|enterprise|all --json`. `--telemetry` **no nativo**: stderr + exit 1 (passthrough Python eliminado). Usa `EnterpriseReportingService` + `NativeDoctorBackend`.

## Para qué sirve

Salud de memoria y visibilidad de promoción.

## Relaciones

### Recibe de

- cortex-enterprise reporting + cortex-doctor native backend.

### Envía a

- stdout JSON o texto.

### Notas de implementación observadas en el código

Cierra el seam P12B-3→P12B-4.
