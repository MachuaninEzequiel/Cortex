"""cortex.ci.review_session — CI-owned review-session helpers (Level 3).

A review session uses the existing Session primitive verbatim. The only
new model bits live in ``cortex.session.models``:

* ``CheckpointSource.CI_BOT`` — the source value emitted by these helpers.
* ``SessionMode.CI_REVIEW`` — the mode the close-time inference picks
  when every checkpoint comes from ``CI_BOT``.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cortex.session.models import CheckpointSource, SessionRecord, SessionStatus
from cortex.session.service import SessionService


def open_review_session(
    service: SessionService,
    *,
    spec_id: str,
    base_commit: str,
    head_branch: str,
    pr_number: int | None = None,
    spec_path: Path | None = None,
) -> SessionRecord:
    """Open a fresh review session.

    The new session is **not** promoted to active — CI runs alongside
    the developer's own session and must not steal the active pointer.
    """
    # Resolve spec_path: if not supplied, fall back to a synthetic
    # ``vault/specs/<spec_id>.md`` reference. It doesn't have to exist
    # on disk — review sessions never invoke the documenter.
    if spec_path is None:
        spec_path = Path("vault/specs") / f"{spec_id}.md"

    summary = (
        f"PR #{pr_number} review"
        if pr_number is not None
        else f"Review of {head_branch}"
    )

    # We can't simply call ``service.open`` here: that sets ``start_commit``
    # to git HEAD (the CI checkout) and promotes the session to active.
    # Review sessions need an explicit ``base_commit`` and **must not**
    # disturb the active pointer.
    record = SessionRecord(
        session_id=service._make_unique_session_id(spec_id),  # noqa: SLF001
        spec_path=Path(spec_path),
        spec_summary=summary,
        start_commit=base_commit,
        start_branch=head_branch,
        opened_at=datetime.now(UTC),
    )
    service.save_new_record(record)
    return record


def report_ci_checkpoint(
    service: SessionService,
    *,
    session_id: str,
    validation_payload: dict[str, Any] | None = None,
    manual_claims: Iterable[str] = (),
    manual_artifacts: Iterable[str] = (),
    note: str = "",
) -> SessionRecord:
    """Append a ``CI_BOT`` checkpoint to the review session.

    ``validation_payload`` is the JSON dict produced by
    ``cortex ci validate-pr --format json`` (see
    :meth:`ValidationResult.to_json_dict`). When supplied, hooks that
    passed become verified_claims, warnings become unverified_claims,
    and files_in_diff become artifacts_touched.
    """
    verified: list[str] = list(manual_claims)
    unverified: list[str] = []
    artifacts: list[str] = list(manual_artifacts)
    payload_note = note

    if validation_payload is not None:
        for hook in validation_payload.get("verification_results", []):
            label = (
                f"hook {hook['name']!r} passed"
                if hook.get("passed")
                else f"hook {hook['name']!r} failed (exit {hook.get('exit_code')})"
            )
            if hook.get("passed"):
                verified.append(label)
            else:
                unverified.append(label)
        for w in validation_payload.get("warnings", []):
            unverified.append(str(w))
        for b in validation_payload.get("blockers", []):
            unverified.append(f"blocker: {b}")
        for f in validation_payload.get("files_in_diff", []):
            artifacts.append(str(f))
        if not payload_note:
            payload_note = str(validation_payload.get("summary_text", "")).strip()

    return service.checkpoint(
        session_id,
        source=CheckpointSource.CI_BOT,
        verified_claims=verified,
        unverified_claims=unverified,
        artifacts_touched=artifacts,
        note=payload_note,
    )


def close_review_session(
    service: SessionService,
    *,
    session_id: str,
    status: SessionStatus,
    reason: str = "",
) -> SessionRecord:
    """Close the review session into a terminal status.

    Review sessions deliberately bypass the documenter — their role is
    audit-only, not memory enrichment. ``documenter_decision`` mirrors
    ``status`` so the SessionRecord invariant holds.
    """
    if status not in {
        SessionStatus.CLOSED,
        SessionStatus.HANDOFF,
        SessionStatus.ABANDONED,
    }:
        raise ValueError(
            f"status must be CLOSED / HANDOFF / ABANDONED, got {status.value!r}"
        )
    if reason:
        # Record the reason as a final manual checkpoint so the audit
        # log has the justification.
        service.checkpoint(
            session_id,
            source=CheckpointSource.MANUAL,
            note=f"close reason: {reason}",
        )
    return service.close(
        session_id,
        status=status,
        documenter_decision=status,
    )


__all__ = [
    "close_review_session",
    "open_review_session",
    "report_ci_checkpoint",
]
