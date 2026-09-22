# cortex/autopilot/detectors/base.py

## Qué tiene adentro

- **Ruta de código:** `cortex/autopilot/detectors/base.py` (78 líneas).
- **Módulo Python:** `cortex.autopilot.detectors.base`.
- **Docstring del módulo:** cortex.autopilot.detectors.base — Detector protocol and resolution logic.
- **Clases definidas:**
  - `AutopilotDetector` (Protocol)
    - Protocol for task-type detectors.
    - Métodos públicos/especiales: `detect`
- **Funciones de módulo:**
  - `resolve_detectors(detectors, request)` — Run all *detectors* and apply the resolution rules from the contract.
- **Constantes / símbolos de módulo:** `_COMPLEXITY_RANK`

## Para qué sirve

cortex.autopilot.detectors.base — Detector protocol and resolution logic.

## Relaciones

### Recibe de

- `cortex.autopilot.models` (DetectionRequest, DetectionResult)
- Dependencias externas/stdlib: `__future__`, `typing`

### Envía a

- `cortex.autopilot.service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 78.
Docstrings de símbolos públicos:
- `resolve_detectors`: Run all *detectors* and apply the resolution rules from the contract.

---
Fuente: código de `cortex/autopilot/detectors/base.py` (AST + grafo de imports internos). No se usó documentación previa.
