"""cortex.ci.result — Typed inputs and outputs for the CI validator."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from cortex.documenter.spec_loader import LoadedSpec
from cortex.session.models import SessionRecord, VerificationHookResult

SessionMatchKind = Literal["explicit", "by_commit", "by_branch", "none"]
ValidationStatus = Literal["pass", "warn", "blocked", "error"]


@dataclass(frozen=True)
class ValidationInput:
    """Everything the validator needs to evaluate a single PR."""

    diff_text: str
    repo_root: Path
    base_commit: str | None = None
    head_commit: str | None = None
    base_branch: str | None = None
    head_branch: str | None = None
    pr_number: int | None = None
    pr_author: str | None = None
    explicit_session_id: str | None = None


@dataclass(frozen=True)
class ScopeDriftFinding:
    """One file that violated ``spec.files_in_scope``."""

    path: Path
    reason: Literal["out_of_scope", "unimplemented"]


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of :class:`CiValidator.validate`.

    Stable JSON schema (``to_json_dict``) for downstream consumers
    (workflows, dashboards). The Markdown formatter operates on this
    object directly.
    """

    session_match: SessionMatchKind
    matched_session: SessionRecord | None
    spec: LoadedSpec | None
    files_in_diff: list[Path]
    scope_drift: list[ScopeDriftFinding] = field(default_factory=list)
    verification_results: list[VerificationHookResult] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    exit_code: int = 0
    status: ValidationStatus = "pass"
    summary_text: str = ""
    # Original PR inputs kept around for the Markdown formatter.
    pr_number: int | None = None
    pr_author: str | None = None
    head_branch: str | None = None

    def to_json_dict(self) -> dict[str, object]:
        """JSON-serialisable representation. Stable across releases."""
        return {
            "status": self.status,
            "exit_code": self.exit_code,
            "session_match": self.session_match,
            "session_id": (
                self.matched_session.session_id if self.matched_session else None
            ),
            "spec_path": str(self.spec.path) if self.spec else None,
            "files_in_diff": [p.as_posix() for p in self.files_in_diff],
            "scope_drift": [
                {"path": f.path.as_posix(), "reason": f.reason}
                for f in self.scope_drift
            ],
            "verification_results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "exit_code": r.exit_code,
                    "duration_ms": r.duration_ms,
                }
                for r in self.verification_results
            ],
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "summary_text": self.summary_text,
            "pr_number": self.pr_number,
            "pr_author": self.pr_author,
            "head_branch": self.head_branch,
        }


__all__ = [
    "ScopeDriftFinding",
    "SessionMatchKind",
    "ValidationInput",
    "ValidationResult",
    "ValidationStatus",
]
