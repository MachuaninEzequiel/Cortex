# cortex/session/quality_gates.py

## Qué tiene adentro

- **Ruta de código:** `cortex/session/quality_gates.py` (203 líneas).
- **Módulo Python:** `cortex.session.quality_gates`.
- **Docstring del módulo:** cortex.session.quality_gates — Two-stage review of subagent checkpoints.
- **Clases definidas:**
  - `ReviewVerdict`
    - Outcome of a two-stage checkpoint review.
- **Funciones de módulo:**
  - `review_checkpoint(checkpoint, spec)` — Run the two-stage review on a single subagent checkpoint.
  - `_is_process_artifact(path)` — True when ``path`` is a Cortex-canonical artifact, not an in-scope file.
  - `_stage_1_spec_compliance(checkpoint, spec)` — Stage 1: artifacts within scope + at least one signal of progress.
  - `_stage_2_quality(checkpoint)` — Stage 2: no placeholders + non-trivial test/build claims.
- **Constantes / símbolos de módulo:** `_PLACEHOLDER_TOKENS`, `_TEST_CLAIM_KEYWORDS`, `_MIN_NON_TRIVIAL_CLAIM_LEN`, `_PROCESS_ARTIFACT_PREFIXES`, `__all__`

## Para qué sirve

cortex.session.quality_gates — Two-stage review of subagent checkpoints.

Pure functions that validate a :class:`Checkpoint` emitted by a subagent
against the active :class:`LoadedSpec`. Exposed as the MCP tool
``cortex_review_checkpoint`` (registered in ``cortex/mcp/server.py``)
and invoked by the SDDwork orchestrator after each subagent checkpoint
in Deep Track.

Stage 1 — Spec compliance:
    * ``artifacts_touched`` ⊆ ``spec.files_in_scope`` (empty scope is a
      wildcard, used by docs-only or research tasks).
    * ``verified_claims`` is non-empty OR ``artifacts_touched`` is
      non-empty (a checkpoint must report *something*).

Stage 2 — Quality:
    * No placeholder tokens (``TBD``, ``FIXME``, ``???``) anywhere in
      ``note``.
    * If any ``verified_claims`` mention tests/build/lint/check/CI, at
      least one verified claim must be non-trivial (> 10 chars). A bare
      ``"tests"`` is not evidence.

The function returns a :class:`ReviewVerdict` whose ``action`` is one of
three literals so the orchestrator branches unambiguously:

    * ``"accept"``      — proceed to the next step.
    * ``"redelegate"``  — repeat the delegation with corrected guidance
                          (spec compliance failed).
    * ``"warn"``        — proceed but propagate ``reason`` into the
                          ``unverified_claims`` of the orchestrator's
                          own next checkpoint (quality failed but spec
                          compliance passed).

Conceptually descends from the deleted
``cortex.autopilot.delegation.DelegationEngine`` (see
``docs/pluggable-middle/fases/_internal/autopilot-audit.md`` §11.2).

## Relaciones

### Recibe de

- `cortex.session.models` (Checkpoint)
- Dependencias externas/stdlib: `__future__`, `dataclasses`, `pathlib`, `typing`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 203.
Docstrings de símbolos públicos:
- `review_checkpoint`: Run the two-stage review on a single subagent checkpoint.

---
Fuente: código de `cortex/session/quality_gates.py` (AST + grafo de imports internos). No se usó documentación previa.
