"""
cortex.pipeline.domain.types
-----------------------------
Core value types for the DevSecDocOps pipeline.

All types are immutable (frozen dataclasses or Pydantic models).
No I/O, no side effects — safe to use anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any


# ------------------------------------------------------------------
# Stage classification
# ------------------------------------------------------------------

class StageType(Enum):
    """
    Semantic classification of pipeline stages.

    Used by the orchestrator to apply gate rules and
    by runners to map stages to CI provider primitives.
    """
    SECURITY_SCAN   = auto()   # SAST / SCA / dependency audit
    LINT            = auto()   # Static analysis / code style
    TEST            = auto()   # Test suite execution + coverage
    DOCUMENTATION   = auto()   # Doc verification / fallback generation
    BUILD           = auto()   # Compilation / packaging
    DEPLOY          = auto()   # Deployment to an environment


class StageStatus(Enum):
    """Execution outcome of a single pipeline stage."""
    PASSED   = "passed"    # Stage ran and succeeded
    FAILED   = "failed"    # Stage ran but failed (may block pipeline)
    SKIPPED  = "skipped"   # Stage was explicitly skipped
    ERROR    = "error"     # Stage raised an unexpected exception


# ------------------------------------------------------------------
# Result value object
# ------------------------------------------------------------------

@dataclass(frozen=True)
class StageResult:
    """
    Immutable record of a single stage's execution outcome.

    Produced by every ``PipelineStage.execute()`` call and
    consumed by the orchestrator for gate enforcement.

    Attributes:
        stage_type:   Which kind of stage produced this result.
        stage_name:   Human-readable name (e.g. "Run Tests").
        status:       Final outcome enum.
        message:      Short summary for display / PR comment.
        artifacts:    Arbitrary key-value pairs (e.g. coverage %, findings).
        duration_ms:  Wall-clock time taken (ms).
        timestamp:    UTC datetime when the stage completed.
    """
    stage_type:  StageType
    stage_name:  str
    status:      StageStatus
    message:     str                        = ""
    artifacts:   dict[str, Any]             = field(default_factory=dict)
    duration_ms: int                        = 0
    timestamp:   datetime                   = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def passed(self) -> bool:
        return self.status == StageStatus.PASSED

    @property
    def failed(self) -> bool:
        return self.status in (StageStatus.FAILED, StageStatus.ERROR)

    @property
    def icon(self) -> str:
        """Emoji icon for display in PR comments / logs."""
        return {
            StageStatus.PASSED:  "✅",
            StageStatus.FAILED:  "❌",
            StageStatus.SKIPPED: "⏭️",
            StageStatus.ERROR:   "💥",
        }.get(self.status, "❓")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict (for artifacts / upload)."""
        return {
            "stage_type":  self.stage_type.name,
            "stage_name":  self.stage_name,
            "status":      self.status.value,
            "message":     self.message,
            "artifacts":   self.artifacts,
            "duration_ms": self.duration_ms,
            "timestamp":   self.timestamp.isoformat(),
        }


# ------------------------------------------------------------------
# Pipeline report
# ------------------------------------------------------------------

@dataclass
class PipelineReport:
    """
    Aggregated result of a full pipeline run.

    Produced by ``PipelineOrchestrator.run()`` after all stages complete.
    """
    results:    list[StageResult]
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at:   datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def passed(self) -> bool:
        """True if all non-skipped stages passed."""
        return all(r.passed or r.status == StageStatus.SKIPPED for r in self.results)

    @property
    def failed_stages(self) -> list[StageResult]:
        return [r for r in self.results if r.failed]

    @property
    def total_duration_ms(self) -> int:
        return sum(r.duration_ms for r in self.results)

    def summary(self) -> str:
        """
        Human-readable single-line summary for logs.

        Example:
            Pipeline PASSED in 3.2s — [✅ security] [✅ lint] [✅ test] [✅ docs]
        """
        overall = "PASSED" if self.passed else "FAILED"
        stage_icons = " ".join(
            f"[{r.icon} {r.stage_name}]" for r in self.results
        )
        duration_s = self.total_duration_ms / 1000
        return f"Pipeline {overall} in {duration_s:.1f}s — {stage_icons}"

    def to_markdown(self) -> str:
        """
        Render pipeline results as a Markdown table for PR comments.

        Example output:
            | Stage | Status | Duration | Message |
            |-------|--------|----------|---------|
            | ✅ lint | passed | 1.2s | All checks passed |
            ...
        """
        lines = [
            "## 🧠 Cortex Pipeline Report",
            "",
            "| Stage | Status | Duration | Message |",
            "|-------|--------|----------|---------|",
        ]
        for r in self.results:
            duration = f"{r.duration_ms / 1000:.1f}s"
            lines.append(
                f"| {r.icon} {r.stage_name} | {r.status.value} "
                f"| {duration} | {r.message or '-'} |"
            )
        lines.append("")
        overall = "✅ All gates passed" if self.passed else "❌ Pipeline failed"
        lines.append(f"**{overall}** — Total: {self.total_duration_ms / 1000:.1f}s")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON artifact upload."""
        return {
            "passed":       self.passed,
            "started_at":   self.started_at.isoformat(),
            "ended_at":     self.ended_at.isoformat(),
            "duration_ms":  self.total_duration_ms,
            "results":      [r.to_dict() for r in self.results],
        }
