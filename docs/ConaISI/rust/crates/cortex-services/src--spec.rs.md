# rust/crates/cortex-services/src/spec.rs

## Qué tiene adentro

`SpecCreationResult { path, session }`, `HookInput` (Hook nativo o Dict JSON), `SpecCreate` (title, goal, requirements, files_in_scope, constraints, acceptance_criteria, tags, verification_hooks, sync_vault, remember, proposal_mode, proposal_confirmed, with_tasks). `SpecService` con `create`. `normalize_hooks` (coerción + nombres duplicados). `validate_proposal`: mode ∈ {optional, required, skip}; `required` exige `proposal_confirmed`.

## Para qué sirve

Crear una Spec canónica en el vault, indexarla, abrir Session best-effort y opcionalmente recordar en episódico.

## Relaciones

### Recibe de

- Args de CLI/MCP (`cortex_create_spec` / NativeSpecBackend).
- `SemanticPort`, `EpisodicPort`, `SessionOpener`.
- Reloj `DateTime<Utc>` (explícito, igual que writers P8).

### Envía a

- `persist_note` → vault `specs/{date}_{slug}.md`.
- `semantic.index_file` (+ `sync` si `sync_vault`).
- `session_opener.open(spec_id, path, summary)` — error de open **no** bloquea la spec.
- `episodic.add` tipo `"spec"` si `remember`.

### Notas de implementación observadas en el código

Tags siempre incluyen `"spec"`; `with_tasks` añade `"tasks-required"`. Status inicial `"draft"`. Session se abre **antes** de episodic.
