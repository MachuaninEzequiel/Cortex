"""cortex.documenter.contradiction_detector — Pluggable memory-search.

The reconstruction algorithm (§7.2 step 5) checks for contradictions
between the current diff and prior decisions stored in Cortex memory.
That check requires the full :class:`cortex.core.AgentMemory` façade
(ChromaDB, ONNX embeddings, vault reader) which is too heavy for the
CLI ``cortex finish-session`` path.

To keep the reconstructor lightweight and testable, contradiction
detection is **pluggable** via the :class:`ContradictionDetector`
Protocol. The CLI passes :class:`NoOpContradictionDetector` (returns no
findings); the MCP-invoked documenter subagent — which already holds an
``AgentMemory`` — can provide a real implementation backed by
``cortex_search``.

Phase 02+ may promote a default implementation here as soon as a
lightweight semantic search becomes available without loading the full
memory stack.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from cortex.session.models import Checkpoint

ContradictionSeverity = Literal["info", "warn", "error"]


@dataclass(frozen=True)
class ContradictionFinding:
    """A potential conflict between current work and prior decisions.

    Attributes:
        prior_record:  Free-form description of the prior record found
                       in memory (path or summary).
        current_claim: What the current session is doing that may conflict.
        evidence:      A short snippet (≤ ~200 chars) showing the match.
        severity:      ``info`` (FYI), ``warn`` (review), or ``error``
                       (likely regression).
    """

    prior_record: str
    current_claim: str
    evidence: str
    severity: ContradictionSeverity = "info"


@runtime_checkable
class ContradictionDetector(Protocol):
    """Interface for memory-search-based contradiction detection."""

    def find_contradictions(
        self,
        spec_summary: str,
        diff_text: str,
        checkpoints: Sequence[Checkpoint],
    ) -> list[ContradictionFinding]:
        """Return contradictions between the current work and past records.

        Implementations must be side-effect-free w.r.t. the vault and
        the session record — they only read.
        """
        ...


class NoOpContradictionDetector:
    """Default detector: returns an empty list.

    Used by the CLI ``cortex finish-session`` path where instantiating
    :class:`AgentMemory` purely to look up potential contradictions is
    too heavy. The MCP-invoked subagent can override with a real
    implementation that hits ``cortex_search``.
    """

    def find_contradictions(
        self,
        spec_summary: str,  # noqa: ARG002 — interface requires the arg
        diff_text: str,  # noqa: ARG002 — interface requires the arg
        checkpoints: Sequence[Checkpoint],  # noqa: ARG002 — interface requires the arg
    ) -> list[ContradictionFinding]:
        return []


__all__ = [
    "ContradictionDetector",
    "ContradictionFinding",
    "ContradictionSeverity",
    "NoOpContradictionDetector",
]
