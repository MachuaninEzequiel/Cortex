"""E2E tests for the interactive documenter mode (Phase 04 / T4.7).

We replace :class:`InteractiveSession` with a scripted test double so the
``cortex finish-session --interactive`` CLI path is exercised end-to-end
without needing a real TTY. The double returns canned
:class:`InteractiveResult` values that map to the user's choices
([A]pprove, [E]dit, [H]andoff, [C]ancel).
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cortex.cli.main import app
from cortex.documenter.interactive import InteractiveAction, InteractiveResult
from cortex.session import SessionStatus

runner = CliRunner()
PY = sys.executable


# ── Fixture: cortex repo with active session via create-spec ────────


@pytest.fixture
def interactive_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@x.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)

    (repo / "src").mkdir()
    (repo / "src" / "demo.py").write_text("def x(): pass\n", encoding="utf-8")

    cortex_dir = repo / ".cortex"
    cortex_dir.mkdir()
    (cortex_dir / "workspace.yaml").write_text("layout_version: 2\n", encoding="utf-8")
    (cortex_dir / "config.yaml").write_text(
        "semantic:\n  vault_path: vault\nepisodic:\n  persist_dir: memory\n",
        encoding="utf-8",
    )
    (cortex_dir / "vault" / "specs").mkdir(parents=True)
    (cortex_dir / "vault" / "sessions").mkdir()
    (cortex_dir / "vault" / "decisions").mkdir()
    (cortex_dir / "sessions").mkdir()
    (cortex_dir / "memory").mkdir()

    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)
    monkeypatch.chdir(repo)
    return repo


def _create_spec_and_edit(repo: Path) -> None:
    """Create a spec, then edit + commit so the session has a real diff."""
    args = [
        "create-spec",
        "--title",
        "Interactive demo",
        "--goal",
        "Validate interactive mode",
        "--verification-hook",
        f'name=t;command={PY} -c "exit(0)"',
        "--file",
        "src/demo.py",
    ]
    r = runner.invoke(app, args)
    assert r.exit_code == 0, r.stdout
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "spec"], cwd=repo, check=True)
    (repo / "src" / "demo.py").write_text("def x(): return 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "edit"], cwd=repo, check=True)


@pytest.fixture
def install_scripted_session(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[InteractiveResult]]:
    """Replace ``InteractiveSession`` in the documenter module with a stub.

    Yields a list to which the caller appends the canned
    :class:`InteractiveResult` for each prompt invocation. The stub pops
    from the front of that list on every ``.prompt()`` call.
    """
    canned: list[InteractiveResult] = []

    class _Stub:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def prompt(self, _reconstruction: object) -> InteractiveResult:
            assert canned, "test forgot to append an InteractiveResult"
            return canned.pop(0)

    monkeypatch.setattr(
        "cortex.documenter.interactive.InteractiveSession", _Stub
    )
    yield canned


# ── Scenarios ───────────────────────────────────────────────────────


@pytest.mark.e2e
class TestInteractiveFlow:
    def test_approve_persists_default_note(
        self,
        interactive_project: Path,
        install_scripted_session: list[InteractiveResult],
    ) -> None:
        _create_spec_and_edit(interactive_project)
        install_scripted_session.append(
            InteractiveResult(action=InteractiveAction.APPROVE)
        )
        r = runner.invoke(app, ["finish-session", "--interactive", "--json"])
        assert r.exit_code == 0, r.stdout
        payload = json.loads(r.stdout)
        assert payload["final_status"] == SessionStatus.CLOSED.value
        assert Path(payload["session_note_path"]).is_file()

    def test_handoff_path_records_status(
        self,
        interactive_project: Path,
        install_scripted_session: list[InteractiveResult],
    ) -> None:
        _create_spec_and_edit(interactive_project)
        install_scripted_session.append(
            InteractiveResult(
                action=InteractiveAction.HANDOFF,
                forced_status=SessionStatus.HANDOFF,
            )
        )
        r = runner.invoke(app, ["finish-session", "--interactive", "--json"])
        assert r.exit_code == 0, r.stdout
        payload = json.loads(r.stdout)
        assert payload["final_status"] == SessionStatus.HANDOFF.value

    def test_cancel_leaves_session_open(
        self,
        interactive_project: Path,
        install_scripted_session: list[InteractiveResult],
    ) -> None:
        _create_spec_and_edit(interactive_project)
        install_scripted_session.append(
            InteractiveResult(action=InteractiveAction.CANCEL)
        )
        r = runner.invoke(app, ["finish-session", "--interactive"])
        assert r.exit_code == 0
        assert "Cancelled" in r.stdout or "Cancelled" in r.stderr or "OPEN" in r.stdout
        # Session must still be OPEN after cancel.
        status = runner.invoke(app, ["session", "current"])
        assert status.exit_code == 0
        assert "no active session" not in status.stdout.lower()

    def test_edit_body_makes_it_into_session_note(
        self,
        interactive_project: Path,
        install_scripted_session: list[InteractiveResult],
    ) -> None:
        _create_spec_and_edit(interactive_project)
        install_scripted_session.append(
            InteractiveResult(
                action=InteractiveAction.APPROVE,
                edited_note_title="A wildly different title",
                edited_note_body="User-authored body. Magic marker XYZ-42.",
            )
        )
        r = runner.invoke(app, ["finish-session", "--interactive", "--json"])
        assert r.exit_code == 0, r.stdout
        payload = json.loads(r.stdout)
        body = Path(payload["session_note_path"]).read_text(encoding="utf-8")
        assert "Magic marker XYZ-42" in body
        assert "A wildly different title" in body

    def test_no_interactive_flag_uses_auto_default(
        self,
        interactive_project: Path,
        install_scripted_session: list[InteractiveResult],
    ) -> None:
        """Without --interactive, the stub MUST NOT be invoked."""
        _create_spec_and_edit(interactive_project)
        # Intentionally do NOT append to canned — if interactive runs, it fails.
        r = runner.invoke(app, ["finish-session", "--json"])
        assert r.exit_code == 0, r.stdout
        payload = json.loads(r.stdout)
        assert payload["final_status"] == SessionStatus.CLOSED.value
