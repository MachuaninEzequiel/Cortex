# rust/crates/cortex-setup/src/yaml.rs

## Qué tiene adentro

AST `Yaml { Null, Bool, Int, Float, Str, Seq, Map }`. Emisor PyYAML 6.0.x (resolver/representer/serializer/emitter), `best_width=80`, `dump` / `dump_with(allow_unicode)`. `python_repr_float`, `detected_tag`, `Emitter`.

## Para qué sirve

Frontmatter `yaml_dump_safe` byte-a-byte.

## Relaciones

### Recibe de

- writers (fm.model_dump).
- setup_templates org.yaml.

### Envía a

- String YAML.

### Notas de implementación observadas en el código

Claves complejas panic. Recursión/anclas fuera de dominio. Paralelo a `cortex-workspace::pyyaml` pero cubre Float/Null y frontmatter canónico.
