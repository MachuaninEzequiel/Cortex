# cortex/autopilot/detectors/default.py

## Qué tiene adentro

- **Ruta de código:** `cortex/autopilot/detectors/default.py` (298 líneas).
- **Módulo Python:** `cortex.autopilot.detectors.default`.
- **Docstring del módulo:** cortex.autopilot.detectors.default — Built-in detectors.
- **Clases definidas:**
  - `CodeChangeDetector`
    - Detects tasks that involve code changes.
    - Métodos públicos/especiales: `detect`
  - `DocsOnlyDetector`
    - Detects tasks that only touch documentation.
    - Métodos públicos/especiales: `detect`
  - `QuestionOnlyDetector`
    - Detects questions that do not require any file changes.
    - Métodos públicos/especiales: `detect`
  - `SecuritySensitiveDetector`
    - Detects changes in auth, crypto, permissions, or secrets.
    - Métodos públicos/especiales: `detect`
  - `LargeRefactorDetector`
    - Detects tasks that affect many files or modules (deep track).
    - Métodos públicos/especiales: `detect`
  - `NoopDetector`
    - Fallback detector when nothing else matches.
    - Métodos públicos/especiales: `detect`

## Para qué sirve

cortex.autopilot.detectors.default — Built-in detectors.

## Relaciones

### Recibe de

- `cortex.autopilot.models` (DetectionRequest, DetectionResult)
- Dependencias externas/stdlib: `__future__`

### Envía a

- `cortex.autopilot.service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 298.

---
Fuente: código de `cortex/autopilot/detectors/default.py` (AST + grafo de imports internos). No se usó documentación previa.
