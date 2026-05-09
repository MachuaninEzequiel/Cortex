"""cortex.autopilot.detectors.ambiguous — Ambiguous-request detector."""
from __future__ import annotations

from cortex.autopilot.models import DetectionRequest, DetectionResult


class AmbiguousRequestDetector:
    """Detects vague user requests that need clarification before preflight.

    Heuristics (from §7.1.1 of the global plan):
    - request with fewer than 8 meaningful words
    - vague verbs without concrete object ("mejorar", "fix", etc.)
    - no mention of files, modules or specific functions
    - no implicit acceptance criterion
    """

    name = "ambiguous_request"

    VAGUE_VERBS = {
        "mejorar", "arreglar", "cambiar", "actualizar", "fixear",
        "improve", "fix", "change", "update", "refactor",
    }
    MIN_WORDS = 8
    FILE_EXTS = ("py", "ts", "js", "md", "yaml", "json")

    def detect(self, request: DetectionRequest) -> DetectionResult:
        if not request.user_request:
            return DetectionResult(
                task_type="ambiguous",
                confidence=0.9,
                reason="No user request provided",
                suggested_complexity="none",
            )

        words = request.user_request.lower().split()
        has_vague_verb = any(w in self.VAGUE_VERBS for w in words)
        is_short = len(words) < self.MIN_WORDS
        has_file_ref = any(
            "." in w and w.split(".")[-1] in self.FILE_EXTS
            for w in words
        )

        if is_short and has_vague_verb and not has_file_ref:
            return DetectionResult(
                task_type="ambiguous",
                confidence=0.7,
                reason=f"Short request ({len(words)} words) with vague verb, no file references",
                suggested_complexity="none",
            )

        return DetectionResult(
            task_type="noop",
            confidence=0.0,
            reason="Request appears sufficiently specific",
            suggested_complexity="none",
        )
