# rust/crates/cortex-tutor/examples/tutor_check.rs

## Qué tiene adentro

Gate P12B-7: reproduce golden_tutor.txt byte-a-byte. JSON estilo Python: ensure_ascii=True ⇒ \uXXXX y pares sustitutos para caracteres fuera del BMP.
Archivo de 144 líneas.

## Para qué sirve

Gate P12B-7: reproduce golden_tutor.txt byte-a-byte. JSON estilo Python: ensure_ascii=True ⇒ \uXXXX y pares sustitutos para caracteres fuera del BMP.

## Relaciones

### Recibe de

- `use cortex_tutor::hint::{get_hint, ProjectState}`
- `use cortex_tutor::topics::get_all_topics`
- Contexto de crate `cortex-tutor`: cortex-workspace, content/*.txt

### Envía a

- Crate `cortex-tutor` envía hacia: cortex-cli tutor, cortex-actions learn.topic (tópicos estáticos)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tutor/examples/tutor_check.rs`.
