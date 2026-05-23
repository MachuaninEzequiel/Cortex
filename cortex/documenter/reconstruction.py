"""cortex.documenter.reconstruction — Documenter reconstruction algorithm.

Implements the 8-step algorithm described in
``docs/pluggable-middle/ARQUITECTURA-PLUGGABLE-MIDDLE.md`` §7.2.
Given a :class:`SessionRecord` (typically an OPEN one about to be closed
by ``cortex finish-session``) the :class:`Reconstructor` synthesizes a
:class:`AgentHandoff`, runs the spec's verification hooks, cross-checks
the diff against the spec, and produces a :class:`ReconstructionOutput`
that the :class:`DocumenterPersister` (Phase 01 / T1.5) consumes to write
the session note.

The reconstructor is **stateless** — every call rebuilds the snapshot
fresh from disk + git. It does not mutate the Session; only the
persister (T1.5) closes it.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from cortex.documenter.adr_evaluator import ADRSuggestion, suggest_adrs
from cortex.documenter.contradiction_detector import (
    ContradictionDetector,
    ContradictionFinding,
    NoOpContradictionDetector,
)
from cortex.documenter.diff_parser import DiffEntry, parse_name_status
from cortex.documenter.spec_loader import LoadedSpec, load_spec
from cortex.handoff import AgentHandoff, ArtifactProduced
from cortex.session import git as git_module
from cortex.session.models import (
    Checkpoint,
    SessionRecord,
    SessionStatus,
    VerificationHookResult,
)
from cortex.session.service import SessionService
from cortex.session.verification import VerificationRunner

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Input / output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReconstructionInput:
    """What the reconstructor needs from the caller.

    Attributes:
        session_id: The session to reconstruct.
        run_hooks:  When True (default), STEP 3 of the algorithm executes the
            spec's ``verification_hooks`` via the :class:`VerificationRunner`.
            Set to False when the caller only needs the reconstruction context
            (checkpoints, diff, scope analysis) and wants to skip potentially
            slow hooks (npm build, integration tests, etc.). The
            ``/cortex-documenter`` briefing flow uses ``run_hooks=False`` to
            avoid timing out on heavy hooks — see AppFutbol Fase 3 incident
            (docs/incidents/2026-05-22_appfutbol-mcp-duplicate-loop/).
    """

    session_id: str
    run_hooks: bool = True


@dataclass(frozen=True)
class ReconstructionOutput:
    """Complete, immutable result of one reconstruction pass.

    The persister consumes this verbatim to write the session note and
    any ADRs. Nothing in here is side-effecting — building this object
    does not touch the vault or the active pointer.
    """

    session_id: str
    handoff: AgentHandoff
    spec: LoadedSpec
    session_record: SessionRecord
    diff_text: str
    diff_entries: list[DiffEntry]
    files_touched: list[Path]
    in_scope_files: list[Path]
    out_of_scope_files: list[Path]
    unimplemented_files: list[Path]
    verification_results: list[VerificationHookResult]
    contradictions: list[ContradictionFinding] = field(default_factory=list)
    suggested_status: SessionStatus = SessionStatus.HANDOFF
    suggested_adrs: list[ADRSuggestion] = field(default_factory=list)
    raw_checkpoints: list[Checkpoint] = field(default_factory=list)
    end_commit: str = ""
    # ``True`` when the session was opened without a usable git repository
    # (``session_record.is_gitless``). In that mode ``diff_text`` is empty
    # and ``files_touched`` is derived from ``Checkpoint.artifacts_touched``
    # instead of the git index. The persister surfaces this in the session
    # note so the user is aware of the reduced fidelity.
    gitless: bool = False
    # File provenance (Phase 09.A+ / May 2026): split of ``files_touched``
    # by source so the documenter / persister / skill can mark which
    # files are objectively verified by git vs only declared by agent
    # checkpoints. A file present in BOTH lists means the diff and the
    # checkpoint agree (highest confidence). A file in ``files_declared_only``
    # is one the agent claimed to touch but wasn't found in the diff —
    # typically because it was created/modified but not committed yet.
    # In gitless mode every file lives in ``files_declared_only`` and
    # ``files_verified_by_git`` is empty.
    files_verified_by_git: list[Path] = field(default_factory=list)
    files_declared_only: list[Path] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Reconstructor
# ---------------------------------------------------------------------------


class Reconstructor:
    """Orchestrator of the 8-step reconstruction algorithm.

    Dependencies are injected so the algorithm can be exercised
    headlessly (CLI), inside the MCP server (where contradiction
    detection can be backed by ``cortex_search``), or in tests with
    real fixtures.
    """

    def __init__(
        self,
        session_service: SessionService,
        verification_runner: VerificationRunner,
        repo_root: Path,
        contradiction_detector: ContradictionDetector | None = None,
    ) -> None:
        self._sessions = session_service
        self._verifier = verification_runner
        self._repo_root = Path(repo_root)
        self._contradictions: ContradictionDetector = (
            contradiction_detector or NoOpContradictionDetector()
        )

    def reconstruct(self, payload: ReconstructionInput) -> ReconstructionOutput:
        """Run the 8 steps and return a :class:`ReconstructionOutput`.

        Raises :class:`cortex.session.errors.SessionNotFound` if the id
        does not resolve. Step-level failures (missing spec file, git
        errors, hook crashes) are surfaced as fields on the output, not
        as exceptions — the persister decides how to communicate them.
        """
        # STEP 1: load context
        session = self._sessions.get(payload.session_id)
        spec = load_spec(self._resolve_spec_path(session.spec_path))
        checkpoints = list(session.checkpoints)

        # STEP 2: compute observable diff
        #
        # Gitless sessions (``session.is_gitless``) cannot use git for
        # ground truth — the diff is empty and ``files_touched`` is
        # derived from ``Checkpoint.artifacts_touched`` instead. This is
        # lower fidelity than a real diff (a checkpoint can claim a
        # touch that didn't happen, and there's no way to verify) but
        # it keeps the workflow functional in workspaces without git.
        if session.is_gitless:
            diff_text = ""
            diff_entries = []
            end_commit = session.end_commit or session.start_commit
            files_verified_by_git: list[Path] = []
            files_declared_only = _files_touched_from_checkpoints(checkpoints)
            files_touched = list(files_declared_only)
        else:
            end_ref = session.end_commit if session.end_commit else "HEAD"
            diff_text = git_module.diff(session.start_commit, end_ref, self._repo_root)
            name_status = git_module.diff_name_status(
                session.start_commit, end_ref, self._repo_root
            )
            diff_entries = parse_name_status(name_status)
            end_commit = (
                session.end_commit
                if session.end_commit
                else git_module.get_head_commit(self._repo_root)
            )
            # Phase 09.A+ / May 2026: combine git diff with checkpoint
            # ``artifacts_touched``. The diff is ground truth (verified
            # changes) but it MISSES files the agent created/modified
            # without committing yet. Checkpoint claims cover that gap
            # at a lower confidence level. Keeping both lists separate
            # lets the documenter render the difference faithfully —
            # the agent that "did the work" gets credit for declared
            # touches, but the renderer marks them as such.
            files_verified_by_git = [e.path for e in diff_entries]
            verified_keys = {p.as_posix() for p in files_verified_by_git}
            declared_all = _files_touched_from_checkpoints(checkpoints)
            files_declared_only = [
                p for p in declared_all if p.as_posix() not in verified_keys
            ]
            # Union preserving order: verified first, then declared-only.
            files_touched = [*files_verified_by_git, *files_declared_only]

        # STEP 3: run verification hooks (skippable by the caller)
        if not payload.run_hooks:
            logger.info(
                "Session %s: run_hooks=False; skipping verification hook execution.",
                session.session_id,
            )
            verification_results = []
        elif spec.verification_hooks:
            verification_results = self._verifier.run_all(spec.verification_hooks)
        else:
            logger.warning(
                "Session %s: spec has no verification_hooks; skipping verification.",
                session.session_id,
            )
            verification_results = []

        # STEP 4: cross-check against spec
        in_scope, out_of_scope, unimplemented = _scope_cross_check(
            files_touched, spec.files_in_scope
        )

        # STEP 5: detect contradictions
        contradictions = self._contradictions.find_contradictions(
            spec_summary=spec.goal or spec.title,
            diff_text=diff_text,
            checkpoints=checkpoints,
        )

        # STEP 6: build synthetic AgentHandoff
        suggested_adrs = suggest_adrs(checkpoints, diff_text)
        handoff = _build_handoff(
            spec=spec,
            diff_entries=diff_entries,
            verification_results=verification_results,
            checkpoints=checkpoints,
            in_scope=in_scope,
            out_of_scope=out_of_scope,
            unimplemented=unimplemented,
            suggested_adrs=suggested_adrs,
            suggested_status=_decide_status(
                verification_results=verification_results,
                unimplemented=unimplemented,
            ),
        )

        # STEP 7: pick suggested final status
        suggested_status = _decide_status(
            verification_results=verification_results,
            unimplemented=unimplemented,
        )

        # STEP 8: package and return
        return ReconstructionOutput(
            session_id=session.session_id,
            handoff=handoff,
            spec=spec,
            session_record=session,
            diff_text=diff_text,
            diff_entries=diff_entries,
            files_touched=files_touched,
            in_scope_files=in_scope,
            out_of_scope_files=out_of_scope,
            unimplemented_files=unimplemented,
            verification_results=verification_results,
            contradictions=contradictions,
            suggested_status=suggested_status,
            suggested_adrs=suggested_adrs,
            raw_checkpoints=checkpoints,
            end_commit=end_commit,
            gitless=session.is_gitless,
            files_verified_by_git=files_verified_by_git,
            files_declared_only=files_declared_only,
        )

    # ── Helpers ────────────────────────────────────────────────────

    def _resolve_spec_path(self, spec_path: Path) -> Path:
        """Resolve ``spec_path`` against ``repo_root`` when relative."""
        if spec_path.is_absolute():
            return spec_path
        return (self._repo_root / spec_path).resolve()


# ---------------------------------------------------------------------------
# Pure helpers (module level so they're trivially testable)
# ---------------------------------------------------------------------------


def _files_touched_from_checkpoints(checkpoints: Sequence[Checkpoint]) -> list[Path]:
    """Aggregate :attr:`Checkpoint.artifacts_touched` across all checkpoints.

    Used by gitless sessions where the diff isn't available. Preserves
    first-seen order and deduplicates by POSIX path so the same file
    touched in two checkpoints only appears once.
    """
    seen: set[str] = set()
    ordered: list[Path] = []
    for cp in checkpoints:
        for raw in cp.artifacts_touched:
            path = Path(raw)
            key = path.as_posix()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(path)
    return ordered


def _scope_cross_check(
    files_touched: Sequence[Path],
    files_in_scope: Sequence[Path],
) -> tuple[list[Path], list[Path], list[Path]]:
    """Split ``files_touched`` against the spec's ``files_in_scope``.

    Returns ``(in_scope, out_of_scope, unimplemented)``.
    Comparison uses ``as_posix()`` so Windows backslashes don't trip
    equality of otherwise identical paths.
    """
    scope_set = {Path(p).as_posix() for p in files_in_scope}
    touched_set = {p.as_posix() for p in files_touched}

    in_scope = [p for p in files_touched if p.as_posix() in scope_set]
    out_of_scope = [p for p in files_touched if p.as_posix() not in scope_set]
    unimplemented = [Path(p) for p in files_in_scope if Path(p).as_posix() not in touched_set]
    return in_scope, out_of_scope, unimplemented


def _decide_status(
    *,
    verification_results: Sequence[VerificationHookResult],
    unimplemented: Sequence[Path],
) -> SessionStatus:
    """Pick the suggested final status (CLOSED or HANDOFF).

    - All required hooks passed AND no unimplemented files → CLOSED.
    - Otherwise → HANDOFF.

    ABANDONED is never auto-suggested; the user must opt in via the
    ``--abandon`` CLI flag.
    """
    required_passed = all(r.passed for r in verification_results if _is_required(r))
    if required_passed and not unimplemented:
        return SessionStatus.CLOSED
    return SessionStatus.HANDOFF


HandoffAction = Literal["created", "modified", "deleted", "renamed"]

_ACTION_MAP: dict[str, HandoffAction] = {
    # Maps :class:`cortex.documenter.diff_parser.DiffAction` values to the
    # vocabulary accepted by :class:`cortex.handoff.ArtifactProduced`.
    "added": "created",
    "modified": "modified",
    "deleted": "deleted",
    "renamed": "renamed",
    "copied": "created",
}


def _diff_action_to_handoff(action: str) -> HandoffAction:
    """Translate a diff action to the AgentHandoff vocabulary."""
    return _ACTION_MAP.get(action, "modified")


def _is_required(result: VerificationHookResult) -> bool:
    """Hook results don't carry the ``required`` flag; we infer from name.

    Phase 04 may add a ``required`` field to ``VerificationHookResult``.
    Until then we treat every result as required — anything else would
    silently lower the bar.
    """
    return True


def _build_handoff(
    *,
    spec: LoadedSpec,
    diff_entries: Sequence[DiffEntry],
    verification_results: Sequence[VerificationHookResult],
    checkpoints: Sequence[Checkpoint],
    in_scope: Sequence[Path],
    out_of_scope: Sequence[Path],
    unimplemented: Sequence[Path],
    suggested_adrs: Sequence[ADRSuggestion],
    suggested_status: SessionStatus,
) -> AgentHandoff:
    """Assemble the synthetic :class:`AgentHandoff` (step 6).

    The handoff mirrors the contract used by SDDwork in legacy mode so
    that the persister (T1.5) and the documenter subagent don't need
    two code paths for the two flows.
    """
    verified_claims: list[str] = []
    if in_scope:
        verified_claims.append(f"Modified {len(in_scope)} file(s) inside spec scope")
    for r in verification_results:
        if r.passed:
            verified_claims.append(f"verification hook '{r.name}' passed")

    unverified_claims: list[str] = []
    for r in verification_results:
        if not r.passed:
            unverified_claims.append(
                f"verification hook '{r.name}' did not pass (exit={r.exit_code})"
            )
    for ac in spec.acceptance_criteria:
        unverified_claims.append(f"acceptance criterion: {ac}")

    artifacts = [
        ArtifactProduced(
            path=entry.path.as_posix(),
            action=_diff_action_to_handoff(entry.action),
            lines_changed=0,
            lines_added=0,
        )
        for entry in diff_entries
    ]

    context_for_next: list[str] = [cp.note for cp in checkpoints if cp.note]
    if out_of_scope:
        context_for_next.append("Scope drift: " + ", ".join(p.as_posix() for p in out_of_scope))
    if unimplemented:
        context_for_next.append(
            "Unimplemented files in scope: " + ", ".join(p.as_posix() for p in unimplemented)
        )

    handoff_status: Literal["complete", "partial", "blocked"]
    if suggested_status is SessionStatus.CLOSED:
        handoff_status = "complete"
    elif suggested_status is SessionStatus.HANDOFF:
        handoff_status = "partial"
    else:  # ABANDONED — never auto-suggested but handled for completeness
        handoff_status = "blocked"

    return AgentHandoff(
        agent="cortex-documenter",
        status=handoff_status,
        verified_claims=verified_claims,
        unverified_claims=unverified_claims,
        artifacts_produced=artifacts,
        context_for_next=context_for_next,
        suggested_adr=bool(suggested_adrs),
        suggested_adr_reason=("; ".join(s.title for s in suggested_adrs) if suggested_adrs else ""),
        suggested_context_terms=[],
    )


__all__ = [
    "ReconstructionInput",
    "ReconstructionOutput",
    "Reconstructor",
]
