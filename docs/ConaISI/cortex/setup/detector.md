# cortex/setup/detector.py

## Qué tiene adentro

- **Ruta de código:** `cortex/setup/detector.py` (362 líneas).
- **Módulo Python:** `cortex.setup.detector`.
- **Docstring del módulo:** cortex.setup.detector --------------------- Auto-detects project stack, CI/CD pipelines, and environment configuration. Used by ``cortex setup`` to generate project-aware defaults.
- **Clases definidas:**
  - `StackInfo`
    - Detected project stack information.
  - `CIInfo`
    - Detected CI/CD configuration.
  - `EnvInfo`
    - Detected environment variables relevant to Cortex.
  - `ProjectContext`
    - Complete detected project context.
    - Métodos públicos/especiales: `project_type`
  - `ProjectDetector`
    - Detects the project's language, package manager, frameworks,
    - Métodos públicos/especiales: `__init__`, `detect`
    - Métodos internos: `_detect_stack`, `_read_json`, `_detect_python`, `_detect_go`, `_detect_rust`, `_detect_java`, `_detect_ruby`, `_detect_node`, `_parse_node_json`, `_detect_ci`, `_detect_env`

## Para qué sirve

cortex.setup.detector
---------------------
Auto-detects project stack, CI/CD pipelines, and environment configuration.
Used by ``cortex setup`` to generate project-aware defaults.

EPIC 4: The detector now accepts an optional ``WorkspaceLayout``
to correctly locate ``.github/workflows/`` regardless of layout mode.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `json`, `os`, `re`, `__future__`, `dataclasses`, `pathlib`, `typing`

### Envía a

- `cortex.setup`
- `cortex.setup.orchestrator`
- `cortex.setup.templates`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 362.
Docstrings de símbolos públicos:
- `ProjectContext.project_type`: High-level project type label for template selection.
- `ProjectDetector.detect`: Run all detectors and return a combined ProjectContext.

---
Fuente: código de `cortex/setup/detector.py` (AST + grafo de imports internos). No se usó documentación previa.
