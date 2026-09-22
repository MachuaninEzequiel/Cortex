# cortex/ide/adapters/pi.py

## Qué tiene adentro

- **Ruta de código:** `cortex/ide/adapters/pi.py` (328 líneas).
- **Módulo Python:** `cortex.ide.adapters.pi`.
- **Clases definidas:**
  - `PiAdapter` (IDEAdapter)
    - Métodos públicos/especiales: `name`, `display_name`, `inject_profiles`, `get_config_paths`, `detect_installation`, `inject_mcp`, `uninstall`
- **Funciones de módulo:**
  - `_default_pi_bundle_dir()` — Path to the in-tree ``cortex-pi/`` bundle.
- **Constantes / símbolos de módulo:** `_CORTEX_PI_MARKER_OPEN`, `_CORTEX_PI_MARKER_CLOSE`, `_PI_ROOT_FILES`, `_SHARED_SUBAGENTS`, `_SHARED_SKILL_ANCHORS`, `_SHARED_LEGACY_SUBAGENTS`, `_SHARED_AGENTS`

## Para qué sirve

Define PiAdapter. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- `cortex.ide.base` (IDEAdapter)
- Dependencias externas/stdlib: `logging`, `re`, `shutil`, `__future__`, `pathlib`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 328.
Docstrings de símbolos públicos:
- `PiAdapter.inject_profiles`: Inject Cortex Pi configuration.
- `PiAdapter.get_config_paths`: Pi configuration is project-local, no global config paths.
- `PiAdapter.detect_installation`: Detect if the Pi Coding Agent CLI is on PATH.
- `PiAdapter.inject_mcp`: Pi Coding Agent uses bash tools, MCP injection not required.
- `PiAdapter.uninstall`: Uninstall Pi configuration, conservador con archivos del adopter.

---
Fuente: código de `cortex/ide/adapters/pi.py` (AST + grafo de imports internos). No se usó documentación previa.
