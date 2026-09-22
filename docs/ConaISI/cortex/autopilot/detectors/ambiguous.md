# cortex/autopilot/detectors/ambiguous.py

## Qué tiene adentro

- **Ruta de código:** `cortex/autopilot/detectors/ambiguous.py` (63 líneas).
- **Módulo Python:** `cortex.autopilot.detectors.ambiguous`.
- **Docstring del módulo:** cortex.autopilot.detectors.ambiguous — Ambiguous-request detector.
- **Clases definidas:**
  - `AmbiguousRequestDetector`
    - Detects vague user requests that need clarification before preflight.
    - Métodos públicos/especiales: `detect`

## Para qué sirve

cortex.autopilot.detectors.ambiguous — Ambiguous-request detector.

## Relaciones

### Recibe de

- `cortex.autopilot.models` (DetectionRequest, DetectionResult)
- Dependencias externas/stdlib: `__future__`

### Envía a

- `cortex.autopilot.service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 63.

---
Fuente: código de `cortex/autopilot/detectors/ambiguous.py` (AST + grafo de imports internos). No se usó documentación previa.
