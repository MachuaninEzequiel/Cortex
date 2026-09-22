# cortex/session/hooks/adapters/pi.py

## Qué tiene adentro

- **Ruta de código:** `cortex/session/hooks/adapters/pi.py` (173 líneas).
- **Módulo Python:** `cortex.session.hooks.adapters.pi`.
- **Docstring del módulo:** cortex.session.hooks.adapters.pi — Pi Coding Agent hook adapter.
- **Clases definidas:**
  - `PiHookAdapter`
    - Manage the Cortex recipe block inside ``<target_dir>/justfile``.
    - Métodos públicos/especiales: `is_supported`, `install`, `uninstall`, `status`
    - Métodos internos: `_justfile_path`, `_read`, `_render`, `_strip_block`
- **Constantes / símbolos de módulo:** `JUSTFILE_RELATIVE`, `START_MARKER`, `END_MARKER`, `RECIPE_BLOCK`, `__all__`

## Para qué sirve

cortex.session.hooks.adapters.pi — Pi Coding Agent hook adapter.

Pi exposes its automation via a project-local ``justfile`` (the Pi
runtime invokes ``just <recipe>`` for routine tasks). This adapter adds
two recipes to the project ``justfile`` so Pi flows can:

    just cortex-checkpoint NOTE     — emit a checkpoint to the active session
    just cortex-finish               — run cortex finish-session

The recipes are wrapped in sentinel markers so install / uninstall are
precise even when the user has their own ``justfile`` content.

Target file: ``<target_dir>/justfile`` (created if absent).

## Relaciones

### Recibe de

- `cortex.session.hooks.installer` (HookStatus, InstallResult, UninstallResult)
- Dependencias externas/stdlib: `__future__`, `pathlib`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 173.

---
Fuente: código de `cortex/session/hooks/adapters/pi.py` (AST + grafo de imports internos). No se usó documentación previa.
