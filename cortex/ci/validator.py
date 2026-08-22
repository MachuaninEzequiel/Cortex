"""cortex.ci.validator — Validate a PR against its Session + spec.

The validator orchestrates the existing primitives (session matcher,
spec loader, scope cross-check, verification runner) into a single
result object. It is the heart of ``cortex ci validate-pr`` (Phase 07 /
Level 1).
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from cortex.ci.result import (
    ScopeDriftFinding,
    ValidationInput,
    ValidationResult,
)
from cortex.documenter.reconstruction import _scope_cross_check
from cortex.documenter.spec_loader import LoadedSpec, load_spec
from cortex.session.models import SessionRecord, SessionStatus
from cortex.session.service import SessionService
from cortex.session.verification import VerificationRunner

EXIT_PASS = 0
EXIT_WARN = 1
EXIT_BLOCKED = 2
EXIT_ERROR = 3


class CiValidator:
    """Run the Level 1 validation pipeline."""

    def __init__(
        self,
        session_service: SessionService,
        verification_runner: VerificationRunner,
        repo_root: Path,
    ) -> None:
        self._sessions = session_service
        self._verifier = verification_runner
        self._repo_root = Path(repo_root)

    def validate(self, payload: ValidationInput) -> ValidationResult:
        """Return a :class:`ValidationResult` for ``payload``."""
        record, match_kind = self._sessions.find_for_pr(
            explicit_session_id=payload.explicit_session_id,
            base_commit=payload.base_commit,
            head_branch=payload.head_branch,
        )

        files_in_diff = _parse_files_from_diff(payload.diff_text)

        if record is None:
            return _no_session_result(
                payload=payload,
                files_in_diff=files_in_diff,
                match_kind=match_kind,
            )

        spec = self._load_spec(record)
        warnings: list[str] = []
        blockers: list[str] = []

        # Lifecycle warnings: HANDOFF → warn; ABANDONED → block.
        if record.status is SessionStatus.HANDOFF:
            warnings.append(
                f"Matched session {record.session_id!r} is in HANDOFF status."
            )
        elif record.status is SessionStatus.ABANDONED:
            blockers.append(
                f"Matched session {record.session_id!r} is ABANDONED — block."
            )

        # Scope cross-check (re-uses the documenter's pure helper).
        scope_drift: list[ScopeDriftFinding] = []
        if spec is not None and spec.files_in_scope:
            _, out_of_scope, unimplemented = _scope_cross_check(
                files_in_diff, spec.files_in_scope
            )
            for path in out_of_scope:
                scope_drift.append(ScopeDriftFinding(path=path, reason="out_of_scope"))
                warnings.append(f"out-of-scope file in diff: {path.as_posix()}")
            for path in unimplemented:
                scope_drift.append(ScopeDriftFinding(path=path, reason="unimplemented"))
                blockers.append(f"file in scope not implemented: {path.as_posix()}")

        # Verification hooks.
        verif_results = []
        if spec is not None and spec.verification_hooks:
            verif_results = list(self._verifier.run_all(spec.verification_hooks))
            for r in verif_results:
                if r.passed:
                    continue
                # ``VerificationHookResult`` does not preserve the
                # ``required`` flag of the original ``VerificationHook``;
                # we look it up from the spec to decide blocker vs warn.
                hook = next(
                    (h for h in spec.verification_hooks if h.name == r.name),
                    None,
                )
                if hook is not None and not hook.required:
                    warnings.append(
                        f"non-required hook {r.name!r} failed (exit {r.exit_code})"
                    )
                else:
                    blockers.append(
                        f"required hook {r.name!r} failed (exit {r.exit_code})"
                    )
        elif spec is not None:
            warnings.append(
                "spec declares no verification_hooks — validation is partial"
            )

        if blockers:
            status = "blocked"
            exit_code = EXIT_BLOCKED
        elif warnings:
            status = "warn"
            exit_code = EXIT_WARN
        else:
            status = "pass"
            exit_code = EXIT_PASS

        summary = self._build_summary(
            record=record,
            status=status,
            files_in_diff=files_in_diff,
            verif_results=verif_results,
            warnings=warnings,
            blockers=blockers,
        )

        return ValidationResult(
            session_match=match_kind,
            matched_session=record,
            spec=spec,
            files_in_diff=files_in_diff,
            scope_drift=scope_drift,
            verification_results=verif_results,
            blockers=blockers,
            warnings=warnings,
            exit_code=exit_code,
            status=status,  # type: ignore[arg-type]
            summary_text=summary,
            pr_number=payload.pr_number,
            pr_author=payload.pr_author,
            head_branch=payload.head_branch,
        )

    # ── Internals ──────────────────────────────────────────────────

    def _load_spec(self, record: SessionRecord) -> LoadedSpec | None:
        spec_path = record.spec_path
        if not spec_path.is_absolute():
            spec_path = (self._repo_root / spec_path).resolve()
        if not spec_path.is_file():
            return None
        return load_spec(spec_path)

    @staticmethod
    def _build_summary(
        *,
        record: SessionRecord,
        status: str,
        files_in_diff: list[Path],
        verif_results: Sequence[object],
        warnings: list[str],
        blockers: list[str],
    ) -> str:
        passed = sum(1 for r in verif_results if getattr(r, "passed", False))
        return (
            f"session={record.session_id} status={status} "
            f"files={len(files_in_diff)} hooks={passed}/{len(verif_results)} "
            f"warnings={len(warnings)} blockers={len(blockers)}"
        )


def validate_pull_request(
    payload: ValidationInput,
    *,
    session_service: SessionService,
    verification_runner: VerificationRunner,
) -> ValidationResult:
    """Convenience wrapper used by the CLI."""
    return CiValidator(
        session_service=session_service,
        verification_runner=verification_runner,
        repo_root=payload.repo_root,
    ).validate(payload)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_files_from_diff(diff_text: str) -> list[Path]:
    """Extract the changed file paths from a unified diff body.

    Only ``+++ b/<path>`` lines are kept (right-hand side of the diff).
    Removed-only files surface as ``--- a/<path>`` with ``+++ /dev/null``
    — those still count as touched.
    """
    seen: list[Path] = []
    for raw in diff_text.splitlines():
        if raw.startswith("+++ b/"):
            seen.append(Path(raw[len("+++ b/"):].strip()))
        elif raw.startswith("--- a/"):
            # Pair with the next +++ line; if that is /dev/null, the file
            # was deleted and we still want it in the touched list.
            candidate = Path(raw[len("--- a/"):].strip())
            # Only add if not already added by a +++ b/ line later.
            if candidate not in seen:
                seen.append(candidate)
    # Dedupe while preserving order.
    out: list[Path] = []
    for p in seen:
        if p not in out:
            out.append(p)
    return out


def _no_session_result(
    *,
    payload: ValidationInput,
    files_in_diff: list[Path],
    match_kind: str,
) -> ValidationResult:
    """Build a ``status=blocked`` result when no Session matches."""
    blockers = [
        "No Cortex Session matches this PR. Open one before re-running CI: "
        "`cortex create-spec ...` (creates the spec and the session)."
    ]
    return ValidationResult(
        session_match=match_kind,  # type: ignore[arg-type]
        matched_session=None,
        spec=None,
        files_in_diff=files_in_diff,
        scope_drift=[],
        verification_results=[],
        blockers=blockers,
        warnings=[],
        exit_code=EXIT_BLOCKED,
        status="blocked",
        summary_text=(
            f"no session match (kind={match_kind}); "
            f"diff has {len(files_in_diff)} files"
        ),
        pr_number=payload.pr_number,
        pr_author=payload.pr_author,
        head_branch=payload.head_branch,
    )


__all__ = [
    "CiValidator",
    "EXIT_BLOCKED",
    "EXIT_ERROR",
    "EXIT_PASS",
    "EXIT_WARN",
    "validate_pull_request",
]
