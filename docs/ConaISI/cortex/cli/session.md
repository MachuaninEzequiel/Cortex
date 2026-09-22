# cortex/cli/session.py

## Qué tiene adentro

- **Ruta de código:** `cortex/cli/session.py` (846 líneas).
- **Módulo Python:** `cortex.cli.session`.
- **Docstring del módulo:** ``cortex session`` — user-facing CLI for the Session primitive.
- **Funciones de módulo:**
  - `_build_service(project_root)` — Resolve the layout and construct a ``SessionService``.
  - `_record_summary(record)` — Reduced representation used by the JSON output of ``list``.
  - `_error_exit(message, code)`
  - `current_command(project_root, output_json)` — Print the id of the currently active Session (or a friendly message).
  - `list_command(status, project_root, output_json)` — List Sessions on disk, newest first.
  - `show_command(session_id, project_root, output_json, watch, refresh)` — Print the full detail of one Session.
  - `_run_watch_tui(project_root)` — Shared entry point for ``session watch`` and ``session show --watch``.
  - `watch_command(session_id, refresh, project_root)` — Open a live TUI view of the active (or named) Session.
  - `diff_command(session_id, project_root)` — Print ``git diff <start_commit>..<end_ref>`` for the Session.
  - `switch_command(session_id, project_root)` — Set ``session_id`` as the active session. It must exist and be OPEN.
  - `checkpoint_command(source, note, verified_claim, unverified_claim, artifact, session_id, project_root, output_json)` — Append a checkpoint to the active session.
  - `abandon_command(session_id, reason, yes, project_root)` — Close a session as ABANDONED. No session note is created.
  - `_resolve_record(service, session_id)` — Load ``session_id`` if provided, otherwise the active session.
  - `_resolve_task_session(service, session_id)` — Pick the requested or active Session for the task subcommands.
  - `task_list_command(session_id, status, project_root, output_json)` — List tasks attached to a Session.
  - `_update_task_status_cli()`
  - `task_done_command(task_id, note, session_id, project_root, output_json)` — Mark a task as ``done``.
  - `task_in_progress_command(task_id, note, session_id, project_root, output_json)` — Mark a task as ``in-progress``.
  - `task_skip_command(task_id, reason, session_id, project_root, output_json)` — Mark a task as ``skipped`` (with mandatory reason).
  - `task_block_command(task_id, reason, session_id, project_root, output_json)` — Mark a task as ``blocked`` (with mandatory reason).
  - `_resolve_installer()`
  - `_resolve_target_dir(project_root)`
  - `hooks_list_command(project_root, output_json)` — List the bundled IDE adapters and report their current install status.
  - `hooks_install_command(ide, project_root, output_json)` — Install the requested IDE hook under the project root.
  - `hooks_uninstall_command(ide, project_root, output_json)` — Uninstall the requested IDE hook from the project root.
  - `hooks_status_command(ide, project_root, output_json)` — Report the install status of one or all IDE adapters.
- **Constantes / símbolos de módulo:** `_PROJECT_ROOT_HELP`, `_REFRESH_MIN`, `_REFRESH_MAX`

## Para qué sirve

``cortex session`` — user-facing CLI for the Session primitive.

Sub-commands:
    current   — id of the active session (or "no active session")
    list      — list sessions, optionally filtered by status
    show      — full detail of one session (defaults to the active one)
    diff      — ``git diff start_commit..(end_commit|HEAD)`` for the session
    switch    — change the active session pointer
    abandon   — close a session as ABANDONED with a reason

All commands accept ``--project-root <path>`` (defaults to CWD) so that
they can be exercised from a tmpdir in tests, and ``--json`` for
machine-readable output suitable for piping into other tools.

The CLI talks directly to :class:`SessionService` (it does NOT spin up the
full :class:`AgentMemory` façade) because Session management does not need
the vault, the embeddings, the retriever, etc. This keeps ``cortex session``
fast and usable even in repos where Cortex is only partially configured.

## Relaciones

### Recibe de

- `cortex.session` (CheckpointSource, SessionRecord, SessionStatus, TaskStatus)
- `cortex.session.errors` (SessionError, SessionNotFound)
- `cortex.session.git` (GitError)
- `cortex.session.hooks` (HookInstaller, default_installer)
- `cortex.session.service` (SessionService)
- `cortex.session.storage` (SessionStorage)
- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `json`, `typer`, `__future__`, `pathlib`, `rich.console`, `rich.table`

### Envía a

- `cortex.cli.main`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 846.
Docstrings de símbolos públicos:
- `current_command`: Print the id of the currently active Session (or a friendly message).
- `list_command`: List Sessions on disk, newest first.
- `show_command`: Print the full detail of one Session.
- `watch_command`: Open a live TUI view of the active (or named) Session.
- `diff_command`: Print ``git diff <start_commit>..<end_ref>`` for the Session.
- `switch_command`: Set ``session_id`` as the active session. It must exist and be OPEN.
- `checkpoint_command`: Append a checkpoint to the active session.
- `abandon_command`: Close a session as ABANDONED. No session note is created.
- `task_list_command`: List tasks attached to a Session.
- `task_done_command`: Mark a task as ``done``.
- `task_in_progress_command`: Mark a task as ``in-progress``.
- `task_skip_command`: Mark a task as ``skipped`` (with mandatory reason).

---
Fuente: código de `cortex/cli/session.py` (AST + grafo de imports internos). No se usó documentación previa.
