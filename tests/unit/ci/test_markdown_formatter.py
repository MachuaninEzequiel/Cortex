"""Tests for :func:`cortex.ci.markdown_formatter.render_pr_comment` (Level 2)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from cortex.ci.markdown_formatter import DEFAULT_MARKER, render_pr_comment
from cortex.ci.result import ScopeDriftFinding, ValidationResult
from cortex.session.models import SessionRecord, SessionStatus, VerificationHookResult


def _session() -> SessionRecord:
    return SessionRecord(
        session_id="2026-05-17_demo",
        spec_path=Path("vault/specs/demo.md"),
        spec_summary="demo",
        start_commit="a" * 40,
        start_branch="feature/demo",
        opened_at=datetime.now(UTC),
        status=SessionStatus.OPEN,
    )


def _result(**overrides: object) -> ValidationResult:
    base: dict[str, object] = {
        "session_match": "explicit",
        "matched_session": _session(),
        "spec": None,
        "files_in_diff": [Path("src/x.py")],
        "scope_drift": [],
        "verification_results": [],
        "blockers": [],
        "warnings": [],
        "exit_code": 0,
        "status": "pass",
        "summary_text": "session=2026-05-17_demo status=pass",
        "pr_number": 42,
    }
    base.update(overrides)
    return ValidationResult(**base)  # type: ignore[arg-type]


def test_renders_marker_at_start_and_end() -> None:
    text = render_pr_comment(_result())
    assert text.startswith(DEFAULT_MARKER)
    assert text.rstrip().endswith(DEFAULT_MARKER)


def test_status_pass_format() -> None:
    text = render_pr_comment(_result())
    assert "PASS" in text
    assert "0 blocker(s)" in text


def test_warn_includes_warnings_section() -> None:
    text = render_pr_comment(
        _result(
            status="warn",
            exit_code=1,
            warnings=["out-of-scope file in diff"],
        )
    )
    assert "WARN" in text
    assert "#### Warnings" in text
    assert "out-of-scope file in diff" in text


def test_blocked_includes_blockers_section() -> None:
    text = render_pr_comment(
        _result(
            status="blocked",
            exit_code=2,
            blockers=["required hook failed"],
        )
    )
    assert "BLOCKED" in text
    assert "#### Blockers" in text
    assert "required hook failed" in text


def test_no_session_match_includes_action_hint() -> None:
    text = render_pr_comment(
        _result(
            session_match="none",
            matched_session=None,
            status="blocked",
            blockers=["No Cortex Session matches this PR."],
        )
    )
    assert "No Cortex Session matched" in text
    assert "cortex create-spec" in text


def test_long_file_list_truncated() -> None:
    files = [Path(f"src/file_{i}.py") for i in range(25)]
    text = render_pr_comment(_result(files_in_diff=files))
    assert "and 15 more" in text  # 25 - 10 visible


def test_hooks_section_when_present() -> None:
    text = render_pr_comment(
        _result(
            verification_results=[
                VerificationHookResult(
                    name="tests",
                    command="pytest",
                    passed=True,
                    exit_code=0,
                    output="ok",
                    duration_ms=2300,
                    run_at=datetime.now(UTC),
                )
            ]
        )
    )
    assert "#### Verification hooks" in text
    assert "✓ `tests`" in text


def test_scope_drift_section_when_present() -> None:
    drift = [ScopeDriftFinding(path=Path("src/x.py"), reason="out_of_scope")]
    text = render_pr_comment(_result(scope_drift=drift))
    assert "#### Scope drift" in text
    assert "src/x.py" in text
    assert "out_of_scope" in text
