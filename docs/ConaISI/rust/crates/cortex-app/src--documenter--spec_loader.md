# src/documenter/spec_loader.rs

## Qué tiene adentro

`LoadedSpec` + `load_spec(path)` + `extract_section(body, heading)`. `AdrSuggestion` + `suggest_adrs(checkpoints)` (puerto `adr_evaluator.py`).

## Para qué sirve

Leer la spec markdown asociada a la sesión (goal, files_in_scope, acceptance, hooks) y sugerir ADRs desde checkpoints.

## Relaciones

### Recibe de

- Path de spec en `SessionRecord.spec_path`; checkpoints.

### Envía a

- Reconstructor, `CiValidator`, persister.

### Notas de implementación observadas en el código

Usado también por CI para scope drift.
