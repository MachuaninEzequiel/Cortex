# rust/crates/cortex-setup/src/jinja.rs

## Qué tiene adentro

13 `TEMPLATE_NAMES` + `EMBEDDED_TEMPLATES` include_str de `*.md.j2`. minijinja: trim_blocks, lstrip_blocks, keep_trailing_newline, autoescape off para md.j2. `render_template`, `global_environment`.

## Para qué sirve

Cuerpos markdown canónicos de cada DocType.

## Relaciones

### Recibe de

- Archivos `cortex/documentation/templates/`.
- JSON data de writers.

### Envía a

- Body de `build_note`.

### Notas de implementación observadas en el código

Test de sincronía embebido == disco.
