# rust/crates/cortex-mcp/src/handlers_finish.rs

## Qué tiene adentro

Mirrors de reconstrucción (spec, diff, verification, contradictions, ADR suggestions, checkpoints). Trait `FinishBackend`. `serialize_reconstruction`, `finish_session_text`, `documenter_briefing_text`.

## Para qué sirve

Tools `cortex_finish_session` y `cortex_documenter_briefing` (read-only, `run_hooks` default false).

## Relaciones

### Recibe de

- session_id/intent/reason/run_hooks.
- `FinishBackend` (prod: `NativeFinishBackend` — git diff + SessionService).
- CLI `finish` reusa `finish_session_text`.

### Envía a

- JSON ReconstructionOutput / FinishResult.

### Notas de implementación observadas en el código

`required` de hooks se deriva por nombre con default True. Briefing no persiste ni cierra sesión.
