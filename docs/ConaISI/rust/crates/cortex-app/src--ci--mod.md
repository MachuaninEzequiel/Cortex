# src/ci/mod.rs

## Qué tiene adentro

Plugin CI provider-agnostic. Reexporta: `SessionMatchKind`, `read_diff_from_args`, `DiffResolutionError`, `render_pr_comment`, `DEFAULT_MARKER`, tipos de `result`, `open/close_review_session`, `report_ci_checkpoint`, `find_session_for_pr`, `validate_pull_request`, `CiValidator`, exit codes.

`TempGuard` solo en tests (tmpdir único, Drop borra).

## Para qué sirve

Fachada del módulo CI para CLI `cortex ci validate-pr` y comentarios de PR.

## Relaciones

### Recibe de

- Submódulos ci/* y session.

### Envía a

- `cortex-cli` comando ci; example `ci_check`.

### Notas de implementación observadas en el código

Sin crate `tempfile` en tests de este módulo (usa TempGuard). El crate sí tiene tempfile en dev-deps para otros tests.
