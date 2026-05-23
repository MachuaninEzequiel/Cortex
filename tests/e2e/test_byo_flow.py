"""E2E tests for BYO (Bring-Your-Own) mode (Phase 01 / T1.10).

Demonstrates that a user can:

1. Run ``cortex create-spec`` with verification hooks → a Session opens.
2. Modify files manually (no SDDwork, no checkpoints).
3. Commit the changes.
4. Run ``cortex finish-session`` → the documenter reconstructs the
   context, runs the verification hooks, and persists a session note.

The four scenarios cover the architecture's contract:

- simple code change → status=CLOSED, mode=BYO
- failing verification → status=HANDOFF, blockers documented
- scope drift → out_of_scope files surface in next_steps
- no changes made → status=HANDOFF with unimplemented files listed
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cortex.cli.main import app
from cortex.session import SessionStatus

runner = CliRunner()
PY = sys.executable


# ---------------------------------------------------------------------------
# Fixture: a Cortex-shaped project with git + minimal vault + .cortex/.
# ---------------------------------------------------------------------------


@pytest.fixture
def byo_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@x.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)

    (repo / "src").mkdir()
    (repo / "src" / "calculator.py").write_text(
        "def add(a, b): return a + b\n", encoding="utf-8"
    )

    cortex_dir = repo / ".cortex"
    cortex_dir.mkdir()
    (cortex_dir / "workspace.yaml").write_text("layout_version: 2\n", encoding="utf-8")
    (cortex_dir / "config.yaml").write_text(
        "semantic:\n  vault_path: vault\nepisodic:\n  persist_dir: memory\n",
        encoding="utf-8",
    )
    (cortex_dir / "vault").mkdir()
    (cortex_dir / "vault" / "specs").mkdir()
    (cortex_dir / "vault" / "sessions").mkdir()
    (cortex_dir / "vault" / "decisions").mkdir()
    (cortex_dir / "sessions").mkdir()
    (cortex_dir / "memory").mkdir()

    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)

    monkeypatch.chdir(repo)
    return {"repo": repo, "cortex": cortex_dir}


def _create_spec(
    title: str,
    goal: str,
    files: list[str],
    *,
    hook_command: str = f'{PY} -c "exit(0)"',
    hook_name: str = "smoke",
) -> str:
    """Invoke ``cortex create-spec`` and return its captured stdout."""
    args = [
        "create-spec",
        "--title",
        title,
        "--goal",
        goal,
        "--verification-hook",
        f"name={hook_name};command={hook_command}",
    ]
    for f in files:
        args.extend(["--file", f])
    result = runner.invoke(app, args)
    assert result.exit_code == 0, f"create-spec failed: {result.stdout}\n{result.stderr}"
    return result.stdout


def _commit(repo: Path, message: str = "edit") -> None:
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=repo, check=True)


def _finish(*extra_args: str) -> dict[str, object]:
    """Invoke ``cortex finish-session --json`` and return parsed payload."""
    result = runner.invoke(app, ["finish-session", "--json", *extra_args])
    assert result.exit_code == 0, f"finish-session failed: {result.stdout}\n{result.stderr}"
    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestBYOFlow:
    def test_simple_code_change_yields_closed(
        self, byo_project: dict[str, Path]
    ) -> None:
        """Happy path: spec → edit file in scope → finish → CLOSED."""
        repo = byo_project["repo"]
        _create_spec(
            "Calculator subtraction",
            "Add subtraction support to the calculator",
            files=["src/calculator.py"],
        )
        _commit(repo, "add spec")

        # User edits the in-scope file and commits.
        (repo / "src" / "calculator.py").write_text(
            "def add(a, b): return a + b\ndef sub(a, b): return a - b\n",
            encoding="utf-8",
        )
        _commit(repo, "implement sub")

        payload = _finish()
        assert payload["final_status"] == SessionStatus.CLOSED.value
        assert payload["session_note_path"]
        # Session note was actually written.
        assert Path(payload["session_note_path"]).is_file()  # type: ignore[arg-type]
        # No ADRs in BYO mode (no checkpoints to mine).
        assert payload["adrs_created"] == []

    def test_failing_verification_yields_handoff(
        self, byo_project: dict[str, Path]
    ) -> None:
        """A hook that exits non-zero forces HANDOFF and documents the blocker."""
        repo = byo_project["repo"]
        _create_spec(
            "Failing verify",
            "Edit the file but hook always fails",
            files=["src/calculator.py"],
            hook_command=f'{PY} -c "exit(1)"',
            hook_name="must-fail",
        )
        _commit(repo, "add spec")

        (repo / "src" / "calculator.py").write_text(
            "def add(a, b): return a + b\ndef noop(): pass\n", encoding="utf-8"
        )
        _commit(repo, "edit")

        payload = _finish()
        assert payload["final_status"] == SessionStatus.HANDOFF.value
        body = Path(payload["session_note_path"]).read_text(encoding="utf-8")  # type: ignore[arg-type]
        assert "must-fail" in body  # blocker name surfaced
        assert "handoff" in body.lower()

    def test_scope_drift_recorded_in_next_steps(
        self, byo_project: dict[str, Path]
    ) -> None:
        """Touching files outside ``files_in_scope`` is surfaced as drift."""
        repo = byo_project["repo"]
        _create_spec(
            "Scoped edit",
            "Only calculator.py is in scope",
            files=["src/calculator.py"],
        )
        _commit(repo, "add spec")

        # Edit in-scope AND out-of-scope files.
        (repo / "src" / "calculator.py").write_text(
            "def add(a, b): return a + b + 0\n", encoding="utf-8"
        )
        (repo / "README.md").write_text("# Calc\n", encoding="utf-8")
        _commit(repo, "edit both")

        payload = _finish()
        body = Path(payload["session_note_path"]).read_text(encoding="utf-8")  # type: ignore[arg-type]
        assert "README.md" in body  # surfaced as scope drift in next steps

    def test_no_changes_yields_handoff_with_unimplemented(
        self, byo_project: dict[str, Path]
    ) -> None:
        """When the user runs finish without editing anything: HANDOFF."""
        repo = byo_project["repo"]
        _create_spec(
            "Will not be implemented",
            "User opens a spec but never makes any change",
            files=["src/calculator.py"],
        )
        _commit(repo, "add spec")

        payload = _finish()
        assert payload["final_status"] == SessionStatus.HANDOFF.value
        body = Path(payload["session_note_path"]).read_text(encoding="utf-8")  # type: ignore[arg-type]
        # The unimplemented file shows up in next_steps.
        assert "Implement: src/calculator.py" in body or "src/calculator.py" in body

    def test_session_listed_as_closed_after_finish(
        self, byo_project: dict[str, Path]
    ) -> None:
        """After ``finish-session``, ``session list`` shows the session closed."""
        repo = byo_project["repo"]
        _create_spec(
            "Tiny change",
            "Edit calculator",
            files=["src/calculator.py"],
        )
        _commit(repo, "add spec")
        (repo / "src" / "calculator.py").write_text(
            "def add(a, b): return a + b\n# updated\n", encoding="utf-8"
        )
        _commit(repo, "edit")

        _finish()
        list_result = runner.invoke(
            app, ["session", "list", "--project-root", str(repo), "--json"]
        )
        assert list_result.exit_code == 0
        records = json.loads(list_result.stdout)
        assert records
        assert records[0]["status"] == "closed"
