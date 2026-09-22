# cortex/autopilot/config.py

## Qué tiene adentro

- **Ruta de código:** `cortex/autopilot/config.py` (69 líneas).
- **Módulo Python:** `cortex.autopilot.config`.
- **Docstring del módulo:** cortex.autopilot.config — Optional configuration for Autopilot.
- **Clases definidas:**
  - `AutopilotConfig` (BaseModel)
    - Runtime configuration for the Autopilot module.
    - Métodos públicos/especiales: `defaults`
- **Funciones de módulo:**
  - `load_autopilot_config(layout)` — Load configuration from ``{workspace_root}/autopilot.yaml``.

## Para qué sirve

cortex.autopilot.config — Optional configuration for Autopilot.

Reads ``.cortex/autopilot.yaml`` if present; otherwise returns sensible
defaults so the module works out-of-the-box.

## Relaciones

### Recibe de

- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `yaml`, `__future__`, `pydantic`, `errors`

### Envía a

- `cortex.autopilot.doctor`
- `cortex.autopilot.policies`
- `cortex.autopilot.service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 69.
Docstrings de símbolos públicos:
- `load_autopilot_config`: Load configuration from ``{workspace_root}/autopilot.yaml``.

---
Fuente: código de `cortex/autopilot/config.py` (AST + grafo de imports internos). No se usó documentación previa.
