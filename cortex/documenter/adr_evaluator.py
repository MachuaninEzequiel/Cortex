"""cortex.documenter.adr_evaluator — Surface ADR candidates from checkpoints.

The architecture (§12 of the documenter subagent) requires three criteria
to merit an ADR: hard to reverse, surprising without context, and a real
trade-off. Pure-Python evaluation cannot judge those qualities; what we
*can* do is detect keyword signals in checkpoint notes and flag them as
*candidates*, with the rationale visible to the LLM or human reviewer
in interactive mode (Phase 04).

When no checkpoints exist (BYO mode), no ADR candidates are surfaced —
there is no narrated decision to mine.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from cortex.session.models import Checkpoint

# Keywords that signal an explicit decision narrative in a checkpoint
# note. Case-insensitive; whole-word matching to avoid false positives
# inside file names or identifiers.
_DECISION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bdecid(?:ed|imos|í)\b", re.IGNORECASE),
    re.compile(r"\bchose\b", re.IGNORECASE),
    re.compile(r"\binstead of\b", re.IGNORECASE),
    re.compile(r"\brather than\b", re.IGNORECASE),
    re.compile(r"\btrade-?off\b", re.IGNORECASE),
    re.compile(r"\bvs\.?\b", re.IGNORECASE),
    re.compile(r"\brejected\b", re.IGNORECASE),
    re.compile(r"\balternativa(?:s)?\b", re.IGNORECASE),
    re.compile(r"\bsupersedes\b", re.IGNORECASE),
    re.compile(r"\bADR\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class ADRSuggestion:
    """One candidate ADR surfaced from session evidence.

    Attributes:
        title:                  Short label derived from the note.
        rationale:              Why this looks like an ADR-worthy decision.
        source_checkpoint_index: Index into the session's ``checkpoints``
                                list that produced the suggestion, or
                                ``None`` for diff-derived candidates.
        evidence:               The original snippet that matched.
        confidence:             ``"high"`` if multiple decision keywords
                                matched in the same note; ``"low"``
                                otherwise. Used by Phase 04 interactive
                                review to order the prompt.
    """

    title: str
    rationale: str
    source_checkpoint_index: int | None
    evidence: str
    confidence: str = "low"


def suggest_adrs(
    checkpoints: Sequence[Checkpoint],
    diff_text: str = "",  # noqa: ARG001 — reserved for Phase 04 diff-driven heuristics
) -> list[ADRSuggestion]:
    """Return a list of ADR candidates derived from *checkpoints*.

    The current heuristic only inspects checkpoint notes. ``diff_text``
    is accepted to keep the API stable for future phases that may parse
    commit messages or diff hunks for decision narratives.

    A candidate is emitted when:

    - The checkpoint note matches **two or more** decision keywords →
      ``confidence="high"``.
    - The checkpoint note matches **exactly one** decision keyword →
      ``confidence="low"``.
    - Zero matches → no suggestion.

    Title is the first ~80 chars of the note, ellipsis if longer.
    """
    suggestions: list[ADRSuggestion] = []
    for idx, cp in enumerate(checkpoints):
        if not cp.note.strip():
            continue
        matches = [p for p in _DECISION_PATTERNS if p.search(cp.note)]
        if not matches:
            continue
        confidence = "high" if len(matches) >= 2 else "low"
        suggestions.append(
            ADRSuggestion(
                title=_title_from_note(cp.note),
                rationale=(
                    f"Checkpoint #{idx} note mentions decision signal(s): "
                    + ", ".join(sorted({m.pattern for m in matches}))
                ),
                source_checkpoint_index=idx,
                evidence=cp.note,
                confidence=confidence,
            )
        )
    return suggestions


def _title_from_note(note: str) -> str:
    """Build a short ADR title from a checkpoint note."""
    cleaned = " ".join(note.split())  # collapse whitespace
    if len(cleaned) <= 80:
        return cleaned
    return cleaned[:77].rstrip() + "..."


__all__ = ["ADRSuggestion", "suggest_adrs"]
