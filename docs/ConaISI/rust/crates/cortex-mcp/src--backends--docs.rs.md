# rust/crates/cortex-mcp/src/backends/docs.rs

## Qué tiene adentro

`NativeDocsBackend`. Escribe notas en `vault/{doc_type}/{slug}.md` con frontmatter mínimo. `import_hu`/`get_hu` sobre `vault/handoff-units/` (comentario del archivo) / flujo HU.

## Para qué sirve

Write_doc / design / HU en producción MCP.

## Relaciones

### Recibe de

- Config vault + payload.

### Envía a

- Archivos markdown en el vault.

### Notas de implementación observadas en el código

Si existe y `overwrite=false` → error `"Document already exists"`. El header menciona NoteService; la escritura observada usa slug + frontmatter directo en este backend.
