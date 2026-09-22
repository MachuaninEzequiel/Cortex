# src/ci/result.rs

## Qué tiene adentro

`ValidationStatus`: pass/warn/blocked/error. `ValidationInput` (diff, repo, commits/branches, pr_number/author, explicit_session_id).

`DriftReason`: out_of_scope / unimplemented. `ScopeDriftFinding`. `ValidationResult` con match, session, spec, files_in_diff, drift, verification, blockers/warnings, exit_code, status, summary_text + campos de PR para markdown. Serializa JSON ordenado vía pyjson (`to_json_dict`).

## Para qué sirve

Contrato estable JSON/Markdown del validador.

## Relaciones

### Recibe de

- `CiValidator`.

### Envía a

- `markdown_formatter`, CLI, goldens P11.

### Notas de implementación observadas en el código

El esquema JSON se declara estable entre releases.
