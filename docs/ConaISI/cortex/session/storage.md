# cortex/session/storage.py

## Qué tiene adentro

- **Ruta de código:** `cortex/session/storage.py` (359 líneas).
- **Módulo Python:** `cortex.session.storage`.
- **Docstring del módulo:** cortex.session.storage — File-based persistence for ``SessionRecord``.
- **Clases definidas:**
  - `SessionStorage`
    - File-based persistence for :class:`SessionRecord`.
    - Métodos públicos/especiales: `__init__`, `root`, `file_path`, `active_pointer_path`, `save`, `mutate`, `save_new`, `load`, `exists`, `delete`, `list_all`, `list_by_status`, `get_active_session_id`, `set_active_session_id`
    - Métodos internos: `_file_for`, `_tmp_file_for`, `_gc_orphan_tmps`, `_active_pointer`, `_ensure_dir`
- **Funciones de módulo:**
  - `_path_lock(path)` — Return the process-wide reentrant lock that guards writes to ``path``.
  - `_is_transient_replace_error(exc)` — Return True for OS errors that justify an ``os.replace`` retry.
  - `_atomic_replace(tmp, dst)` — ``os.replace`` with bounded retry on transient OS errors.
- **Constantes / símbolos de módulo:** `SESSION_FILE_SUFFIX`, `ACTIVE_POINTER_FILENAME`, `_TMP_SUFFIX`, `_TMP_MAX_AGE_SECONDS`, `_PATH_LOCKS`, `_PATH_LOCKS_MUTEX`, `__all__`

## Para qué sirve

cortex.session.storage — File-based persistence for ``SessionRecord``.

Layout::

    .cortex/sessions/
        <session_id>.yaml      # one file per session
        active.txt             # single line: id of the currently active session

Atomicity:
    Every write goes through a temporary file followed by :func:`os.replace`,
    which is atomic on POSIX and on Windows NTFS. Interrupted writes leave
    the previous content intact (or no file at all, for first writes).

Concurrency:
    The MCP server runs tool calls in a ``ThreadPoolExecutor`` (up to
    ``CORTEX_MCP_MAX_WORKERS`` workers, default 4). Clients that double-dispatch
    requests (observed with the Pi client) trigger parallel writes against the
    same session file. We serialize writes per final-path with a process-wide
    lock map (:func:`_path_lock`) and wrap :func:`os.replace` in a short retry
    loop (:func:`_atomic_replace`) to survive transient Windows sharing
    violations from antivirus / indexer scans. See
    ``docs/incidents/2026-05-22_appfutbol-mcp-duplicate-loop/``.

Corrupted files:
    ``list_all`` and ``list_by_status`` log a warning and skip any
    ``*.yaml`` whose content fails to parse, instead of raising. The
    explicit ``load`` operation raises :class:`SessionStorageCorrupted`
    when a specific id cannot be parsed.

## Relaciones

### Recibe de

- `cortex.session.errors` (SessionAlreadyExists, SessionNotFound, SessionStorageCorrupted)
- `cortex.session.models` (SessionRecord, SessionStatus)
- Dependencias externas/stdlib: `logging`, `os`, `threading`, `time`, `yaml`, `__future__`, `collections.abc`, `pathlib`

### Envía a

- `cortex.autopilot.doctor`
- `cortex.autopilot.service`
- `cortex.ci.session_matcher`
- `cortex.cli.ci`
- `cortex.cli.session`
- `cortex.core`
- `cortex.session.service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 359.
Docstrings de símbolos públicos:
- `SessionStorage.root`: The sessions directory. Created on demand by ``save``.
- `SessionStorage.file_path`: Ruta canónica del YAML de una sesión (lectura/watchers).
- `SessionStorage.active_pointer_path`: Ruta del puntero de sesión activa (``active.txt``).
- `SessionStorage.save`: Persist ``record`` atomically. Overwrites any existing file.
- `SessionStorage.mutate`: Transactional load→mutate→save under the per-path lock.
- `SessionStorage.save_new`: Persist ``record`` and refuse to overwrite an existing file.
- `SessionStorage.load`: Read and validate a session by id.
- `SessionStorage.delete`: Remove the session file.
- `SessionStorage.list_all`: Return every session on disk that can be parsed.
- `SessionStorage.get_active_session_id`: Return the id of the active session, or ``None`` if unset.
- `SessionStorage.set_active_session_id`: Set / clear the active pointer atomically.

---
Fuente: código de `cortex/session/storage.py` (AST + grafo de imports internos). No se usó documentación previa.
