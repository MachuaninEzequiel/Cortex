# rust/crates/cortex-webgraph-server/examples/webgraph_check.rs

## Qué tiene adentro

Archivo de 449 líneas.
Verificador de paridad P12B-2 — servidor webgraph axum vs Flask.  Uso: webgraph_check <fixtures_dir> <golden_dir>  Levanta el router axum REAL sobre puerto efímero, golpea la MISMA secuencia del oráculo (`bench/parity/webgraph_golden_p12b.py`), normaliza igual ({{ROOT}}/{{TS}}/{{FP}}) y compara byte-a-byte contra `golden_webgraph.txt`.

## Para qué sirve

Verificador de paridad P12B-2 — servidor webgraph axum vs Flask.  Uso: webgraph_check <fixtures_dir> <golden_dir>  Levanta el router axum REAL sobre puerto efímero, golpea la MISMA secuencia del oráculo (`bench/parity/webgraph_golden_p12b.py`), normaliza igual ({{ROOT}}/{{TS}}/{{FP}}) y compara byte-a-byte contra `golden_webgraph.txt`.

## Relaciones

### Recibe de

- `use cortex_webgraph_server::config::WebGraphConfig`
- `use cortex_webgraph_server::pyjson`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-webgraph-server/examples/webgraph_check.rs`. 449 líneas.
