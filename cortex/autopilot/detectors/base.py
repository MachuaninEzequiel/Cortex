"""cortex.autopilot.detectors.base — Detector protocol and resolution logic."""
from __future__ import annotations

from typing import Protocol

from cortex.autopilot.models import DetectionRequest, DetectionResult


class AutopilotDetector(Protocol):
    """Protocol for task-type detectors."""

    name: str

    def detect(self, request: DetectionRequest) -> DetectionResult:
        ...


# Complexity ranking for tie-breaking (higher = more conservative)
_COMPLEXITY_RANK = {"deep": 3, "fast": 2, "none": 1}


def resolve_detectors(
    detectors: list[AutopilotDetector],
    request: DetectionRequest,
) -> DetectionResult:
    """Run all *detectors* and apply the resolution rules from the contract.

    Resolution rules (§7.1.2 of the global plan):
    1. Execute all registered detectors.
    2. Filter results with ``confidence > 0.3``.
    3. If any ``SecuritySensitiveDetector`` has ``confidence > 0.5``, it wins.
    4. If any ``AmbiguousRequestDetector`` has ``confidence > 0.6``, it blocks.
    5. Otherwise, pick the result with the highest ``confidence``.
    6. On tie, prefer the more conservative (greater suggested_complexity).
    """
    results: list[tuple[AutopilotDetector, DetectionResult]] = []
    for det in detectors:
        try:
            res = det.detect(request)
        except Exception:
            # Malfunctioning detectors are ignored rather than crashing the pipeline
            continue
        results.append((det, res))

    # Step 2 — filter by confidence threshold
    candidates = [(d, r) for d, r in results if r.confidence > 0.3]
    if not candidates:
        # Nothing confident enough — return noop from the highest-confidence result
        # or a synthetic noop if every detector failed.
        if results:
            return max(results, key=lambda dr: dr[1].confidence)[1]
        return DetectionResult(task_type="noop", confidence=0.0, reason="No detectors returned results")

    # Step 3 — security override
    security = [(d, r) for d, r in candidates if d.name == "security_sensitive" and r.confidence > 0.5]
    if security:
        return security[0][1]

    # Step 4 — ambiguous override (blocks before anything else)
    ambiguous = [(d, r) for d, r in candidates if d.name == "ambiguous_request" and r.confidence > 0.6]
    if ambiguous:
        return ambiguous[0][1]

    # Step 5 — highest confidence
    def _rank(dr: tuple[AutopilotDetector, DetectionResult]) -> tuple[float, int]:
        _det, res = dr
        complexity_score = _COMPLEXITY_RANK.get(res.suggested_complexity, 0)
        return (res.confidence, complexity_score)

    best = max(candidates, key=_rank)
    return best[1]
