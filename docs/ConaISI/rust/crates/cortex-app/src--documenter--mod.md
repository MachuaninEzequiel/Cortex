# src/documenter/mod.rs

## Qué tiene adentro

Reconstructor de 8 pasos (P5a gitless, P5b git-aware).

`ReconstructionOutput`: session_id, handoff, spec fields, diff_text/entries, files_touched/in/out/unimplemented, verification_results, suggested_status/adrs, end_commit, gitless, files_verified_by_git vs declared_only, checkpoint_notes/phase_line/evidence/close_warning (skip serde).

Funciones: `phase_line` (orden de aparición, dedup, `"grill → spec → ..."`), `evidence_by_phase` (claims verificadas), `scope_cross_check` → (in, out, unimplemented), `decide_status` (CLOSED si hooks ok y nada unimplemented y close-phase OK; si no HANDOFF), `close_phase_warning`, `reconstruct_gitless`, `reconstruct_git`.

Filtra `.cortex/session.lock` como path interno.

## Para qué sirve

Reconstruir qué pasó en la sesión para persistir la nota y decidir closed vs handoff.

## Relaciones

### Recibe de

- `SessionRecord`, `git`, `diff_parser`, `spec_loader`, `handoff`, verification results.

### Envía a

- `persister`, `interactive`, CLI finish, MCP finish backend.

### Notas de implementación observadas en el código

Orden de `files_touched` es primera aparición en checkpoints. Git timeout 10s vía `crate::git`.
