from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from cortex.cli.main import app


runner = CliRunner()


def test_install_skills_uses_dest_argument(monkeypatch, tmp_path: Path) -> None:
    called: dict[str, Path] = {}

    def fake_install_skills(target_path: Path) -> list[str]:
        called["target_path"] = target_path
        return ["obsidian-cli"]

    monkeypatch.setattr("cortex.skills.install_skills", fake_install_skills)

    result = runner.invoke(app, ["install-skills", "--dest", str(tmp_path)])

    assert result.exit_code == 0
    assert called["target_path"] == tmp_path
    assert str(tmp_path) in result.stdout
