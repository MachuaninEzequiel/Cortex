# cortex/autopilot/cli.py

## Qué tiene adentro

- **Ruta de código:** `cortex/autopilot/cli.py` (355 líneas).
- **Módulo Python:** `cortex.autopilot.cli`.
- **Docstring del módulo:** cortex.autopilot.cli — Typer subapp for ``cortex autopilot ...`` commands.
- **Funciones de módulo:**
  - `_resolve_root(project_root)`
  - `_resolve_service(project_root)`
  - `_emit(payload, json_mode)`
  - `_parse_mode(raw)`
  - `_abort_no_session(exc, json_mode)`
  - `start(mode, project_root, json_output)` — Adopt the active session under the requested mode and surface warnings.
  - `preflight(request, changed_files, project_root, json_output)` — Run the detector pipeline as a dry-run; do not touch any session state.
  - `checkpoint(source, note, verified_claim, unverified_claim, artifact, files_in_scope, project_root, json_output)` — Append a checkpoint to the active session.
  - `finish(auto, handoff, abandon, reason, session_id, project_root, json_output)` — Close the active session — ``--auto`` runs the canonical documenter.
  - `status(session_id, project_root, json_output)` — Show the active or named session.
  - `doctor(project_root, json_output)` — Diagnose the Autopilot installation and state. (Read-only)

## Para qué sirve

cortex.autopilot.cli — Typer subapp for ``cortex autopilot ...`` commands.

Phase 03 refactor: every command delegates to the new
:class:`AutopilotService`, which itself is a thin layer over the canonical
:class:`cortex.session.service.SessionService`.

Commands kept (UX continuity for users who already know them):
    start         — adopt the active session under a chosen mode.
    preflight     — dry-run the detector pipeline (no state mutation).
    checkpoint    — append a checkpoint to the active session.
    finish        — close the active session; ``--auto`` runs the documenter.
    status        — describe the active or named session.
    doctor        — run the Autopilot diagnostic checks.
    install       — install an IDE hook (delegates to legacy adapters
                    until T3.6 ships the new ``cortex session hooks`` flow).
    uninstall     — inverse of ``install``.

Commands removed (Phase 03 §11.3 + §11.4):
    cleanup       — JSONL events no longer exist; sessions live in
                    ``.cortex/sessions/`` and are managed by
                    ``cortex session``.
    report        — fully covered by ``cortex session list``.

## Relaciones

### Recibe de

- `cortex.autopilot.errors` (AutopilotError, NoActiveSessionError)
- `cortex.autopilot.lifecycle` (AutopilotCheckpointRequest, AutopilotFinishRequest, AutopilotPreflightRequest, AutopilotStartRequest)
- `cortex.autopilot.policies` (AutopilotMode)
- `cortex.autopilot.service` (AutopilotService)
- `cortex.session.errors` (SessionNotFound)
- Dependencias externas/stdlib: `json`, `typer`, `__future__`, `pathlib`

### Envía a

- `cortex.cli.main`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 355.
Docstrings de símbolos públicos:
- `start`: Adopt the active session under the requested mode and surface warnings.
- `preflight`: Run the detector pipeline as a dry-run; do not touch any session state.
- `checkpoint`: Append a checkpoint to the active session.
- `finish`: Close the active session — ``--auto`` runs the canonical documenter.
- `status`: Show the active or named session.
- `doctor`: Diagnose the Autopilot installation and state. (Read-only)

---
Fuente: código de `cortex/autopilot/cli.py` (AST + grafo de imports internos). No se usó documentación previa.
