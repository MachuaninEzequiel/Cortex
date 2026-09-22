# src/episodic/entities.rs

## Qué tiene adentro

Puerto de `_extract_entities`. Categorías en orden: function, class, endpoint, error, config_key, dependency, variable, constant.

Cada categoría: lista de regex; `findall`; si hay varios grupos, primer no-vacío; dedup primera aparición; cap 15.

`extract_entities(content) -> Vec<(tipo, Vec<valores>)>` omite categorías vacías.

Tests contra oráculo: «función» en español no matchea; `def authenticate_user(` sí; cap 15 clases; `const MAX_RETRIES` gana grupo 1; orden class antes que error.

## Para qué sirve

Poblar flags `entity_{tipo}_{valor}` en metadata flattenada al appender.

## Relaciones

### Recibe de

- Contenido de una memoria (`NativeEpisodicStore::append` y tests).

### Envía a

- `episodic/mod.rs` (serialize_metadata / entity_filter_key).

### Notas de implementación observadas en el código

Patrones compilados en `OnceLock`. `{` de class assignment va escapado en Rust.
