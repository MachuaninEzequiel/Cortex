# rust/crates/cortex-mcp/src/backends/spec.rs

## Qué tiene adentro

`NativeSpecBackend`. Ports `NoopSemantic` / `NoopEpisodic` (index incremental no expuesto; remember no appenda aquí). `create_spec_note` → SpecService.

## Para qué sirve

Persistir specs desde MCP.

## Relaciones

### Recibe de

- `cortex_services::spec::SpecService`.
- Vault path del proyecto.

### Envía a

- Archivo spec en vault + SpecResultMirror.

### Notas de implementación observadas en el código

El spec aparece en `cortex search` tras `cortex reindex` (deuda documentada). Memoria episódica del spec se espera vía `cortex remember`.
