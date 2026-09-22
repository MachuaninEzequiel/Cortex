# rust/crates/cortex-cli/tests/t_lea2_b_webgraph.rs

## Qué tiene adentro

webgraph doctor ×3, serve smoke ×2, error sin config. axum create_app.

## Para qué sirve

MITAD B ruta 2 webgraph.

## Relaciones

### Recibe de

- webgraph.rs + cortex-webgraph-server.

### Envía a

- cargo test.

### Notas de implementación observadas en el código

Antes serve/doctor caían en Other ⇒ exit 127.
