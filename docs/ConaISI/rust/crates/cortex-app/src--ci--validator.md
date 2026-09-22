# src/ci/validator.rs

## Qué tiene adentro

Exit codes: PASS 0, WARN 1, BLOCKED 2, ERROR 3.

`CiValidator { sessions, verifier, repo_root }`. `validate(payload)`:
- `find_for_pr`
- `parse_files_from_diff`
- sin sesión → resultado no_session
- HANDOFF → warning; ABANDONED → blocker
- `scope_cross_check` vs spec.files_in_scope (out_of_scope warning, unimplemented finding)
- corre verification hooks
- arma `ValidationResult` + exit_code

`validate_pull_request` función libre. `parse_files_from_diff(diff_text) -> Vec<PathBuf>`.

## Para qué sirve

Corazón de `cortex ci validate-pr` (Level 1).

## Relaciones

### Recibe de

- `ValidationInput`, `SessionService`, `VerificationRunner`, `load_spec`, `documenter::scope_cross_check`.

### Envía a

- `ValidationResult` → formatters/CLI.

### Notas de implementación observadas en el código

Level 1 = validate; Level 2 markdown comment; Level 3 review sessions.
