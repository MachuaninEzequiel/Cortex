# cortex/session/models.py

## Qué tiene adentro

- **Ruta de código:** `cortex/session/models.py` (460 líneas).
- **Módulo Python:** `cortex.session.models`.
- **Docstring del módulo:** cortex.session.models — Pydantic models for the Session primitive.
- **Clases definidas:**
  - `SessionStatus` (StrEnum)
    - Lifecycle states of a Session.
  - `SessionMode` (StrEnum)
    - How the *middle* of the workflow was executed.
  - `CheckpointSource` (StrEnum)
    - Authoring source for a Checkpoint.
  - `TaskStatus` (StrEnum)
    - Lifecycle states of a :class:`Task` (Pluggable Middle Phase 09.C).
  - `Task` (BaseModel)
    - A granular work item inside a Session.
    - Métodos internos: `_validate_id`, `_validate_completed_at`, `_validate_status_invariants`
  - `Checkpoint` (BaseModel)
    - A single enrichment record appended to a Session during work.
    - Métodos internos: `_validate_timestamp`
  - `VerificationHook` (BaseModel)
    - One verification hook declared in a spec.
  - `VerificationHookResult` (BaseModel)
    - Captured outcome of executing one verification hook from the spec.
    - Métodos internos: `_validate_output_size`, `_validate_run_at`
  - `SessionRecord` (BaseModel)
    - The complete record of a development Session.
    - Métodos públicos/especiales: `is_gitless`
    - Métodos internos: `_validate_session_id`, `_validate_start_commit`, `_validate_end_commit`, `_validate_opened_at`, `_validate_closed_at`, `_validate_status_invariants`
- **Funciones de módulo:**
  - `_to_utc(value, field_name)` — Reject naive datetimes; normalize any aware datetime to UTC.
  - `_truncate_output(text)` — Truncate output to ``MAX_VERIFICATION_OUTPUT_BYTES``, keeping the tail.
- **Constantes / símbolos de módulo:** `SESSION_ID_PATTERN`, `COMMIT_SHA_PATTERN`, `GITLESS_COMMIT_PLACEHOLDER`, `MAX_VERIFICATION_OUTPUT_BYTES`, `_TERMINAL_STATUSES`, `TASK_ID_PATTERN`

## Para qué sirve

cortex.session.models — Pydantic models for the Session primitive.

The Session is the core primitive of the Pluggable Middle architecture. It
tracks the lifecycle of a unit of development from the moment ``cortex-sync``
creates a spec until ``cortex-documenter`` (via ``cortex finish-session``)
persists the session note and closes the record.

See: ``docs/pluggable-middle/ARQUITECTURA-PLUGGABLE-MIDDLE.md`` §5.

Module contents:
    - :class:`SessionStatus`         — lifecycle state enum
    - :class:`SessionMode`           — execution mode enum (inferred at close)
    - :class:`CheckpointSource`      — authoring source for a checkpoint
    - :class:`Checkpoint`            — immutable in-flight enrichment record
    - :class:`VerificationHookResult` — immutable hook execution result
    - :class:`SessionRecord`         — root document persisted as YAML

Conventions:
    - All datetimes are timezone-aware and normalized to UTC at validation.
    - ``session_id`` follows ``YYYY-MM-DD_<slug>``.
    - Commit SHAs are 40-character lowercase hex (full SHA-1).
    - Paths are not constrained to relative or absolute; the service layer
      is responsible for storing them workspace-relative.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `re`, `__future__`, `datetime`, `enum`, `pathlib`, `pydantic`

### Envía a

- `cortex.autopilot.doctor`
- `cortex.autopilot.lifecycle`
- `cortex.autopilot.policies`
- `cortex.autopilot.service`
- `cortex.ci.result`
- `cortex.ci.review_session`
- `cortex.ci.session_matcher`
- `cortex.ci.validator`
- `cortex.cli.session_tui`
- `cortex.documentation.schemas.spec`
- `cortex.documenter.adr_evaluator`
- `cortex.documenter.contradiction_detector`
- `cortex.documenter.interactive`
- `cortex.documenter.persistence`
- `cortex.documenter.reconstruction`
- `cortex.documenter.spec_loader`
- `cortex.mcp.schemas`
- `cortex.services.spec_service`
- `cortex.session`
- `cortex.session.quality_gates`
- `cortex.session.service`
- `cortex.session.storage`
- `cortex.session.verification`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 460.
Docstrings de símbolos públicos:
- `SessionRecord.is_gitless`: Whether this session was opened without a usable git repository.

---
Fuente: código de `cortex/session/models.py` (AST + grafo de imports internos). No se usó documentación previa.
