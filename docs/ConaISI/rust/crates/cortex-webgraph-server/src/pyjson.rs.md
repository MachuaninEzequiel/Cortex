# rust/crates/cortex-webgraph-server/src/pyjson.rs

## Qué tiene adentro

Serializador JSON compatible byte-a-byte con `json.dumps` de Python y `flask.jsonify` (Flask 3.x).  Modos soportados (ambos verificados contra el runtime instalado): - **COMPACT** (`jsonify`): `separators=(",", ":")`, `sort_keys=True`, `ensure_ascii=True`, `\n` final agregado por Flask. - **PYTHON_DEFAULT** (`json.dumps(..., sort_keys=True)` del fingerprint): separadores `(", ", ": ")`.  Escapes ensure_ascii: `"`, `\\`, `\n`, `\r`, `\t`, `\b`, `\f`, controles `<0x20` como `\uXXXX`, todo `>=0x80` como `\uXXXX` (lowercase; pares sustitutos para >0xFFFF) — idéntico a CPython.
Archivo de 158 líneas.
Símbolos públicos observados:
- `pub enum Mode`
- `pub fn dumps(value: &Value, mode: Mode, sort_keys: bool) -> String`
Tests en el mismo archivo: `compact_sorted_ascii`, `python_default_separators`, `escapes_controles_y_surrogates`

## Para qué sirve

Serializador JSON compatible byte-a-byte con `json.dumps` de Python y `flask.jsonify` (Flask 3.x).  Modos soportados (ambos verificados contra el runtime instalado): - **COMPACT** (`jsonify`): `separators=(",", ":")`, `sort_keys=True`, `ensure_ascii=True`, `\n` final agregado por Flask. - **PYTHON_DEFAULT** (`json.dumps(..., sort_keys=True)` del fingerprint): separadores `(", ", ": ")`.  Escapes ensure_ascii: `"`, `\\`, `\n`, `\r`, `\t`, `\b`, `\f`, controles `<0x20` como `\uXXXX`, todo `>=0x80` como `\uXXXX` (lowercase; pares sustitutos para >0xFFFF) — idéntico a CPython.

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-webgraph-server`: cortex-core, cortex-app, cortex-workspace, cortex-setup

### Envía a

- Crate `cortex-webgraph-server` envía hacia: HTTP axum, cortex-cli webgraph, brain webgraph.serve

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-webgraph-server/src/pyjson.rs`.
El crate/archivo declara `forbid(unsafe_code)`.
