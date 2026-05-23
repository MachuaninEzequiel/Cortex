"""Autopilot doctor tests — minimal smoke during Phase 03.

T3.12 will rebuild the doctor on top of the canonical session primitive
and add the proper coverage. For now this file just exercises the
``run_diagnosis`` happy-path so the function stays callable end-to-end.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from cortex.autopilot.doctor import DoctorReport, run_diagnosis


@pytest.fixture
def cortex_repo(tmp_path: Path) -> Path:
    """A minimal git repo with a ``.cortex/`` workspace skeleton."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".cortex").mkdir()
    (repo / ".cortex" / "sessions").mkdir()
    (repo / "config.yaml").write_text("episodic: {}\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "README.md").write_text("# repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "initial"], cwd=repo, check=True
    )
    return repo


class TestRunDiagnosis:
    def test_returns_report(self, cortex_repo: Path) -> None:
        report = run_diagnosis(cortex_repo)
        assert isinstance(report, DoctorReport)
        assert isinstance(report.checks, list)
        assert len(report.checks) > 0

    def test_known_check_names_present(self, cortex_repo: Path) -> None:
        report = run_diagnosis(cortex_repo)
        names = {c.name for c in report.checks}
        # Minimum set the Phase-03 doctor must expose.
        expected = {"config", "sessions_dir", "adapters", "last_finish"}
        assert expected.issubset(names)
