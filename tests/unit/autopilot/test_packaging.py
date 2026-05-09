"""Tests for cortex.autopilot.packaging."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cortex.autopilot.packaging import (
    PluginManifest,
    install_plugin,
    list_compatible_plugins,
    uninstall_plugin,
    validate_manifest,
)


class TestPluginManifest:
    def test_from_file(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "plugin.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "name": "cortex-autopilot",
                    "version": "0.1.0",
                    "description": "Autopilot plugin",
                    "author": "DevSecDocOps",
                    "homepage": "https://example.com",
                    "skills": {"directory": "cortex/autopilot/skills"},
                    "hooks": {"directory": "cortex/autopilot/hooks"},
                    "requires": {"python": ">=3.10"},
                }
            ),
            encoding="utf-8",
        )
        m = PluginManifest.from_file(manifest_path)
        assert m.name == "cortex-autopilot"
        assert m.version == "0.1.0"
        assert m.skills["directory"] == "cortex/autopilot/skills"

    def test_from_file_invalid_json(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "plugin.json"
        manifest_path.write_text("not json", encoding="utf-8")
        with pytest.raises(Exception):
            PluginManifest.from_file(manifest_path)


class TestValidateManifest:
    def test_valid_manifest(self) -> None:
        m = PluginManifest(
            name="test",
            version="1.0.0",
            skills={"directory": "skills"},
            hooks={"directory": "hooks"},
        )
        assert validate_manifest(m) == []

    def test_missing_name(self) -> None:
        m = PluginManifest(name="", version="1.0.0", skills={"directory": "s"}, hooks={"directory": "h"})
        errors = validate_manifest(m)
        assert any("name" in e for e in errors)

    def test_missing_version(self) -> None:
        m = PluginManifest(name="test", version="", skills={"directory": "s"}, hooks={"directory": "h"})
        errors = validate_manifest(m)
        assert any("version" in e for e in errors)

    def test_missing_skills_directory(self) -> None:
        m = PluginManifest(name="test", version="1.0.0", skills={}, hooks={"directory": "h"})
        errors = validate_manifest(m)
        assert any("skills.directory" in e for e in errors)

    def test_missing_hooks_directory(self) -> None:
        m = PluginManifest(name="test", version="1.0.0", skills={"directory": "s"}, hooks={})
        errors = validate_manifest(m)
        assert any("hooks.directory" in e for e in errors)


class TestInstallUninstall:
    def test_install_cursor(self, tmp_path: Path) -> None:
        modified = install_plugin(tmp_path, "cursor")
        assert len(modified) == 1
        assert (tmp_path / ".cursorrules").exists()

    def test_install_unknown(self, tmp_path: Path) -> None:
        with pytest.raises(KeyError):
            install_plugin(tmp_path, "unknown-ide")

    def test_uninstall_cursor(self, tmp_path: Path) -> None:
        install_plugin(tmp_path, "cursor")
        modified = uninstall_plugin(tmp_path, "cursor")
        assert len(modified) == 1
        text = (tmp_path / ".cursorrules").read_text(encoding="utf-8")
        assert "AUTOPILOT-CURSOR" not in text

    def test_uninstall_without_install(self, tmp_path: Path) -> None:
        modified = uninstall_plugin(tmp_path, "cursor")
        assert modified == []

    def test_install_idempotent(self, tmp_path: Path) -> None:
        modified1 = install_plugin(tmp_path, "cursor")
        assert len(modified1) == 1
        modified2 = install_plugin(tmp_path, "cursor")
        # Second install should be a no-op because the marker is already present
        assert modified2 == []


class TestListCompatiblePlugins:
    def test_finds_manifests(self, tmp_path: Path) -> None:
        # Create fake plugin directories
        (tmp_path / ".cursor-plugin").mkdir()
        (tmp_path / ".cursor-plugin" / "plugin.json").write_text(
            json.dumps(
                {
                    "name": "cursor-autopilot",
                    "version": "0.1.0",
                    "skills": {"directory": "skills"},
                    "hooks": {"directory": "hooks"},
                }
            ),
            encoding="utf-8",
        )
        (tmp_path / ".claude-plugin").mkdir()
        (tmp_path / ".claude-plugin" / "plugin.json").write_text(
            json.dumps(
                {
                    "name": "claude-autopilot",
                    "version": "0.1.0",
                    "skills": {"directory": "skills"},
                    "hooks": {"directory": "hooks"},
                }
            ),
            encoding="utf-8",
        )
        manifests = list_compatible_plugins(tmp_path)
        names = {m.name for m in manifests}
        assert names == {"cursor-autopilot", "claude-autopilot"}

    def test_ignores_invalid_manifests(self, tmp_path: Path) -> None:
        (tmp_path / ".bad-plugin").mkdir()
        (tmp_path / ".bad-plugin" / "plugin.json").write_text("bad json", encoding="utf-8")
        manifests = list_compatible_plugins(tmp_path)
        assert manifests == []

    def test_no_plugins(self, tmp_path: Path) -> None:
        assert list_compatible_plugins(tmp_path) == []
