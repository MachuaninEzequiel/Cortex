# rust/crates/cortex-cli/tests/t6b_session_watch.rs

## Qué tiene adentro

`session watch`/`tui` en stdout pipe: un snapshot ratatui, rc 0. IDs coinciden con fixture; vacío → `"(no sessions on disk)"`. Sin mocks.

## Para qué sirve

Gate CIERRE T6-b.

## Relaciones

### Recibe de

- SessionService + cortex-tui snapshot.

### Envía a

- cargo test.

### Notas de implementación observadas en el código

Integración con binario real + tmp.
