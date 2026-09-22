# src/documenter/handoff.rs

## Qué tiene adentro

`ArtifactProduced { path, action, lines_changed, lines_added }`. `AgentHandoff { agent, status default "partial", verified/unverified claims, artifacts_produced, context_for_next, suggested_adr, suggested_adr_reason, suggested_context_terms }`.

## Para qué sirve

Handoff sintético que el reconstructor mete en `ReconstructionOutput.handoff` (`_build_handoff` Python).

## Relaciones

### Recibe de

- Reconstructor al agregar claims/artefactos de checkpoints+diff.

### Envía a

- Persister / nota de sesión / JSON de paridad.

### Notas de implementación observadas en el código

Puerto mínimo: solo los campos que produce el reconstructor, no el módulo handoff completo de workspace.
