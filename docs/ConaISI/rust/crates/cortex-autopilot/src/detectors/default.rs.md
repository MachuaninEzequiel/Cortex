# rust/crates/cortex-autopilot/src/detectors/default.rs

## Qué tiene adentro

Los 7 detectores built-in de `detectors/default.py`.
Archivo de 292 líneas.
Símbolos públicos observados:
- `pub const CODE_EXTS: &[&str] = &[`
- `pub const DOCS_EXTS: &[&str] = &[".md", ".rst", ".txt", ".adoc"]`
- `pub struct CodeChangeDetector`
- `pub struct DocsOnlyDetector`
- `pub struct QuestionOnlyDetector`
- `pub struct SecuritySensitiveDetector`
- `pub struct LargeRefactorDetector`
- `pub struct NoopDetector`

## Para qué sirve

Los 7 detectores built-in de `detectors/default.py`.

## Relaciones

### Recibe de

- `use crate::models::{DetectionRequest, DetectionResult}`
- Contexto de crate `cortex-autopilot`: cortex-app, cortex-enterprise, cortex-workspace, cortex-mcp

### Envía a

- Crate `cortex-autopilot` envía hacia: cortex-cli autopilot, cortex-mcp handlers

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-autopilot/src/detectors/default.rs`.
