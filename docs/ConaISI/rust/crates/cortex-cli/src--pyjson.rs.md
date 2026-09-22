# rust/crates/cortex-cli/src/pyjson.rs

## Qué tiene adentro

Árbol `PyVal` / `Num` (no usa `serde_json::Value` porque Object es BTreeMap). `stdlib_dumps_indent2`, `stdlib_dumps_compact_array`, `pydantic_dumps_indent2`, `format_float`, `write_escaped` (ensure_ascii con pares sustitutos).

## Para qué sirve

JSON de `--json` idéntico a `json.dumps` / pydantic del CLI Python.

## Relaciones

### Recibe de

- Comandos session/org/promote/webgraph/etc. que emiten JSON.

### Envía a

- stdout.

### Notas de implementación observadas en el código

`#![forbid(unsafe_code)]`. preserve_order a nivel workspace se evitó para no romper crates gated.
