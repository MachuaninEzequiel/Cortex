# rust/crates/cortex-companion/tests/parity_cli.rs

## Qué tiene adentro

Archivo de 254 líneas.
G-B1 — paridad por construcción: el engine in-proceso produce las MISMAS salidas JSON que el binario CLI sobre el mismo fixture.  Uso: `cargo build -p cortex-cli` primero (el binario CLI se ubica en target/debug; se puede sobreescribir con la env `CORTEX_BIN`). Fixture commiteado del repo (mismo que usan los gates de doctor). Copia hermética del fixture (única por corrida) + una nota más en el vault para que la búsqueda "auth" tenga resultados semánticos. Normaliza `"elapsed_ms": <digits>` (variable real) para comparar byte a byte el payload de `next` (patrón {{ELAPSED}} de los gates).
Tests: `session_list_json_equals_cli`, `stats_then_search_same_instance_matches_cli`, `search_json_equals_cli`, `next_json_equals_cli_normalized_elapsed`, `session_current_none_without_active_session`

## Para qué sirve

G-B1 — paridad por construcción: el engine in-proceso produce las MISMAS salidas JSON que el binario CLI sobre el mismo fixture.  Uso: `cargo build -p cortex-cli` primero (el binario CLI se ubica en target/debug; se puede sobreescribir con la env `CORTEX_BIN`). Fixture commiteado del repo (mismo que usan los gates de doctor). Copia hermética del fixture (única por corrida) + una nota más en el vault para que la búsqueda "auth" tenga resultados semánticos. Normaliza `"elapsed_ms": <digits>` (variable real) para comparar byte a byte el payload de `next` (patrón {{ELAPSED}} de los gates).

## Relaciones

### Recibe de

- `use cortex_companion::engine::{Backend, InProcessBackend}`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/tests/parity_cli.rs`. 254 líneas.
