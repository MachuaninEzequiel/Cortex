# cortex/documenter/reconstruction.py

## Qué tiene adentro

- `ReconstructionInput(session_id, run_hooks=True)`.
- `ReconstructionOutput`: resultado inmutable (handoff sintético, diff, hooks, contradicciones, ADR suggestions, status sugerido). No escribe vault.
- `Reconstructor`: algoritmo de 8 pasos (carga spec, diff `start_commit`→HEAD, hooks, files_in_scope vs tocados, contradicciones opcionales, `AgentHandoff` sintético, status, ADRs).
- **Stateless:** no muta la Session; eso es `DocumenterPersister`.
- `run_hooks=False` en el briefing MCP para no timeout en `npm build` (comentario AppFutbol).

## Para qué sirve

Reconstruir qué pasó en una sesión a partir de git + spec + checkpoints, para que el persister escriba la nota.

## Relaciones

### Recibe de

- `SessionService` / `SessionRecord`.
- `load_spec`, `parse_name_status`, `VerificationRunner`, `suggest_adrs`, `ContradictionDetector`.
- `cortex.session.git`, `cortex.handoff`.

### Envía a

- `DocumenterPersister` (`persistence.py`).
- MCP `cortex_documenter_briefing` / `cortex_finish_session`.

---
Fuente: lectura de `cortex/documenter/reconstruction.py`. No se usó documentación previa.
