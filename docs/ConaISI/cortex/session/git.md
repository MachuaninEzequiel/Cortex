# cortex/session/git.py

## Qué tiene adentro

- **Ruta de código:** `cortex/session/git.py` (146 líneas).
- **Módulo Python:** `cortex.session.git`.
- **Docstring del módulo:** cortex.session.git — Minimal subprocess wrappers for git commands.
- **Clases definidas:**
  - `GitError` (Exception)
    - Raised on any failure of an underlying git command.
- **Funciones de módulo:**
  - `_run(args, repo_root)` — Run ``git <args>`` in *repo_root* and return stdout (text).
  - `is_git_repo(repo_root)` — Return ``True`` iff *repo_root* is inside a git working tree.
  - `get_head_commit(repo_root)` — Return the 40-char lowercase hex SHA-1 of HEAD.
  - `try_get_head_commit(repo_root)` — Soft variant of :func:`get_head_commit` that returns ``None`` on failure.
  - `get_current_branch(repo_root)` — Return the current branch name (or ``HEAD`` when detached).
  - `try_get_current_branch(repo_root)` — Soft variant of :func:`get_current_branch`.
  - `diff(start_ref, end_ref, repo_root)` — Return ``git diff <start_ref>..<end_ref>`` stdout.
  - `diff_name_status(start_ref, end_ref, repo_root)` — Return ``git diff --name-status <start_ref>..<end_ref>`` stdout.
- **Constantes / símbolos de módulo:** `_HEX_DIGITS`, `_GIT_SUBPROCESS_TIMEOUT_SECONDS`, `__all__`

## Para qué sirve

cortex.session.git — Minimal subprocess wrappers for git commands.

We avoid GitPython (not a project dependency, ships ~MB of bytecode) and
shell out to ``git`` directly. The wrappers are intentionally small and
typed so the service layer can mock or replace them in tests.

All functions raise :class:`GitError` on subprocess failure, on a missing
``git`` executable, on a subprocess timeout, or on output that violates a
documented invariant (e.g. ``rev-parse HEAD`` not returning a full SHA-1).

For projects that lack a git repository entirely, callers should prefer
the ``try_*`` helpers and :func:`is_git_repo` over the strict wrappers —
those return ``None`` / ``False`` instead of raising so the service layer
can fall back to ``GITLESS_COMMIT_PLACEHOLDER`` and run in degraded mode.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `subprocess`, `__future__`, `pathlib`

### Envía a

- `cortex.cli.session`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 146.
Docstrings de símbolos públicos:
- `is_git_repo`: Return ``True`` iff *repo_root* is inside a git working tree.
- `get_head_commit`: Return the 40-char lowercase hex SHA-1 of HEAD.
- `try_get_head_commit`: Soft variant of :func:`get_head_commit` that returns ``None`` on failure.
- `get_current_branch`: Return the current branch name (or ``HEAD`` when detached).
- `try_get_current_branch`: Soft variant of :func:`get_current_branch`.
- `diff`: Return ``git diff <start_ref>..<end_ref>`` stdout.
- `diff_name_status`: Return ``git diff --name-status <start_ref>..<end_ref>`` stdout.

---
Fuente: código de `cortex/session/git.py` (AST + grafo de imports internos). No se usó documentación previa.
