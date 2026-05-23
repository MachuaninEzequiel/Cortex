"""cortex.documenter — Documenter Reconstruction Mode (Phase 01).

This package implements the **Documenter Reconstruction Mode** introduced
by the Pluggable Middle architecture (Phase 01). Given a closed-but-not-
yet-documented :class:`SessionRecord`, the reconstructor:

1. Loads the spec the session was anchored on.
2. Computes the diff from ``start_commit`` to HEAD.
3. Runs the verification hooks declared by the spec.
4. Cross-checks ``files_in_scope`` against the actually-touched files.
5. (Optionally) searches memory for contradictions.
6. Builds a synthetic :class:`cortex.handoff.AgentHandoff`.
7. Decides the suggested status (closed / handoff / abandoned).
8. Surfaces ADR candidates from checkpoint notes.

The output of step 8 is consumed by :class:`DocumenterPersister`
(Phase 01 / T1.5) to write the session note and any ADRs.

See: ``docs/pluggable-middle/ARQUITECTURA-PLUGGABLE-MIDDLE.md`` §7.
"""

from __future__ import annotations

from cortex.documenter.adr_evaluator import ADRSuggestion, suggest_adrs
from cortex.documenter.contradiction_detector import (
    ContradictionDetector,
    ContradictionFinding,
    NoOpContradictionDetector,
)
from cortex.documenter.diff_parser import DiffEntry, parse_name_status
from cortex.documenter.persistence import (
    DocumenterPersister,
    FinishOverrides,
    FinishSessionResult,
)
from cortex.documenter.reconstruction import (
    ReconstructionInput,
    ReconstructionOutput,
    Reconstructor,
)
from cortex.documenter.spec_loader import LoadedSpec, load_spec

__all__ = [
    "ADRSuggestion",
    "ContradictionDetector",
    "ContradictionFinding",
    "DiffEntry",
    "DocumenterPersister",
    "FinishOverrides",
    "FinishSessionResult",
    "LoadedSpec",
    "NoOpContradictionDetector",
    "ReconstructionInput",
    "ReconstructionOutput",
    "Reconstructor",
    "load_spec",
    "parse_name_status",
    "suggest_adrs",
]
