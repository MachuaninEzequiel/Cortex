# cortex/autopilot/doctor.py

## Qué tiene adentro

- **Ruta de código:** `cortex/autopilot/doctor.py` (176 líneas).
- **Módulo Python:** `cortex.autopilot.doctor`.
- **Docstring del módulo:** cortex.autopilot.doctor — Diagnostic toolkit for the Autopilot installation.
- **Clases definidas:**
  - `DoctorCheck`
  - `DoctorReport`
- **Funciones de módulo:**
  - `_check_config(layout)`
  - `_check_sessions_dir(layout)`
  - `_check_adapters()`
  - `_check_hooks_installed(layout)` — Report which canonical IDE adapters are installed under the repo root.
  - `_check_last_finish(layout)`
  - `_check_service_construction(layout)` — Verify that the new AutopilotService wires correctly.
  - `run_diagnosis(project_root)` — Run all diagnostic checks and return a :class:`DoctorReport`.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.autopilot.doctor — Diagnostic toolkit for the Autopilot installation.

Phase 03 stub: the legacy checks targeting ``run/autopilot/`` state and
the old ``IndexingSessionWriter`` were removed (those files no longer
exist). T3.12 will rebuild the doctor on top of the canonical
``.cortex/sessions/`` primitive and the new ``cortex.session.hooks``
installer. Until then, this module ships a minimal set of checks that
keep ``cortex doctor`` working and surface the obvious problems:

* config: ``AutopilotConfig`` parses without raising.
* sessions_dir: ``.cortex/sessions/`` is writable.
* adapters: registry returns its known names.
* last_finish: most recent ``SessionRecord`` (if any) is in a sensible
  state.
* hooks_installed: which legacy IDE adapters left markers in the repo.

All checks are read-only.

## Relaciones

### Recibe de

- `cortex.autopilot.config` (load_autopilot_config)
- `cortex.autopilot.service` (AutopilotService)
- `cortex.session.hooks` (default_installer)
- `cortex.session.models` (SessionStatus)
- `cortex.session.storage` (SessionStorage)
- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `os`, `__future__`, `dataclasses`, `pathlib`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 176.
Docstrings de símbolos públicos:
- `run_diagnosis`: Run all diagnostic checks and return a :class:`DoctorReport`.

---
Fuente: código de `cortex/autopilot/doctor.py` (AST + grafo de imports internos). No se usó documentación previa.
