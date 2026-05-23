"""Conditional rendering of ``session.md.j2`` per ``task_type``.

Phase 08 / T8.5 introduced ``{% if task_type == "..." %}`` blocks so a
single template serves all task profiles:

* ``question-only`` and ``docs-only`` → omit ``Changes Made`` and
  ``Files Touched``.
* ``security`` → adds a dedicated ``Security Review`` section with
  decorated verified / unverified claims.
* All other types (default / ``fast-code`` / ``deep-code``) → render the
  full layout that existed before T8.5.
"""

from __future__ import annotations

from typing import Any

from cortex.documentation.templates_engine import render_template

_TEMPLATE = "session.md.j2"


def _base_vars(**overrides: Any) -> dict[str, Any]:
    """Minimal context dict matching the SessionData → asdict shape."""
    base: dict[str, Any] = {
        "title": "Sample",
        "tags": ["session"],
        "links": [],
        "status": "completed",
        "owner": None,
        "team": None,
        "classification": None,
        "retention_days": None,
        "session_id": "abc123",
        "spec_summary": "Implement X.",
        "changes_made": ["edit src/foo.py"],
        "files_touched": ["src/foo.py"],
        "key_decisions": ["use bcrypt"],
        "next_steps": ["wire CI"],
        "pr": None,
        "branch": None,
        "commit": None,
        "verified_state": ["tests green"],
        "unverified_claims": ["perf negligible"],
        "blockers": [],
        "suggested_skills": [],
        "cortex_telemetry": None,
        "task_type": "",
    }
    base.update(overrides)
    return base


class TestQuestionOnlyAndDocsOnly:
    """``question-only`` and ``docs-only`` omit body sections about code."""

    def test_question_only_omits_files_section(self) -> None:
        out = render_template(_TEMPLATE, _base_vars(task_type="question-only"))
        assert "Files Touched" not in out
        assert "Changes Made" not in out
        # But the high-signal sections survive.
        assert "Key Decisions" in out

    def test_docs_only_omits_files_section(self) -> None:
        out = render_template(_TEMPLATE, _base_vars(task_type="docs-only"))
        assert "Files Touched" not in out
        assert "Changes Made" not in out
        assert "Key Decisions" in out


class TestSecurityTaskType:
    def test_security_adds_security_review_section(self) -> None:
        out = render_template(_TEMPLATE, _base_vars(task_type="security"))
        assert "Security Review" in out
        # Verified state uses the security marker.
        assert "✓ tests green" in out
        # Unverified claims use the pending marker.
        assert "⏸ perf negligible (unverified)" in out
        # The plain "Verified State" / "Unverified Claims" headings do not
        # double-render — the security block replaces them.
        assert "## Verified State" not in out
        assert "## Unverified Claims" not in out


class TestDeepAndFastCodeKeepFullLayout:
    def test_deep_code_includes_all_sections(self) -> None:
        out = render_template(_TEMPLATE, _base_vars(task_type="deep-code"))
        assert "Changes Made" in out
        assert "Files Touched" in out
        assert "Key Decisions" in out
        assert "Verified State" in out
        assert "Unverified Claims" in out

    def test_fast_code_includes_all_sections(self) -> None:
        out = render_template(_TEMPLATE, _base_vars(task_type="fast-code"))
        assert "Changes Made" in out
        assert "Files Touched" in out


class TestUnspecifiedTaskTypeFallsBackToFullLayout:
    """An empty ``task_type`` must not break the existing layout."""

    def test_empty_task_type_renders_full_layout(self) -> None:
        out = render_template(_TEMPLATE, _base_vars(task_type=""))
        assert "Changes Made" in out
        assert "Files Touched" in out
        assert "Key Decisions" in out

    def test_unknown_task_type_renders_full_layout(self) -> None:
        """Defensive: an unrecognised value renders the full template."""
        out = render_template(_TEMPLATE, _base_vars(task_type="something-new"))
        assert "Changes Made" in out
        assert "Files Touched" in out
