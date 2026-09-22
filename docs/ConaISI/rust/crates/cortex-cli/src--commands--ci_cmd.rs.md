# rust/crates/cortex-cli/src/commands/ci_cmd.rs

## Qué tiene adentro

`ci validate-pr` (diff file o commits, session, format json|text|pr-comment). `open-review-session`, `report-checkpoint`, `close-review-session`. Sobre `cortex_app::ci::{CiValidator, read_diff_from_args}` + SessionService + VerificationRunner.

## Para qué sirve

Validar PRs contra Session en CI.

## Relaciones

### Recibe de

- Diff git / archivo `--diff`.
- Sesiones en disco.

### Envía a

- JSON/texto/comentario PR; exit codes de ci.

### Notas de implementación observadas en el código

`--format` inválido → lista json, pr-comment, text.
