# cortex/cli/ci.py

## Qué tiene adentro

- **Ruta de código:** `cortex/cli/ci.py` (287 líneas).
- **Módulo Python:** `cortex.cli.ci`.
- **Docstring del módulo:** ``cortex ci`` — CI plugin subapp (Pluggable Middle Phase 07).
- **Funciones de módulo:**
  - `_build_validator(project_root)`
  - `_resolve_format(value)`
  - `validate_pr_command(diff, base_commit, head_commit, base_branch, head_branch, pr_number, pr_author, session_id, output_format, project_root)` — Validate a pull request against the matching Cortex Session + spec.
  - `_emit(result, fmt)`
  - `_build_session_service(project_root)`
  - `open_review_session_command(pr_number, base_commit, head_branch, spec_path, project_root, output_json)` — Open a CI-owned review Session (Phase 07 / Level 3).
  - `report_checkpoint_command(session_id, from_validation_result, manual_claim, manual_artifact, note, project_root, output_json)` — Emit a ``CI_BOT`` checkpoint into the review session.
  - `close_review_session_command(session_id, status, reason, project_root, output_json)` — Close the review session into a terminal status.
- **Constantes / símbolos de módulo:** `_PROJECT_ROOT_HELP`, `__all__`

## Para qué sirve

``cortex ci`` — CI plugin subapp (Pluggable Middle Phase 07).

Subcommands:

* ``validate-pr`` (Level 1): runs the validator against the matching
  Session + spec and emits JSON / text / pr-comment output. Exit code
  doubles as the CI gate (0 pass / 1 warn / 2 blocked / 3 error).
* ``open-review-session`` / ``report-checkpoint`` /
  ``close-review-session`` (Level 3): drive a CI-owned Session that
  records the validation history of a PR.

## Relaciones

### Recibe de

- `cortex.ci.diff_io` (DiffResolutionError, read_diff_from_args)
- `cortex.ci.markdown_formatter` (render_pr_comment)
- `cortex.ci.result` (ValidationInput, ValidationResult)
- `cortex.ci.validator` (EXIT_ERROR, CiValidator)
- `cortex.session.service` (SessionService)
- `cortex.session.storage` (SessionStorage)
- `cortex.session.verification` (VerificationRunner)
- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `json`, `typer`, `__future__`, `datetime`, `pathlib`, `rich.console`

### Envía a

- `cortex.cli.main`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 287.
Docstrings de símbolos públicos:
- `validate_pr_command`: Validate a pull request against the matching Cortex Session + spec.
- `open_review_session_command`: Open a CI-owned review Session (Phase 07 / Level 3).
- `report_checkpoint_command`: Emit a ``CI_BOT`` checkpoint into the review session.
- `close_review_session_command`: Close the review session into a terminal status.

---
Fuente: código de `cortex/cli/ci.py` (AST + grafo de imports internos). No se usó documentación previa.
