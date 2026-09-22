# rust/crates/cortex-setup/examples/note_dump.rs

## Qué tiene adentro

Imprime nota construida para un caso de `inputs.json` writers. Uso: `cargo run -p cortex-setup --example note_dump -- <case>`.

## Para qué sirve

Debug de paridad writers.

## Relaciones

### Recibe de

- golden_setup/writers/inputs.json + build_note.

### Envía a

- stdout markdown.

### Notas de implementación observadas en el código

Reloj del fixture.
