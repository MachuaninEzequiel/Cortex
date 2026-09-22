# rust/crates/cortex-companion/tests/rss_measure.rs

## Qué tiene adentro

Archivo de 82 líneas.
Medición de RSS del flujo compuesto Home→Search (G-B1 nota: re-muestrear en B4). Diagnóstico MANUAL: `cargo test -p cortex-companion --test rss_measure -- --ignored --nocapture`. NO es un gate (el binario de release es la cifra operativa); detecta fugas y documenta el objetivo ~15-25 MB. Medición adicional del binario real en PTY: ver reporte B4. Fixture del repo para paridad (misma que usa tests/parity_cli.rs). Copia hermética mínima del fixture (como tests/parity_cli.rs) para no tocar el fixture commiteado del bench.
Tests: `composite_flow_rss_print`

## Para qué sirve

Medición de RSS del flujo compuesto Home→Search (G-B1 nota: re-muestrear en B4). Diagnóstico MANUAL: `cargo test -p cortex-companion --test rss_measure -- --ignored --nocapture`. NO es un gate (el binario de release es la cifra operativa); detecta fugas y documenta el objetivo ~15-25 MB. Medición adicional del binario real en PTY: ver reporte B4. Fixture del repo para paridad (misma que usa tests/parity_cli.rs). Copia hermética mínima del fixture (como tests/parity_cli.rs) para no tocar el fixture commiteado del bench.

## Relaciones

### Recibe de

- `use cortex_companion::engine::{Backend, InProcessBackend}`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/tests/rss_measure.rs`. 82 líneas.
