# rust/crates/cortex-brain/tests/spec_behavior.rs

## Qué tiene adentro

Spec conductual del brain nativo — espejo de los 13 tests de tests/unit/brain/test_brain_v1.py (LA especificación de comportamiento).  Las decisiones (routing, tiers, nunca-muta, ayuda en desconocido, banner ≤80) deben coincidir; el renderizado exacto de respuestas de servicios Python difiere por diseño (los servicios se consumen vía CLI).
Archivo de 128 líneas.
Tests en el mismo archivo: `salud_a_cortex_health`, `webgraph_a_serve`, `busqueda_extrae_query`, `pregunta_abierta_va_a_related`, `slash_quit`, `sin_match_devuelve_razon`, `no_hay_herramientas_mutadoras`, `todas_read_o_safe`, `webgraph_es_safe_action`, `propose_nunca_ejecuta_mutaciones_y_ofrece_comando`, `desconocido_ofrece_ayuda`, `banner_visible_en_80`, `doctor_responde_sin_modelo`

## Para qué sirve

Spec conductual del brain nativo — espejo de los 13 tests de tests/unit/brain/test_brain_v1.py (LA especificación de comportamiento).  Las decisiones (routing, tiers, nunca-muta, ayuda en desconocido, banner ≤80) deben coincidir; el renderizado exacto de respuestas de servicios Python difiere por diseño (los servicios se consumen vía CLI).

## Relaciones

### Recibe de

- `use cortex_brain::chat::{self, DeterministicBackend, LlmBackend}`
- `use cortex_brain::router::route_intent`
- `use cortex_brain::tools::{build_tools, dispatch, Tier}`
- Contexto de crate `cortex-brain`: cortex-branding, ureq, llama-cpp-2 (feature), CLI cortex via Command

### Envía a

- Crate `cortex-brain` envía hacia: stdout, cortex-brain-app, cortex-companion

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-brain/tests/spec_behavior.rs`.
