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


def test_install_ide_specific_target_uses_adapter_layer(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_inject(ide_name: str, project_root: Path | None = None) -> list[str]:
        called["ide_name"] = ide_name
        called["project_root"] = project_root
        return ["ok"]

    monkeypatch.setattr("cortex.ide.inject", fake_inject)

    result = runner.invoke(app, ["install-ide", "--ide", "cursor"])

    assert result.exit_code == 0
    assert called["ide_name"] == "cursor"
    assert called["project_root"] == Path.cwd()


def test_inject_all_uses_new_ide_module(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_inject_all(project_root: Path | None = None) -> dict[str, list[str]]:
        called["project_root"] = project_root
        return {"cursor": ["ok"]}

    monkeypatch.setattr("cortex.ide.inject_all", fake_inject_all)

    result = runner.invoke(app, ["inject", "--all"])

    assert result.exit_code == 0
    assert called["project_root"] == Path.cwd()
