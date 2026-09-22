# rust/crates/cortex-mcp/src/handlers_spec.rs

## Qué tiene adentro

`GOVERNANCE_VIOLATION_MESSAGE` (create_spec sin sync_ticket). `PROPOSAL_MIN_GAP_SECONDS = 2.0`. `VALID_FINISH_INTENTS`. `SpecBackend`, `SpecCreateRequest`, `SpecServerState`. `validate_proposal` (mensajes ValidationError pydantic, truncado input_value >50). `format_proposal_card`, `emit_proposal_text`, `create_spec_text`, `self_review_note_text` (TBD/TODO/FIXME/??? y claims huecos).

## Para qué sirve

Tools `cortex_emit_proposal`, `cortex_create_spec`, `cortex_self_review_note`.

## Relaciones

### Recibe de

- Estado transversal del server (`called_tools`, stamp de proposal).
- `SpecBackend` → SpecService.

### Envía a

- Markdown card de proposal / path de spec / `{warnings, passed}`.

### Notas de implementación observadas en el código

El agente **debe** terminar el turno tras emit_proposal; el server rechaza confirmaciones same-turn (gap 2s).
