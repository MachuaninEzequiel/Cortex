# rust/crates/cortex-companion/src/engine.rs

## Qué tiene adentro

Contrato `Backend` (Send+Sync): lecturas `session_current/list`, `next_actions`, `search`, `doctor`, `stats`, `session_detail`; mutaciones `close_session`, `checkpoint_session`, `approve_action`; `mark_useful`; `menu_run` (default: error con comando `cortex …` exacto, sin fingir paridad).

DTOs: `SessionSummary`, `ActionProposal`, `SearchHit`, `DoctorSummary`, `StatsSummary`.

`InProcessBackend`: `WorkspaceLayout`, `SessionService`, `NativeMemory` lazy en **dos slots** (con/sin embeddings) para no mode-lock stats→search. Acciones vía `build_default_registry` + `Scheduler` + `Runner`. Search usa `cortex_cli::memory` + `retrieval_json` / `pyjson` (paridad `--json`).

## Para qué sirve

Misma semántica que el CLI nativo, in-process, para las pantallas del Companion.

## Relaciones

### Recibe de

- `cortex_cli::{memory, memory_cmds, pyjson, paths, session_cmd}`
- `cortex_actions::{catalog, context, runner, scheduler, store}`
- `cortex_app::session`
- `cortex_workspace::WorkspaceLayout`

### Envía a

- pantallas (`app`, `effects`, `screens/*`)
- mutaciones solo detrás de `approval::run_guarded`

### Notas de implementación observadas en el código

`NativeMemory::open_without_embeddings` evita ~90 MB RSS en stats/forget. Tests de paridad en `tests/parity_cli.rs`.
