# cortex/session/hooks/adapters/cursor.py

## Qué tiene adentro

- **Ruta de código:** `cortex/session/hooks/adapters/cursor.py` (201 líneas).
- **Módulo Python:** `cortex.session.hooks.adapters.cursor`.
- **Docstring del módulo:** cortex.session.hooks.adapters.cursor — Git post-commit hook adapter.
- **Clases definidas:**
  - `CursorGitHookAdapter`
    - Manage the Cortex block inside ``.git/hooks/post-commit``.
    - Métodos públicos/especiales: `is_supported`, `install`, `uninstall`, `status`
    - Métodos internos: `_hook_path`, `_require_git_repo`, `_read`, `_render`, `_strip_block`, `_ensure_executable`
- **Constantes / símbolos de módulo:** `POST_COMMIT_RELATIVE`, `START_MARKER`, `END_MARKER`, `SHEBANG`, `HOOK_BLOCK`, `__all__`

## Para qué sirve

cortex.session.hooks.adapters.cursor — Git post-commit hook adapter.

Despite the name, this adapter is **not** Cursor-specific. It installs
into ``.git/hooks/post-commit`` and therefore works for any IDE that
ends up running ``git commit`` — Cursor, VSCode (Cline/Roo/Continue),
plain editors, the terminal. We call it ``cursor`` because Cursor is
the primary target documented in the Pluggable Middle architecture
(§10.5 / Phase 03 §3.3).

The hook fires after every commit and emits a checkpoint with the SHA
and subject of the new commit. The ``|| true`` clause guarantees that a
Cortex failure (e.g. ``cortex`` not on PATH, no active session) never
turns a successful commit into a failed one.

The hook block is delimited by sentinel markers so install / uninstall
do not clobber any pre-existing user content. If the user has their own
``post-commit`` script, the adapter appends a separate block; uninstall
removes only that block.

## Relaciones

### Recibe de

- `cortex.session.hooks.installer` (HookStatus, InstallResult, UninstallResult)
- Dependencias externas/stdlib: `stat`, `__future__`, `pathlib`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 201.

---
Fuente: código de `cortex/session/hooks/adapters/cursor.py` (AST + grafo de imports internos). No se usó documentación previa.
