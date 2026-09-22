# rust/crates/cortex-setup/src/writers.rs

## Qué tiene adentro

`NoteRequest { doc_type, fields }` (`from_json`). `WriteOutcome { path, content }`. `build_note(req, vault, scope, ...)`. `normalize_pydantic_datetime`. `compute_fingerprint` local además del módulo fingerprint. Orden de campos del frontmatter de schemas Python.

## Para qué sirve

Escribir `---\n` + yaml_dump_safe + `---\n\n` + body jinja, byte-idéntico a Python.

## Relaciones

### Recibe de

- DocType, routing, jinja, slug, yaml, chrono now.
- `cortex_services::persist_note` / MCP docs.

### Envía a

- Path + contenido (el caller puede escribir disco).

### Notas de implementación observadas en el código

Contrato: mismo NoteRequest + mismo now + mismo vault ⇒ mismos bytes.
