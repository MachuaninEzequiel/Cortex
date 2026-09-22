# rust/crates/cortex-mcp/src/handlers_docs.rs

## Qué tiene adentro

`DOC_TYPES_SORTED`, `DocsError`, trait `DocsBackend`, `DesignDocInput`. Handlers: `write_design_note_text`, `write_doc_text`, `import_hu_text`, `get_hu_text`. Validación de doc_type, payload objeto, required fields por tipo, filtrado de campos desconocidos.

## Para qué sirve

Tools `cortex_write_doc`, `write_design_note_canonical`, `cortex_import_hu`, `cortex_get_hu`.

## Relaciones

### Recibe de

- Payload JSON.
- `DocsBackend` (prod: `NativeDocsBackend`).

### Envía a

- `{path, doc_type}` o errores `❌` byte-a-byte.

### Notas de implementación observadas en el código

Mensajes incluyen repr Python `'…'`.
