"""cortex.ci.session_matcher — find the Session matching a PR.

Priority is intentional: explicit > base_commit > head_branch > none.
The caller decides what to do with a ``"none"`` match (typically: emit a
warning and exit with code 2 — see ``cortex.ci.validator``).
"""

from __future__ import annotations

from cortex.ci.result import SessionMatchKind
from cortex.session.models import SessionRecord
from cortex.session.storage import SessionStorage


def find_session_for_pr(
    storage: SessionStorage,
    *,
    explicit_session_id: str | None = None,
    base_commit: str | None = None,
    head_branch: str | None = None,
) -> tuple[SessionRecord | None, SessionMatchKind]:
    """Resolve the Session that owns the given PR.

    Returns ``(record, match_kind)`` where ``match_kind`` is one of
    ``"explicit"``, ``"by_commit"``, ``"by_branch"``, or ``"none"``.
    """
    if explicit_session_id:
        try:
            return storage.load(explicit_session_id), "explicit"
        except Exception:  # noqa: BLE001 — surface as "none" rather than crash
            return None, "none"

    records = storage.list_all()

    if base_commit:
        for record in records:
            if record.start_commit == base_commit:
                return record, "by_commit"

    if head_branch:
        for record in records:
            if record.start_branch == head_branch:
                return record, "by_branch"

    return None, "none"


__all__ = ["find_session_for_pr"]
