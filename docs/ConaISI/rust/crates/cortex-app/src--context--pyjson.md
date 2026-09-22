# src/context/pyjson.rs

## Qué tiene adentro

Emisor JSON estilo `json.dumps(indent=2, ensure_ascii=False)` de CPython.

`enum Pj { Null, Bool, U64, F64, Str, Arr, Obj(Vec<(String,Pj)>) }` — Obj preserva orden de inserción.

`redondear(x, decimales)`, `py_float` (shortest round-trip, `.0` en enteros), `dumps` indent 2, `dumps_compact`, `dumps_ascii`.

Objetos/listas vacíos inline `{}` / `[]`.

## Para qué sirve

Paridad byte del bundle `--json` y de `ValidationResult` JSON.

## Relaciones

### Recibe de

- Estructuras de `models`, `ci/result`, telemetry.

### Envía a

- Strings JSON comparados contra goldens.

### Notas de implementación observadas en el código

No usa `serde_json::to_string_pretty` (orden y floats diferirían).
