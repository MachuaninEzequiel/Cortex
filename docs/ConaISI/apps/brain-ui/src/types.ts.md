# apps/brain-ui/src/types.ts

## Qué tiene adentro

Interfaces TypeScript espejo de payloads Rust (`cortex-brain-app`):

- `ProjectEntry`, `ToolCall`, `ChatTurn`, `ModelEntry`
- `ChatChunkPayload`, `DownloadProgressPayload`, `ChatMessage`
- `MarkRamState` (`idle|weak_awake|awake`), `Lang`
- grafo: `GraphNode/Edge`, `ProjectGraphPayload`, `NodeHighlightEvent`, `PinnedContextNode`
- gobernanza: `SessionStatusPayload`, `DoctorCheck`, `DoctorReportPayload`
- org: `OrgKnowledgeItem`, `OrgMemoryPayload`

## Para qué sirve

Contrato de tipos entre React y commands/eventos Tauri.

## Relaciones

### Recibe de

- Forma de structs serde en `projects.rs`, `chat.rs`, `graph.rs`, `org_memory.rs`, `lib.rs`

### Envía a

- `App.tsx` y todos los components

### Notas de implementación observadas en el código

`kind`/`relation` son uniones literales alineadas a strings Rust. `ChatMessage.isStreaming` es solo UI.
