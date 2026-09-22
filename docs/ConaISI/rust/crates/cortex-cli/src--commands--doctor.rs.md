# rust/crates/cortex-cli/src/commands/doctor.rs

## Qué tiene adentro

`DoctorArgs` (`--project-root`, `--strict`, `--scope` project|enterprise|all). Presentación: `[OK]` stdout, `[FAIL]` stderr, `[WARN]`/`[INFO]` stdout. rc=1 si failures; rc=1 si `--strict` y warnings. Llama `cortex_doctor::doctor::run_doctor`.

## Para qué sirve

`cortex doctor`.

## Relaciones

### Recibe de

- `cortex_doctor`, `paths::resolve_project_root`.

### Envía a

- stdout/stderr y exit code.

### Notas de implementación observadas en el código

Checks stub emiten `backend no nativo aún (<módulo>)`; el gate Python normaliza STUB_TABLE.
