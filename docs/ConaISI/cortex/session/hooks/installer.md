# cortex/session/hooks/installer.py

## Qué tiene adentro

- **Ruta de código:** `cortex/session/hooks/installer.py` (184 líneas).
- **Módulo Python:** `cortex.session.hooks.installer`.
- **Docstring del módulo:** cortex.session.hooks.installer — Generic hook installer infrastructure.
- **Clases definidas:**
  - `InstallResult`
    - Outcome of :meth:`HookInstaller.install` / :meth:`HookAdapter.install`.
  - `UninstallResult`
    - Outcome of :meth:`HookInstaller.uninstall` / :meth:`HookAdapter.uninstall`.
  - `HookStatus`
    - Current installation state of an adapter under a target directory.
  - `HookAdapter` (Protocol)
    - Protocol every IDE-specific adapter must implement.
    - Métodos públicos/especiales: `is_supported`, `install`, `uninstall`, `status`
  - `HookInstaller`
    - Registry + dispatcher for :class:`HookAdapter` instances.
    - Métodos públicos/especiales: `__init__`, `list_available_adapters`, `list_supported`, `get`, `install`, `uninstall`, `status`, `status_all`
- **Funciones de módulo:**
  - `default_installer()` — Build the installer with the bundled adapters.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.session.hooks.installer — Generic hook installer infrastructure.

This module defines the contract every IDE-specific hook adapter must
satisfy, plus the orchestrator (:class:`HookInstaller`) that the CLI
talks to.

Each adapter is responsible for:

* Detecting whether its target IDE/runtime is supported on the current
  system (so the installer can present a useful ``list`` to the user).
* Installing a small, IDE-native artifact that, when triggered by an
  IDE event (file save, post-commit, etc.), invokes the
  ``cortex session checkpoint --source ide-hook ...`` CLI command.
* Removing that artifact cleanly on ``uninstall``.
* Reporting current status (installed / not installed) for the doctor.

The contract is intentionally narrow. Anything more complex than a
trigger script lives outside this layer.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`, `collections.abc`, `dataclasses`, `pathlib`, `typing`

### Envía a

- `cortex.session.hooks`
- `cortex.session.hooks.adapters.claude_code`
- `cortex.session.hooks.adapters.cursor`
- `cortex.session.hooks.adapters.opencode`
- `cortex.session.hooks.adapters.pi`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 184.
Docstrings de símbolos públicos:
- `HookAdapter.is_supported`: Whether this adapter can run on the current machine.
- `HookAdapter.install`: Install the hook artifact inside ``target_dir``.
- `HookAdapter.uninstall`: Remove the hook artifact from ``target_dir``.
- `HookAdapter.status`: Report whether the hook is currently installed under ``target_dir``.
- `HookInstaller.list_available_adapters`: Names of every adapter known to this installer (sorted).
- `HookInstaller.list_supported`: Names of adapters whose ``is_supported()`` returns True (sorted).
- `HookInstaller.get`: Return the adapter registered under ``ide`` or raise :class:`KeyError`.
- `HookInstaller.install`: Install the ``ide`` hook under ``target_dir``.
- `HookInstaller.uninstall`: Uninstall the ``ide`` hook from ``target_dir``.
- `HookInstaller.status`: Report the current status of the ``ide`` hook under ``target_dir``.
- `HookInstaller.status_all`: Status of every known adapter (sorted by name).
- `default_installer`: Build the installer with the bundled adapters.

---
Fuente: código de `cortex/session/hooks/installer.py` (AST + grafo de imports internos). No se usó documentación previa.
