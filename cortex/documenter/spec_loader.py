"""cortex.documenter.spec_loader — Read a spec back from disk.

The reconstruction algorithm needs to introspect the spec the session was
anchored on (title, goal, files_in_scope, verification_hooks). This module
parses the YAML frontmatter of a persisted spec note and returns a
typed :class:`LoadedSpec`.

The loader is lenient: a spec without ``verification_hooks`` (e.g. one
created before the Pluggable Middle architecture) loads with an empty
list and the reconstruction skips verification with a warning.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from cortex.documentation.common import parse_frontmatter_lenient
from cortex.session.models import VerificationHook

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoadedSpec:
    """Subset of spec fields the reconstructor cares about."""

    path: Path
    title: str
    goal: str
    files_in_scope: list[Path]
    constraints: list[str]
    acceptance_criteria: list[str]
    verification_hooks: list[VerificationHook]
    raw_frontmatter: dict[str, Any] = field(default_factory=dict)


def load_spec(path: Path) -> LoadedSpec:
    """Parse the spec at ``path`` and return a :class:`LoadedSpec`.

    Missing or malformed frontmatter yields a :class:`LoadedSpec` with
    empty fields (the reconstructor handles that gracefully). Invalid
    hook entries are logged and skipped — the spec stays usable.

    Note: this loader reads frontmatter only. Body text (goal,
    requirements, acceptance criteria) is duplicated in the frontmatter
    by ``SpecService`` so we don't have to re-parse the markdown body.
    For specs from earlier versions where body and frontmatter diverge,
    frontmatter wins.
    """
    if not path.is_file():
        return _empty(path)
    fm = parse_frontmatter_lenient(path)
    if not fm:
        return _empty(path)

    hooks = _load_hooks(fm.get("verification_hooks") or [])

    return LoadedSpec(
        path=path,
        title=str(fm.get("title", "")),
        goal=str(fm.get("goal") or _extract_section(path, "## Goal")),
        files_in_scope=[Path(p) for p in (fm.get("files_in_scope") or [])],
        constraints=list(fm.get("constraints") or []),
        acceptance_criteria=list(fm.get("acceptance_criteria") or []),
        verification_hooks=hooks,
        raw_frontmatter=fm,
    )


def _empty(path: Path) -> LoadedSpec:
    return LoadedSpec(
        path=path,
        title="",
        goal="",
        files_in_scope=[],
        constraints=[],
        acceptance_criteria=[],
        verification_hooks=[],
    )


def _load_hooks(raw: list[Any]) -> list[VerificationHook]:
    """Coerce raw frontmatter entries into :class:`VerificationHook` list.

    Skips invalid entries with a logged warning rather than raising —
    one bad hook should never disable verification for the rest.
    """
    hooks: list[VerificationHook] = []
    for entry in raw:
        if isinstance(entry, VerificationHook):
            hooks.append(entry)
            continue
        if not isinstance(entry, dict):
            logger.warning("Skipping non-mapping verification_hook entry: %r", entry)
            continue
        try:
            hooks.append(VerificationHook.model_validate(entry))
        except ValidationError as exc:
            logger.warning("Skipping invalid verification_hook %r: %s", entry, exc)
    return hooks


def _extract_section(path: Path, heading: str) -> str:
    """Pull the body text under ``heading`` (used as a fallback for legacy specs).

    Returns the lines between ``heading`` and the next ``##``, stripped.
    Used only when the frontmatter doesn't carry the field.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    lines = text.splitlines()
    in_section = False
    collected: list[str] = []
    for line in lines:
        if line.startswith(heading):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            collected.append(line)
    return "\n".join(collected).strip()


__all__ = ["LoadedSpec", "load_spec"]
