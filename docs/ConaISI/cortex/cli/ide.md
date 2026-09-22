# cortex/cli/ide.py

## Qué tiene adentro

- **Ruta de código:** `cortex/cli/ide.py` (377 líneas).
- **Módulo Python:** `cortex.cli.ide`.
- **Docstring del módulo:** ``cortex ide`` — unified CLI surface for IDE adapters (Obra 02, Fase 3).
- **Funciones de módulo:**
  - `resolve_project_root(explicit)` — Resolve the project root ONCE for the whole command.
  - `_fail(message, code)`
  - `_get_adapter_or_exit(ide_name)` — Resolve an adapter name/alias; unknown names exit with code 2.
  - `_require_ide(ide_name, action)` — No interactive prompts: missing --ide is an error listing options.
  - `_absolute(path, root)`
  - `_uninstall_supported(adapter)` — True when the adapter overrides the ABC's no-op uninstall.
  - `_hook_installer()`
  - `_hook_lookup(installer, adapter_name)` — Return the hook adapter for an IDE adapter name, or None.
  - `run_setup(ide_name, project_root)` — Inject profiles + MCP for one IDE. Returns the files written.
  - `run_remove(ide_name, project_root)` — Remove ONLY Cortex-created content for one IDE. Returns the report.
  - `run_bulk_inject(project_root)` — Legacy bulk injection used only by the deprecated commands.
  - `run_bulk_uninstall(project_root)` — Legacy bulk removal used only by the deprecated commands.
  - `collect_status(adapter, root, installer)` — Build the per-IDE status payload used by text and JSON output.
  - `list_command(output_json)` — List every registered IDE adapter with tier and uninstall support.
  - `setup_command(ide, project_root, dry_run, sync_canonical)` — Install/update Cortex profiles + MCP for one IDE. Idempotent.
  - `remove_command(ide, project_root, dry_run)` — Remove ONLY Cortex-created content for one IDE (never destructive).
  - `status_command(ide, project_root, output_json)` — Report per-IDE: expected config present, MCP configured, session hooks installed.
- **Constantes / símbolos de módulo:** `_PROJECT_ROOT_HELP`, `DEPRECATION_SETUP`, `DEPRECATION_REMOVE`

## Para qué sirve

``cortex ide`` — unified CLI surface for IDE adapters (Obra 02, Fase 3).

One command family for ALL IDEs:

    cortex ide list    [--json]
    cortex ide setup   --ide X [--project-root R] [--dry-run] [--sync-canonical/--no-sync-canonical]
    cortex ide remove  --ide X [--project-root R] [--dry-run]
    cortex ide status  [--ide X] [--json] [--project-root R]

Design rules (docs/transformacion/02-ESTANDAR-UNICO-IDE-CLI.md §3):

* ``project_root`` is EXPLICIT everywhere. When ``--project-root`` is not
  given the CLI resolves cwd → repo root once via
  ``WorkspaceLayout.discover`` with a plain-cwd fallback; no adapter ever
  calls ``Path.cwd()``.
* ``--dry-run`` reports what WOULD be done and never writes or deletes a
  single byte (fixes top-10 bug #4 for the whole IDE surface).
* No interactive prompts on this surface: missing ``--ide`` is a clear
  error listing the available IDEs by tier (exit code 2).
* The legacy commands (``install-ide``, ``uninstall-ide``, ``inject``,
  ``sync-ide``) delegate to the same ``run_*`` functions below, so old and
  new surface stay behaviorally identical during the deprecation window.

## Relaciones

### Recibe de

- `cortex.ide.base` (IDEAdapter)
- `cortex.ide.registry` (get_adapter, get_all_adapters, get_ide_tier, is_ide_validated)
- `cortex.session.hooks` (HookInstaller, default_installer)
- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `json`, `typer`, `__future__`, `pathlib`, `typing`, `rich.console`, `rich.table`

### Envía a

- `cortex.cli.main`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 377.
Docstrings de símbolos públicos:
- `resolve_project_root`: Resolve the project root ONCE for the whole command.
- `run_setup`: Inject profiles + MCP for one IDE. Returns the files written.
- `run_remove`: Remove ONLY Cortex-created content for one IDE. Returns the report.
- `run_bulk_inject`: Legacy bulk injection used only by the deprecated commands.
- `run_bulk_uninstall`: Legacy bulk removal used only by the deprecated commands.
- `collect_status`: Build the per-IDE status payload used by text and JSON output.
- `list_command`: List every registered IDE adapter with tier and uninstall support.
- `setup_command`: Install/update Cortex profiles + MCP for one IDE. Idempotent.
- `remove_command`: Remove ONLY Cortex-created content for one IDE (never destructive).
- `status_command`: Report per-IDE: expected config present, MCP configured, session hooks installed.

---
Fuente: código de `cortex/cli/ide.py` (AST + grafo de imports internos). No se usó documentación previa.
