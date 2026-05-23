"""Tests for the top-level ``cortex finish-session`` CLI (T1.6)."""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cortex.cli.main import app
from cortex.session import SessionStatus

runner = CliRunner()
PY = sys.executable


# ---------------------------------------------------------------------------
# Fixture: a minimal but complete Cortex project (vault + .cortex/) with a
# session already open. ``cortex finish-session`` instantiates AgentMemory
# which needs all of it to exist.
# ---------------------------------------------------------------------------


@pytest.fixture
def project(tmp_path: Path) -> dict[str, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@x.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)

    (repo / "src").mkdir()
    (repo / "src" / "foo.py").write_text("def f(): return 1\n", encoding="utf-8")

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

    # Persist a spec note that the reconstruction can load.
    spec_path = cortex_dir / "vault" / "specs" / "2026-05-16_demo.md"
    spec_path.write_text(
        textwrap.dedent(
            f"""\
            ---
            title: demo
            doc_type: spec
            goal: keep foo working
            files_in_scope:
              - src/foo.py
            acceptance_criteria:
              - returns 1
            verification_hooks:
              - {{name: smoke, command: '{PY} -c "exit(0)"', required: true, success_criteria: "exit 0", timeout_seconds: 30}}
            ---
            """
        ),
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)

    # Open a session via the SessionService bound to the layout.
    from cortex.session.service import SessionService
    from cortex.session.storage import SessionStorage

    storage = SessionStorage(cortex_dir / "sessions")
    service = SessionService(storage, repo_root=repo)
    record = service.open(
        spec_id="2026-05-16_demo",
        spec_path=Path("vault/specs/2026-05-16_demo.md"),
        spec_summary="keep foo working",
    )

    return {"repo": repo, "cortex": cortex_dir, "session_id": Path(record.session_id)}


def _commit_edit(repo: Path, content: str = "def f(): return 2\n") -> None:
    (repo / "src" / "foo.py").write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "edit"], cwd=repo, check=True)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_finish_active_session(
        self, project: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _commit_edit(project["repo"])
        monkeypatch.chdir(project["repo"])
        result = runner.invoke(app, ["finish-session"])
        assert result.exit_code == 0, result.stdout
        assert "closed as closed" in result.stdout
        # The session note exists under vault/sessions/.
        notes = list((project["cortex"] / "vault" / "sessions").glob("*.md"))
        assert notes

    def test_finish_explicit_id(
        self, project: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _commit_edit(project["repo"])
        monkeypatch.chdir(project["repo"])
        result = runner.invoke(app, ["finish-session", str(project["session_id"])])
        assert result.exit_code == 0

    def test_json_output(
        self, project: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _commit_edit(project["repo"])
        monkeypatch.chdir(project["repo"])
        result = runner.invoke(app, ["finish-session", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["final_status"] == SessionStatus.CLOSED.value
        assert data["session_note_path"] is not None


# ---------------------------------------------------------------------------
# Error / forced paths
# ---------------------------------------------------------------------------


class TestErrors:
    def test_no_active_session_errors(
        self, project: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Close the session first via SessionService → no active.
        from cortex.session.service import SessionService
        from cortex.session.storage import SessionStorage

        storage = SessionStorage(project["cortex"] / "sessions")
        service = SessionService(storage, repo_root=project["repo"])
        service.close(
            str(project["session_id"]),
            status=SessionStatus.CLOSED,
            documenter_decision=SessionStatus.CLOSED,
        )
        monkeypatch.chdir(project["repo"])
        result = runner.invoke(app, ["finish-session"])
        assert result.exit_code == 1
        assert "No active session" in result.stderr

    def test_already_closed_session_errors(
        self, project: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Same setup but pass the id explicitly.
        from cortex.session.service import SessionService
        from cortex.session.storage import SessionStorage

        storage = SessionStorage(project["cortex"] / "sessions")
        service = SessionService(storage, repo_root=project["repo"])
        sid = str(project["session_id"])
        service.close(
            sid,
            status=SessionStatus.CLOSED,
            documenter_decision=SessionStatus.CLOSED,
        )
        monkeypatch.chdir(project["repo"])
        result = runner.invoke(app, ["finish-session", sid])
        assert result.exit_code == 1
        assert "already" in result.stderr

    def test_mutually_exclusive_handoff_and_abandon(
        self, project: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(project["repo"])
        result = runner.invoke(
            app,
            ["finish-session", "--handoff", "--abandon", "--reason", "x"],
        )
        assert result.exit_code == 1
        assert "mutually exclusive" in result.stderr

    def test_handoff_requires_reason(
        self, project: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(project["repo"])
        result = runner.invoke(app, ["finish-session", "--handoff"])
        assert result.exit_code == 1
        assert "--reason" in result.stderr


class TestForcedStatus:
    def test_force_handoff(
        self, project: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _commit_edit(project["repo"])
        monkeypatch.chdir(project["repo"])
        result = runner.invoke(
            app, ["finish-session", "--handoff", "--reason", "tests pending"]
        )
        assert result.exit_code == 0
        assert "closed as handoff" in result.stdout
