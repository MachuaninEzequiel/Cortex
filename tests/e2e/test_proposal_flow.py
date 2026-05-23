"""E2E coverage of the Phase 09.A ``--proposal-mode`` flag.

Drives ``cortex create-spec`` through the Typer CLI and validates the
three modes:

* ``optional`` (default) — spec creation proceeds without explicit
  confirmation.
* ``required`` — creation fails unless ``--proposal-confirmed`` is also
  passed.
* ``skip`` — creation proceeds even if no confirmation is supplied.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cortex.cli.main import app

runner = CliRunner()
PY = sys.executable


@pytest.fixture
def proposal_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Minimal Cortex-shaped project fixture (same shape as test_byo_flow)."""
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

    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)

    monkeypatch.chdir(repo)
    return repo


def _create_spec_args(title: str, *extra: str) -> list[str]:
    return [
        "create-spec",
        "--title",
        title,
        "--goal",
        "proposal-mode E2E",
        "--verification-hook",
        f'name=smoke;command={PY} -c "exit(0)"',
        "--file",
        "src/foo.py",
        *extra,
    ]


@pytest.mark.e2e
class TestProposalFlow:
    def test_proposal_optional_creates_spec_without_confirmation(
        self,
        proposal_project: Path,
    ) -> None:
        """Default ``optional`` mode → spec persisted, exit 0."""
        result = runner.invoke(app, _create_spec_args("opt-default"))
        assert result.exit_code == 0, result.stdout
        assert "Specification saved" in result.stdout

    def test_proposal_optional_explicit_also_works(
        self,
        proposal_project: Path,
    ) -> None:
        result = runner.invoke(
            app,
            _create_spec_args("opt-explicit", "--proposal-mode", "optional"),
        )
        assert result.exit_code == 0, result.stdout

    def test_proposal_required_blocks_without_confirmation(
        self,
        proposal_project: Path,
    ) -> None:
        """Required mode without ``--proposal-confirmed`` must fail."""
        result = runner.invoke(
            app,
            _create_spec_args("req-no-confirm", "--proposal-mode", "required"),
        )
        assert result.exit_code == 1
        # CliRunner merges stdout+stderr by default — the message lands
        # in the combined output regardless of stream.
        combined = result.stdout + (result.stderr or "")
        assert "proposal_mode is 'required'" in combined
        assert "not confirmed" in combined

    def test_proposal_required_succeeds_with_confirmation(
        self,
        proposal_project: Path,
    ) -> None:
        result = runner.invoke(
            app,
            _create_spec_args(
                "req-confirmed",
                "--proposal-mode",
                "required",
                "--proposal-confirmed",
            ),
        )
        assert result.exit_code == 0, result.stdout
        assert "Specification saved" in result.stdout

    def test_proposal_skip_bypasses_check(self, proposal_project: Path) -> None:
        """Skip mode proceeds even without confirmation."""
        result = runner.invoke(
            app,
            _create_spec_args("skipped", "--proposal-mode", "skip"),
        )
        assert result.exit_code == 0, result.stdout

    def test_invalid_proposal_mode_rejected(self, proposal_project: Path) -> None:
        result = runner.invoke(
            app,
            _create_spec_args("bogus", "--proposal-mode", "make-stuff-up"),
        )
        assert result.exit_code == 1
        combined = result.stdout + (result.stderr or "")
        assert "proposal_mode must be one of" in combined
