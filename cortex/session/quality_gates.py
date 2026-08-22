"""cortex.session.quality_gates — Two-stage review of subagent checkpoints.

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
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from cortex.session.models import Checkpoint

if TYPE_CHECKING:  # pragma: no cover - solo hints; rompe acople session→documenter (V9)
    from cortex.documenter.spec_loader import LoadedSpec

ReviewAction = Literal["accept", "redelegate", "warn"]

# Placeholder tokens are matched case-insensitively. The list is small on
# purpose: a permissive scan creates more false positives than it
# prevents bad checkpoints. The documenter self-review (T8.3) widens
# this set when validating the *final* note, which is the right place
# for an aggressive scan.
_PLACEHOLDER_TOKENS: tuple[str, ...] = ("tbd", "fixme", "???")

# Keywords that imply the agent is asserting an objective verification.
# We don't second-guess these substantively; we just require the claim
# carry enough text to be auditable.
_TEST_CLAIM_KEYWORDS: tuple[str, ...] = ("test", "build", "lint", "check", "ci")

_MIN_NON_TRIVIAL_CLAIM_LEN = 10


@dataclass(frozen=True)
class ReviewVerdict:
    """Outcome of a two-stage checkpoint review.

    Attributes:
        accepted:       True iff both stages passed.
        stage_1_passed: Spec compliance gate.
        stage_2_passed: Quality gate.
        reason:         Single sentence explaining the verdict (shown to
                        the orchestrator and propagated into the
                        documenter's session note if action == "warn").
        action:         What the orchestrator should do next.
    """

    accepted: bool
    stage_1_passed: bool
    stage_2_passed: bool
    reason: str
    action: ReviewAction


def review_checkpoint(checkpoint: Checkpoint, spec: LoadedSpec) -> ReviewVerdict:
    """Run the two-stage review on a single subagent checkpoint.

    Pure: no I/O, no logging, no mutation. See the module docstring for
    the exact gate definitions.
    """
    stage_1_ok, stage_1_reason = _stage_1_spec_compliance(checkpoint, spec)
    if not stage_1_ok:
        return ReviewVerdict(
            accepted=False,
            stage_1_passed=False,
            stage_2_passed=False,
            reason=stage_1_reason,
            action="redelegate",
        )

    stage_2_ok, stage_2_reason = _stage_2_quality(checkpoint)
    if not stage_2_ok:
        return ReviewVerdict(
            accepted=False,
            stage_1_passed=True,
            stage_2_passed=False,
            reason=stage_2_reason,
            action="warn",
        )

    return ReviewVerdict(
        accepted=True,
        stage_1_passed=True,
        stage_2_passed=True,
        reason="checkpoint passed both gates",
        action="accept",
    )


_PROCESS_ARTIFACT_PREFIXES: tuple[str, ...] = (
    ".cortex/vault/designs/",
    ".cortex/vault/sessions/",
    ".cortex/vault/handoffs/",
    ".cortex/vault/specs/",
    ".cortex/vault/decisions/",
    ".cortex/vault/postmortems/",
    ".cortex/vault/incidents/",
    ".cortex/vault/changelog/",
    ".cortex/vault/glossary/",
    ".cortex/vault/runbooks/",
    ".cortex/vault/architecture/",
    ".cortex/vault/hu/",
)


def _is_process_artifact(path: str) -> bool:
    """True when ``path`` is a Cortex-canonical artifact, not an in-scope file.

    Design docs, session notes, handoff YAML, ADRs, etc. are produced by the
    Cortex process itself (designer, documenter, SDDwork checkpointing). They
    live under ``.cortex/vault/<subfolder>/`` regardless of the spec being
    implemented and must NOT be treated as scope creep. Otherwise any Deep
    Track checkpoint that writes the design doc would fail Stage 1, even
    though that's the expected workflow.

    See ``docs/incidents/2026-05-22_appfutbol-mcp-duplicate-loop/``.
    """
    p = Path(path).as_posix().lstrip("./")
    return any(p.startswith(prefix) for prefix in _PROCESS_ARTIFACT_PREFIXES)


def _stage_1_spec_compliance(
    checkpoint: Checkpoint,
    spec: LoadedSpec,
) -> tuple[bool, str]:
    """Stage 1: artifacts within scope + at least one signal of progress."""
    scope = {Path(p).as_posix() for p in spec.files_in_scope}
    # Empty scope is a wildcard: research / docs-only specs may declare
    # no files_in_scope; we still let the checkpoint through.
    if scope:
        out_of_scope = [
            p
            for p in checkpoint.artifacts_touched
            if Path(p).as_posix() not in scope and not _is_process_artifact(p)
        ]
        if out_of_scope:
            return False, "files touched outside spec scope: " + ", ".join(out_of_scope)

    if not checkpoint.verified_claims and not checkpoint.artifacts_touched:
        return False, "checkpoint has neither verified_claims nor artifacts_touched"

    return True, "spec compliance OK"


def _stage_2_quality(checkpoint: Checkpoint) -> tuple[bool, str]:
    """Stage 2: no placeholders + non-trivial test/build claims."""
    note_lower = checkpoint.note.lower()
    placeholders = [t for t in _PLACEHOLDER_TOKENS if t in note_lower]
    if placeholders:
        return False, "placeholders in note: " + ", ".join(placeholders)

    mentions_tests = any(
        kw in claim.lower()
        for claim in checkpoint.verified_claims
        for kw in _TEST_CLAIM_KEYWORDS
    )
    if mentions_tests and not any(
        len(claim) > _MIN_NON_TRIVIAL_CLAIM_LEN for claim in checkpoint.verified_claims
    ):
        return False, "test/build claim too short to be auditable evidence"

    return True, "quality OK"


__all__ = ["ReviewAction", "ReviewVerdict", "review_checkpoint"]
