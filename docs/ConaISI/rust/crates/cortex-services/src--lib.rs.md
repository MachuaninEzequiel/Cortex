# rust/crates/cortex-services/src/lib.rs

## Qué tiene adentro

Módulos `migration`, `note`, `spec`. Struct `EpisodicRequest`. Traits `EpisodicPort`, `SemanticPort`, `SessionOpener` (con impl para `SessionService` de cortex-app). Función interna `persist_note` + `fingerprint` leyendo `fingerprint:` del frontmatter.

## Para qué sirve

Capa de servicios: orquesta writer canónico + índices + sesión sin duplicar templates.

## Relaciones

### Recibe de

- `cortex_setup::writers::{NoteRequest, build_note}`.
- `cortex_app::session::{SessionRecord, SessionService}`.

### Envía a

- Disco (nota markdown en el vault).
- Consumidores CLI/MCP.

### Notas de implementación observadas en el código

Si el path destino existe y el fingerprint coincide → OK idempotente. Si existe con contenido distinto → error `"Document already exists with different content: ... Pass overwrite=True..."`.
