# rust/crates/cortex-services/src/note.rs

## Qué tiene adentro

`NoteCreate` (title, spec_summary, changes, files, decisions, next_steps, tags, handoff, blockers, verified/unverified, skills, telemetry, tasks, gitless, phase_line, evidence_by_phase). `NoteService::create` (uuid4 hex[:12]) y `create_with_id` determinista. Alias `SessionNoteService`.

## Para qué sirve

Persistir nota de sesión (`doc_type=session`) con contrato transaccional: si index/sync/episodic falla, **borra el archivo** y propaga el error (`file on disk ⇒ indexed in memory`).

## Relaciones

### Recibe de

- CLI/MCP save_session / documenter.
- Puertos semántico y episódico.

### Envía a

- Vault `sessions/{session_id}_{slug}.md` vía writer.
- Índice semántico y memoria episódica (`memory_type: "session"`).

### Notas de implementación observadas en el código

`remember` default True en `basic()`. Status `"handoff"` o `"completed"`. Tag `"handoff"` si corresponde. `uuid` v4 simple, 12 hex chars.
