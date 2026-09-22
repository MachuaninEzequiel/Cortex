# rust/crates/cortex-tutor/src/topics.rs

## Qué tiene adentro

Registro de topics — espejo de `topics/__init__.py::get_all_topics`. Los cuerpos renderizados viven en `content/topic_<slug>.txt` (captura byte-exacto de rich export_text a width=100).
Archivo de 82 líneas.
Símbolos públicos observados:
- `pub struct TopicMeta`
- `pub fn get_all_topics() -> Vec<TopicMeta>`

## Para qué sirve

Registro de topics — espejo de `topics/__init__.py::get_all_topics`. Los cuerpos renderizados viven en `content/topic_<slug>.txt` (captura byte-exacto de rich export_text a width=100).

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-tutor`: cortex-workspace, content/*.txt

### Envía a

- Crate `cortex-tutor` envía hacia: cortex-cli tutor, cortex-actions learn.topic (tópicos estáticos)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tutor/src/topics.rs`.
