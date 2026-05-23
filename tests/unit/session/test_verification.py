"""Tests for :class:`cortex.session.verification.VerificationRunner` (T1.3)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from cortex.session import MAX_VERIFICATION_OUTPUT_BYTES, VerificationHook
from cortex.session.verification import VerificationRunner

# ---------------------------------------------------------------------------
# Cross-platform shell helpers
# ---------------------------------------------------------------------------
#
# Hooks are spec-author authored shell commands. To keep tests portable on
# Windows and POSIX, we invoke Python via ``sys.executable`` for anything
# beyond trivial echoes; ``shell=True`` then wraps it in cmd.exe or sh.


PY = sys.executable


@pytest.fixture
def runner(tmp_path: Path) -> VerificationRunner:
    return VerificationRunner(repo_root=tmp_path)


# ---------------------------------------------------------------------------
# Happy / failure paths
# ---------------------------------------------------------------------------


class TestRepoRootProperty:
    def test_property_exposes_root(self, tmp_path: Path) -> None:
        runner = VerificationRunner(repo_root=tmp_path)
        assert runner.repo_root == tmp_path


class TestRunHook:
    def test_success(self, runner: VerificationRunner) -> None:
        hook = VerificationHook(name="ok", command=f'{PY} -c "print(\\"hi\\")"')
        result = runner.run_hook(hook)
        assert result.passed is True
        assert result.exit_code == 0
        assert "hi" in result.output
        assert result.duration_ms >= 0
        assert result.run_at.tzinfo is not None

    def test_failure_non_zero_exit(self, runner: VerificationRunner) -> None:
        hook = VerificationHook(name="fail", command=f'{PY} -c "import sys; sys.exit(2)"')
        result = runner.run_hook(hook)
        assert result.passed is False
        assert result.exit_code == 2

    def test_timeout(self, runner: VerificationRunner) -> None:
        # 5-second sleep with 1-second timeout.
        hook = VerificationHook(
            name="slow",
            command=f'{PY} -c "import time; time.sleep(5)"',
            timeout_seconds=1,
        )
        result = runner.run_hook(hook)
        assert result.passed is False
        assert result.exit_code == -1
        assert "timeout" in result.output.lower()

    def test_stderr_is_captured(self, runner: VerificationRunner) -> None:
        hook = VerificationHook(
            name="stderr",
            command=f'{PY} -c "import sys; sys.stderr.write(\\"boom\\"); sys.exit(3)"',
        )
        result = runner.run_hook(hook)
        assert result.passed is False
        assert "boom" in result.output
        # The merged output carries the [stderr] marker when stderr is present.
        assert "[stderr]" in result.output or result.output == "boom"


# ---------------------------------------------------------------------------
# Encoding & truncation
# ---------------------------------------------------------------------------


class TestEncodingAndTruncation:
    def test_unicode_output_does_not_crash(self, runner: VerificationRunner) -> None:
        hook = VerificationHook(
            name="utf8",
            command=f'{PY} -c "print(\\"héllo ñ\\")"',
        )
        result = runner.run_hook(hook)
        assert result.passed is True
        # Either character set may have been replaced depending on the active
        # console encoding; we just assert that the runner did not raise and
        # that something representative survived.
        assert result.output

    def test_long_output_truncated_by_model(self, runner: VerificationRunner) -> None:
        # Emit ~50KB of bytes; the model caps at 10KB keeping the tail.
        # Use ``"x" * N`` via -c to avoid file IO.
        count = MAX_VERIFICATION_OUTPUT_BYTES * 5
        hook = VerificationHook(
            name="big",
            command=f'{PY} -c "import sys; sys.stdout.write(\\"x\\" * {count})"',
        )
        result = runner.run_hook(hook)
        # The model itself truncates output (kept the tail) — see
        # VerificationHookResult._validate_output_size.
        encoded = result.output.encode("utf-8")
        assert len(encoded) <= MAX_VERIFICATION_OUTPUT_BYTES + 200
        # The truncation header is present and the tail of "x"s survives.
        assert "truncated" in result.output
        assert result.output.endswith("x" * 100)


# ---------------------------------------------------------------------------
# Working directory
# ---------------------------------------------------------------------------


class TestWorkingDirectory:
    def test_cwd_is_repo_root(self, tmp_path: Path) -> None:
        # Create a sentinel file under repo_root; the hook reads it via
        # relative path to verify cwd was applied.
        marker = tmp_path / "marker.txt"
        marker.write_text("HERE", encoding="utf-8")
        runner = VerificationRunner(repo_root=tmp_path)
        hook = VerificationHook(
            name="cwd",
            command=f'{PY} -c "import pathlib; print(pathlib.Path(\\"marker.txt\\").read_text())"',
        )
        result = runner.run_hook(hook)
        assert result.passed is True
        assert "HERE" in result.output


# ---------------------------------------------------------------------------
# run_all
# ---------------------------------------------------------------------------


class TestRunAll:
    def test_preserves_order(self, runner: VerificationRunner) -> None:
        hooks = [
            VerificationHook(name="first", command=f'{PY} -c "print(\\"1\\")"'),
            VerificationHook(name="second", command=f'{PY} -c "print(\\"2\\")"'),
            VerificationHook(name="third", command=f'{PY} -c "print(\\"3\\")"'),
        ]
        results = runner.run_all(hooks)
        assert [r.name for r in results] == ["first", "second", "third"]
        assert all(r.passed for r in results)

    def test_empty_input_returns_empty(self, runner: VerificationRunner) -> None:
        assert runner.run_all([]) == []

    def test_failure_does_not_abort_remaining(self, runner: VerificationRunner) -> None:
        # First hook fails; the runner still runs the next one.
        hooks = [
            VerificationHook(name="bad", command=f'{PY} -c "import sys; sys.exit(1)"'),
            VerificationHook(name="good", command=f'{PY} -c "print(\\"ok\\")"'),
        ]
        results = runner.run_all(hooks)
        assert results[0].passed is False
        assert results[1].passed is True
