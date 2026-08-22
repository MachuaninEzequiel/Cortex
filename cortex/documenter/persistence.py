"""cortex.documenter.persistence — Persist a ReconstructionOutput.

Given the read-only :class:`ReconstructionOutput` produced by the
:class:`Reconstructor`, the :class:`DocumenterPersister` writes the
artefacts to disk and closes the session:

1. Build a ``SessionData`` and persist it via :class:`NoteService`.
2. For every :class:`ADRSuggestion`, build an ``ADRData`` and persist it
   via :func:`write_adr_note`.
3. Update CONTEXT.md if applicable (deferred — Phase 01 leaves this as
   a no-op and Phase 04 will integrate the glossary loop).
4. Close the underlying :class:`SessionRecord` via :class:`SessionService`
   with the documenter's verdict.

The persister is **idempotent**: calling ``finalize`` on an already-
closed session returns the existing artefact paths without re-writing.

Phase 08 / T8.3 added a *self-review* pass over the about-to-persist
draft. It is **informational only** — never blocks persistence. When
the scan finds placeholders, unreferenced files, or success claims
without evidence, the resulting warnings are appended to the note's
``next_steps`` (prefixed ``[self-review]``) and the ``auto-draft`` tag
is attached so consumers can filter on it. Blocking here would create
infinite loops in the agentic flow; we surface, not gate.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from cortex.documentation.data import ADRData
from cortex.documentation.writers import write_adr_note
from cortex.documenter.adr_evaluator import ADRSuggestion
from cortex.documenter.reconstruction import ReconstructionOutput
from cortex.services.note_service import NoteService
from cortex.session.models import SessionStatus, Task, TaskStatus
from cortex.session.service import SessionService

logger = logging.getLogger(__name__)

# Tokens scanned in the draft body. The set is more permissive than the
# checkpoint-level scan in ``cortex.session.quality_gates`` because the
# documenter's final draft is the user-visible artefact: any leftover
# placeholder here is genuinely confusing for the reader, even ones
# (like ``todo``) that are sometimes legitimate inside checkpoints.
_PLACEHOLDER_TOKENS: frozenset[str] = frozenset(
    {"tbd", "todo", "fixme", "xxx", "???", "fill me", "[pendiente]"}
)

# Substrings that imply the draft is claiming an objective verification
# happened. If any of these appear but no verification hook actually
# passed, we warn — the claim is hollow.
_SUCCESS_CLAIM_PATTERNS: frozenset[str] = frozenset(
    {
        "tests pass",
        "test passed",
        "tests passed",
        "build exitoso",
        "build successful",
        "linter clean",
        "lint passed",
        "checks pass",
        "ci passed",
    }
)

_SELF_REVIEW_TAG = "auto-draft"


@dataclass(frozen=True)
class FinishOverrides:
    """Hook point for Phase 04's interactive mode.

    Phase 01 always uses the auto-suggested values verbatim; Phase 04
    will populate the fields below when the user edits the draft in
    ``cortex finish-session --interactive``.
    """

    approved_adr_indices: list[int] | None = None  # None = approve all
    edited_note_title: str | None = None
    edited_note_body: str | None = None
    forced_status: SessionStatus | None = None


@dataclass(frozen=True)
class FinishSessionResult:
    """What ``finalize`` reports back to the caller."""

    session_id: str
    session_note_path: Path | None
    adrs_created: list[Path] = field(default_factory=list)
    final_status: SessionStatus = SessionStatus.HANDOFF
    summary: str = ""
    already_closed: bool = False


# ---------------------------------------------------------------------------


class _VaultPathOnly:
    """Minimal :class:`VaultLike` wrapping a bare path for canonical writers."""

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def path(self) -> Path:
        return self._root

    def index_file(self, relative_path: str) -> bool:  # noqa: ARG002
        return False


class DocumenterPersister:
    """Side-effecting closer of a reconstructed session."""

    def __init__(
        self,
        note_service: NoteService,
        session_service: SessionService,
        vault_path: Path,
    ) -> None:
        self._notes = note_service
        self._sessions = session_service
        self._vault = Path(vault_path)

    # ── Public API ─────────────────────────────────────────────────

    def finalize(
        self,
        reconstruction: ReconstructionOutput,
        overrides: FinishOverrides | None = None,
    ) -> FinishSessionResult:
        """Persist artefacts and close the session.

        Idempotent: if the underlying session has already been closed by
        an earlier finalize() call, returns the prior paths without
        writing anything. Use the SessionService directly to re-open a
        new session for follow-up work.
        """
        overrides = overrides or FinishOverrides()
        record = self._sessions.get(reconstruction.session_id)
        if record.status is not SessionStatus.OPEN:
            logger.info(
                "Session %s is already in status %s; returning existing artefacts.",
                record.session_id,
                record.status.value,
            )
            return FinishSessionResult(
                session_id=record.session_id,
                session_note_path=record.session_note_path,
                adrs_created=list(record.adrs_created),
                final_status=record.status,
                summary="(session was already closed; no changes made)",
                already_closed=True,
            )

        final_status = overrides.forced_status or reconstruction.suggested_status

        note_path = self._write_session_note(reconstruction, final_status, overrides)
        adrs = self._write_adrs(reconstruction.suggested_adrs, overrides)
        self._sessions.close(
            record.session_id,
            status=final_status,
            documenter_decision=final_status,
            session_note_path=note_path,
            adrs_created=adrs,
        )
        summary = self._build_summary(reconstruction, final_status, note_path, adrs)
        logger.info(
            "Closed session %s as %s; note=%s; adrs=%d",
            record.session_id,
            final_status.value,
            note_path,
            len(adrs),
        )
        return FinishSessionResult(
            session_id=record.session_id,
            session_note_path=note_path,
            adrs_created=adrs,
            final_status=final_status,
            summary=summary,
            already_closed=False,
        )

    # ── Internals ──────────────────────────────────────────────────

    def _write_session_note(
        self,
        reconstruction: ReconstructionOutput,
        final_status: SessionStatus,
        overrides: FinishOverrides,
    ) -> Path:
        spec = reconstruction.spec
        is_handoff = final_status is SessionStatus.HANDOFF
        title = overrides.edited_note_title or (spec.title or reconstruction.session_id)
        spec_summary = spec.goal or spec.title or ""

        changes_made = [
            f"{entry.action}: {entry.path.as_posix()}" for entry in reconstruction.diff_entries
        ]
        # Phase 09.A+ / May 2026: surface file provenance in the session
        # note. A leading marker tells the reader whether the file was
        # objectively verified by ``git diff`` (✓) or only declared by
        # an agent checkpoint without a matching commit (◌).
        verified_keys = {p.as_posix() for p in reconstruction.files_verified_by_git}
        files_touched = []
        for p in reconstruction.files_touched:
            posix = p.as_posix()
            marker = "✓" if posix in verified_keys else "◌"
            files_touched.append(f"{marker} {posix}")
        # If any file is declared-only, surface that in next_steps so it's
        # impossible to miss when reviewing the note.
        declared_only_paths = [p.as_posix() for p in reconstruction.files_declared_only]
        key_decisions = [cp.note for cp in reconstruction.raw_checkpoints if cp.note]
        if overrides.edited_note_body:
            # Phase 04: in interactive mode the user's edited body is
            # surfaced verbatim at the top of the decisions section so the
            # template still renders consistently with the auto path.
            key_decisions = [overrides.edited_note_body, *key_decisions]

        next_steps: list[str] = []
        if reconstruction.unimplemented_files:
            next_steps.extend(
                f"Implement: {p.as_posix()}" for p in reconstruction.unimplemented_files
            )
        if reconstruction.out_of_scope_files:
            next_steps.append(
                "Decide if scope drift is intentional: "
                + ", ".join(p.as_posix() for p in reconstruction.out_of_scope_files)
            )
        if declared_only_paths:
            # Files the agent claimed to touch but the diff didn't see —
            # almost always means they were created/modified but never
            # committed. Surface this so the user can decide whether to
            # commit them or remove the (now stale) claim.
            next_steps.append(
                "Commit (or revert) declared-only files: "
                + ", ".join(declared_only_paths)
            )

        blockers: list[str] = [
            f"{r.name} failed (exit {r.exit_code})"
            for r in reconstruction.verification_results
            if not r.passed
        ]

        tags = ["session"]
        # Tag the inferred mode for downstream RRF retrieval; the session
        # record itself also carries the canonical SessionMode.
        if reconstruction.raw_checkpoints:
            tags.append("with-checkpoints")
        else:
            tags.append("byo")
        # Gitless sessions are surfaced as a top-level tag so users can
        # filter them out of dashboards and so future doctor / retrieval
        # paths can opt to treat the note as lower-confidence.
        if reconstruction.gitless:
            tags.append("gitless")

        verified_state = list(reconstruction.handoff.verified_claims)
        unverified_claims = list(reconstruction.handoff.unverified_claims)

        # Phase 08 / T8.3: self-review the about-to-persist draft. The
        # scan is informational; warnings get appended to next_steps so
        # they remain visible in the note, and the auto-draft tag is
        # attached so consumers can filter or surface a notice in TUIs.
        draft_body = _build_draft_body_for_review(
            spec_summary=spec_summary,
            changes_made=changes_made,
            key_decisions=key_decisions,
            next_steps=next_steps,
            blockers=blockers,
            verified_state=verified_state,
            unverified_claims=unverified_claims,
        )
        warnings = self._self_review_draft(reconstruction, draft_body)
        if warnings:
            if _SELF_REVIEW_TAG not in tags:
                tags.append(_SELF_REVIEW_TAG)
            next_steps = [
                *next_steps,
                *[f"[self-review] {w}" for w in warnings],
            ]
            logger.info(
                "Self-review warnings for session %s: %s",
                reconstruction.session_id,
                warnings,
            )

        # Phase 08 / T8.5: pass task_type so session.md.j2 renders the
        # right sections per profile. Lookup chain: explicit frontmatter
        # → empty (template falls back to the full layout).
        raw_task_type = reconstruction.spec.raw_frontmatter.get("task_type")
        task_type = str(raw_task_type).strip() if raw_task_type else ""

        # Phase 09.C: task completion summary. Empty list (legacy specs
        # without ``--with-tasks``) renders nothing in the template and
        # does not affect the summary line.
        tasks_payload = _summarize_tasks(reconstruction.session_record.tasks)

        return self._notes.create(
            title=title,
            spec_summary=spec_summary,
            changes_made=changes_made,
            files_touched=files_touched,
            key_decisions=key_decisions,
            next_steps=next_steps,
            tags=tags,
            sync_vault=False,
            remember=True,
            handoff=is_handoff,
            blockers=blockers,
            verified_state=verified_state,
            unverified_claims=unverified_claims,
            suggested_skills=[],
            task_type=task_type,
            tasks=tasks_payload["tasks"],
            tasks_total=tasks_payload["total"],
            tasks_done=tasks_payload["done"],
            tasks_skipped=tasks_payload["skipped"],
            gitless=reconstruction.gitless,
        )

    @staticmethod
    def _self_review_draft(
        reconstruction: ReconstructionOutput,
        draft_body: str,
    ) -> list[str]:
        """Run quality scans on the about-to-persist draft.

        Returns a list of human-readable warnings. Empty list = clean.
        Informational only — never blocks persistence.
        """
        warnings: list[str] = []
        body_lower = draft_body.lower()

        # 1. Placeholder scan.
        found = sorted({t for t in _PLACEHOLDER_TOKENS if t in body_lower})
        if found:
            warnings.append(f"Placeholders detected in draft: {found}")

        # 2. File consistency: every touched file should be mentioned in body.
        body_paths = {p.as_posix() for p in reconstruction.files_touched}
        missing = sorted(p for p in body_paths if p not in draft_body)
        if missing:
            warnings.append(f"Files touched but not mentioned in body: {missing}")

        # 3. Evidence check: success claims require at least one passed hook.
        has_claim = any(c in body_lower for c in _SUCCESS_CLAIM_PATTERNS)
        has_verified = any(r.passed for r in reconstruction.verification_results)
        if has_claim and not has_verified:
            warnings.append("Success claim in body without any verified hook result")

        return warnings

    def _write_adrs(
        self,
        suggestions: Iterable[ADRSuggestion],
        overrides: FinishOverrides,
    ) -> list[Path]:
        approved_idx = overrides.approved_adr_indices
        adrs: list[Path] = []
        vault = _VaultPathOnly(self._vault)
        for idx, suggestion in enumerate(suggestions):
            if approved_idx is not None and idx not in approved_idx:
                continue
            data = ADRData(
                title=suggestion.title,
                tags=["adr"],
                status="proposed",
                context=suggestion.rationale,
                decision=suggestion.evidence,
                alternatives_considered=[],
                consequences="",
            )
            try:
                path = write_adr_note(data, vault=vault)
            except Exception as exc:  # pragma: no cover — defensive logging
                logger.warning(
                    "Failed to persist ADR '%s': %s",
                    suggestion.title,
                    exc,
                )
                continue
            adrs.append(path)
        return adrs

    @staticmethod
    def _build_summary(
        reconstruction: ReconstructionOutput,
        final_status: SessionStatus,
        note_path: Path,
        adrs: list[Path],
    ) -> str:
        """Compose the one-line summary returned to CLI / MCP callers."""
        diff_count = len(reconstruction.diff_entries)
        hook_count = len(reconstruction.verification_results)
        passed = sum(1 for r in reconstruction.verification_results if r.passed)
        lines = [
            f"status: {final_status.value}",
            f"diff: {diff_count} file(s)",
            f"hooks: {passed}/{hook_count} passed",
            f"adrs: {len(adrs)}",
        ]
        # Phase 09.C: task completion (only if the session opted in).
        tasks = reconstruction.session_record.tasks
        if tasks:
            done = sum(1 for t in tasks if t.status is TaskStatus.DONE)
            skipped = sum(1 for t in tasks if t.status is TaskStatus.SKIPPED)
            tasks_str = f"tasks: {done}/{len(tasks)} done"
            if skipped:
                tasks_str += f" ({skipped} skipped)"
            lines.append(tasks_str)
        lines.append(f"note: {note_path}")
        return " · ".join(lines)


def _summarize_tasks(tasks: list[Task]) -> dict[str, object]:
    """Bundle task data the way the session template expects it.

    Returns a dict with:
        - ``tasks``: list[dict] — serialised tasks (id, description, status).
        - ``total``, ``done``, ``skipped``: aggregate counts.
    """
    if not tasks:
        return {"tasks": [], "total": 0, "done": 0, "skipped": 0}
    serialised = [
        {
            "id": t.id,
            "description": t.description,
            "status": t.status.value,
        }
        for t in tasks
    ]
    return {
        "tasks": serialised,
        "total": len(tasks),
        "done": sum(1 for t in tasks if t.status is TaskStatus.DONE),
        "skipped": sum(1 for t in tasks if t.status is TaskStatus.SKIPPED),
    }


def _build_draft_body_for_review(
    *,
    spec_summary: str,
    changes_made: list[str],
    key_decisions: list[str],
    next_steps: list[str],
    blockers: list[str],
    verified_state: list[str],
    unverified_claims: list[str],
) -> str:
    """Compose a single text blob the self-review can scan.

    Rendering the actual Jinja2 template just to scan it would couple
    the persister tightly to template evolution. The fields below cover
    every place where a human-authored sentence ends up in the note's
    body — sufficient for placeholder / consistency / evidence checks.
    """
    return "\n".join(
        [
            spec_summary,
            *changes_made,
            *key_decisions,
            *next_steps,
            *blockers,
            *verified_state,
            *unverified_claims,
        ]
    )


__all__ = [
    "DocumenterPersister",
    "FinishOverrides",
    "FinishSessionResult",
]
