"""cortex.documenter.diff_parser — Parse ``git diff --name-status`` output.

Used by the reconstruction algorithm to classify changes between a
session's start commit and HEAD. The parser is intentionally lenient:
unknown status letters fall back to ``"modified"`` rather than raising,
so future git versions don't break the documenter.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

DiffAction = Literal["added", "modified", "deleted", "renamed", "copied"]

# Status letter → semantic action. Renames and copies use ``R<percentage>``
# or ``C<percentage>``; we strip the percentage suffix before lookup.
_STATUS_MAP: dict[str, DiffAction] = {
    "A": "added",
    "M": "modified",
    "D": "deleted",
    "R": "renamed",
    "C": "copied",
    "T": "modified",  # type change (e.g. file → symlink); treat as modified
}


@dataclass(frozen=True)
class DiffEntry:
    """One file change between two commits.

    ``path`` is the *current* (post-change) location. ``old_path`` is set
    for renames and copies; ``None`` otherwise.
    """

    action: DiffAction
    path: Path
    old_path: Path | None = None


def parse_name_status(output: str) -> list[DiffEntry]:
    """Parse the stdout of ``git diff --name-status``.

    Each non-empty line has the form ``<status>\\t<path>`` or, for renames
    and copies, ``<status>\\t<old_path>\\t<new_path>``. Empty lines and
    leading whitespace are ignored. Unknown statuses fall back to
    ``"modified"``.
    """
    entries: list[DiffEntry] = []
    for raw_line in output.splitlines():
        line = raw_line.rstrip("\r\n")
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            # Malformed — skip rather than raise. The documenter is
            # defensive on read paths.
            continue
        status = parts[0].strip()
        letter = status[:1].upper()
        action = _STATUS_MAP.get(letter, "modified")
        if action in {"renamed", "copied"} and len(parts) >= 3:
            entries.append(
                DiffEntry(
                    action=action,
                    path=Path(parts[2]),
                    old_path=Path(parts[1]),
                )
            )
        else:
            entries.append(DiffEntry(action=action, path=Path(parts[1])))
    return entries


__all__ = ["DiffAction", "DiffEntry", "parse_name_status"]
