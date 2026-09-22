# rust/crates/cortex-tutor/src/engine.rs

## Qué tiene adentro

Puerto de `cortex.tutor.engine`: menú y navegación. Render plano (divergencia cosmética documentada).
Archivo de 22 líneas.
Símbolos públicos observados:
- `pub fn render_menu() -> String`
- `pub fn show_topic_by_slug(slug: &str) -> Option<String>`
- `pub type State = ProjectState`

## Para qué sirve

Puerto de `cortex.tutor.engine`: menú y navegación. Render plano (divergencia cosmética documentada).

## Relaciones

### Recibe de

- `use crate::hint::ProjectState`
- `use crate::topics::get_all_topics`
- Contexto de crate `cortex-tutor`: cortex-workspace, content/*.txt

### Envía a

- Crate `cortex-tutor` envía hacia: cortex-cli tutor, cortex-actions learn.topic (tópicos estáticos)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tutor/src/engine.rs`.
