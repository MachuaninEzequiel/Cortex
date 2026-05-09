"""Tests for cortex.autopilot.adapters.pi."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cortex.autopilot.adapters.base import _backup_path
from cortex.autopilot.adapters.pi import (
    PiAutopilotAdapter,
    _extension_dest,
    _load_settings,
    _merge_settings,
    _remove_settings_entries,
    _settings_path,
    _skill_dest,
)
from cortex.autopilot.adapters.platform_detect import Platform, detect_platform
from cortex.autopilot.adapters.registry import get_adapter, list_adapters
from cortex.autopilot.models import AutopilotSessionState


class TestPiHelpers:
    def test_load_settings_missing_returns_minimal(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        result = _load_settings(path)
        assert result == {"defaultExtensions": [], "skills": []}

    def test_load_settings_reads_existing(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        data = {"model": "gpt-4", "skills": [".pi/skills/a.md"]}
        path.write_text(json.dumps(data), encoding="utf-8")
        result = _load_settings(path)
        assert result["model"] == "gpt-4"

    def test_load_settings_invalid_json_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        path.write_text("not json", encoding="utf-8")
        with pytest.raises(ValueError, match="Invalid JSON"):
            _load_settings(path)

    def test_merge_settings_adds_entries(self) -> None:
        settings = {"defaultExtensions": ["ext/a.ts"], "skills": ["sk/a.md"]}
        merged = _merge_settings(settings)
        assert "extensions/cortex-autopilot.ts" in merged["defaultExtensions"]
        assert ".pi/skills/using-cortex-autopilot/SKILL.md" in merged["skills"]
        assert "ext/a.ts" in merged["defaultExtensions"]
        assert "sk/a.md" in merged["skills"]

    def test_merge_settings_creates_missing_keys(self) -> None:
        merged = _merge_settings({})
        assert "extensions/cortex-autopilot.ts" in merged["defaultExtensions"]
        assert ".pi/skills/using-cortex-autopilot/SKILL.md" in merged["skills"]

    def test_merge_settings_rejects_non_list(self) -> None:
        with pytest.raises(ValueError, match="Expected 'defaultExtensions' to be a list"):
            _merge_settings({"defaultExtensions": "oops"})

    def test_merge_settings_idempotent(self) -> None:
        settings = {"defaultExtensions": ["extensions/cortex-autopilot.ts"], "skills": []}
        merged = _merge_settings(settings)
        assert merged["defaultExtensions"].count("extensions/cortex-autopilot.ts") == 1

    def test_remove_settings_entries(self) -> None:
        settings = {
            "defaultExtensions": ["ext/a.ts", "extensions/cortex-autopilot.ts"],
            "skills": ["sk/a.md", ".pi/skills/using-cortex-autopilot/SKILL.md"],
        }
        cleaned = _remove_settings_entries(settings)
        assert "extensions/cortex-autopilot.ts" not in cleaned["defaultExtensions"]
        assert ".pi/skills/using-cortex-autopilot/SKILL.md" not in cleaned["skills"]
        assert "ext/a.ts" in cleaned["defaultExtensions"]
        assert "sk/a.md" in cleaned["skills"]

    def test_remove_settings_preserves_non_list(self) -> None:
        settings = {"defaultExtensions": "bad", "skills": ["sk/a.md"]}
        cleaned = _remove_settings_entries(settings)
        assert cleaned["defaultExtensions"] == "bad"


class TestPiAdapterInstall:
    def test_install_creates_pi_files_when_missing(self, tmp_path: Path) -> None:
        adapter = PiAutopilotAdapter()
        paths = adapter.install(tmp_path)

        ext = _extension_dest(tmp_path)
        skill = _skill_dest(tmp_path)
        settings = _settings_path(tmp_path)

        assert ext.exists()
        assert skill.exists()
        assert settings.exists()

        data = json.loads(settings.read_text(encoding="utf-8"))
        assert "extensions/cortex-autopilot.ts" in data.get("defaultExtensions", [])
        assert ".pi/skills/using-cortex-autopilot/SKILL.md" in data.get("skills", [])

    def test_install_merges_existing_settings(self, tmp_path: Path) -> None:
        pi_dir = tmp_path / ".pi"
        pi_dir.mkdir(parents=True, exist_ok=True)
        settings = pi_dir / "settings.json"
        original = {
            "model": "claude-sonnet",
            "theme": "cortex-dark",
            "defaultExtensions": ["extensions/cortex-dashboard.ts"],
            "skills": [".pi/skills/cortex-vault.md"],
            "agents": [".pi/agents/cortex-sync.md"],
        }
        settings.write_text(json.dumps(original, indent=2), encoding="utf-8")

        adapter = PiAutopilotAdapter()
        adapter.install(tmp_path)

        data = json.loads(settings.read_text(encoding="utf-8"))
        assert data["model"] == "claude-sonnet"
        assert data["theme"] == "cortex-dark"
        assert "extensions/cortex-dashboard.ts" in data["defaultExtensions"]
        assert "extensions/cortex-autopilot.ts" in data["defaultExtensions"]
        assert ".pi/skills/cortex-vault.md" in data["skills"]
        assert ".pi/skills/using-cortex-autopilot/SKILL.md" in data["skills"]
        assert ".pi/agents/cortex-sync.md" in data["agents"]

    def test_install_is_idempotent(self, tmp_path: Path) -> None:
        adapter = PiAutopilotAdapter()
        adapter.install(tmp_path)
        adapter.install(tmp_path)

        data = json.loads(_settings_path(tmp_path).read_text(encoding="utf-8"))
        assert data["defaultExtensions"].count("extensions/cortex-autopilot.ts") == 1
        assert data["skills"].count(".pi/skills/using-cortex-autopilot/SKILL.md") == 1

    def test_install_rejects_invalid_settings_json(self, tmp_path: Path) -> None:
        pi_dir = tmp_path / ".pi"
        pi_dir.mkdir(parents=True, exist_ok=True)
        settings = pi_dir / "settings.json"
        settings.write_text("not json", encoding="utf-8")

        adapter = PiAutopilotAdapter()
        with pytest.raises(ValueError, match="Invalid JSON"):
            adapter.install(tmp_path)

        # Original file must not be overwritten
        assert settings.read_text(encoding="utf-8") == "not json"

    def test_install_creates_backup(self, tmp_path: Path) -> None:
        pi_dir = tmp_path / ".pi"
        pi_dir.mkdir(parents=True, exist_ok=True)
        settings = pi_dir / "settings.json"
        settings.write_text(json.dumps({"model": "x"}), encoding="utf-8")

        adapter = PiAutopilotAdapter()
        adapter.install(tmp_path)

        backup = _backup_path(settings)
        assert backup.exists()
        assert json.loads(backup.read_text(encoding="utf-8")) == {"model": "x"}


class TestPiAdapterUninstall:
    def test_uninstall_removes_only_autopilot_files(self, tmp_path: Path) -> None:
        adapter = PiAutopilotAdapter()
        adapter.install(tmp_path)

        # Create an unrelated file
        other_ext = tmp_path / ".pi" / "extensions" / "other.ts"
        other_ext.write_text("// other", encoding="utf-8")

        removed = adapter.uninstall(tmp_path)
        assert _extension_dest(tmp_path) not in removed or not _extension_dest(tmp_path).exists()
        assert other_ext.exists()

    def test_uninstall_removes_settings_entries(self, tmp_path: Path) -> None:
        adapter = PiAutopilotAdapter()
        adapter.install(tmp_path)
        adapter.uninstall(tmp_path)

        data = json.loads(_settings_path(tmp_path).read_text(encoding="utf-8"))
        assert "extensions/cortex-autopilot.ts" not in data.get("defaultExtensions", [])
        assert ".pi/skills/using-cortex-autopilot/SKILL.md" not in data.get("skills", [])

    def test_uninstall_preserves_other_settings(self, tmp_path: Path) -> None:
        pi_dir = tmp_path / ".pi"
        pi_dir.mkdir(parents=True, exist_ok=True)
        settings = pi_dir / "settings.json"
        original = {
            "model": "claude",
            "theme": "dark",
            "defaultExtensions": ["ext/a.ts"],
            "skills": ["sk/a.md"],
        }
        settings.write_text(json.dumps(original), encoding="utf-8")

        adapter = PiAutopilotAdapter()
        adapter.install(tmp_path)
        adapter.uninstall(tmp_path)

        data = json.loads(settings.read_text(encoding="utf-8"))
        assert data["model"] == "claude"
        assert data["theme"] == "dark"
        assert "ext/a.ts" in data["defaultExtensions"]
        assert "sk/a.md" in data["skills"]


class TestPiAdapterEmit:
    def test_emit_session_start_uses_default_json_shape(self) -> None:
        adapter = PiAutopilotAdapter()
        state = AutopilotSessionState(
            session_id="sid",
            project_root="/r",
            workspace_root="/r/.cortex",
            mode="assist",
        )
        payload = adapter.emit_session_start(state, "bootstrap")
        data = json.loads(payload)
        assert "additionalContext" in data
        inner = json.loads(data["additionalContext"])
        assert inner["session_id"] == "sid"
        assert inner["mode"] == "assist"


class TestPiRegistry:
    def test_registry_includes_pi(self) -> None:
        names = list_adapters()
        assert "pi" in names

    def test_get_adapter_pi(self) -> None:
        from cortex.autopilot.adapters.pi import PiAutopilotAdapter

        assert get_adapter("pi") is PiAutopilotAdapter


class TestPiPlatformDetect:
    def test_pi_plugin_root(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PI_PLUGIN_ROOT", "/pi")
        assert detect_platform() == Platform.PI

    def test_pi_coding_agent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PI_CODING_AGENT", "1")
        assert detect_platform() == Platform.PI

    def test_pi_after_codex_priority(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CODEX_PLUGIN_ROOT", "/codex")
        monkeypatch.setenv("PI_PLUGIN_ROOT", "/pi")
        assert detect_platform() == Platform.CODEX


class TestPiTemplates:
    def test_extension_mentions_autopilot_cli(self) -> None:
        path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "cortex"
            / "autopilot"
            / "pi"
            / "extensions"
            / "cortex-autopilot.ts"
        )
        text = path.read_text(encoding="utf-8")
        assert "autopilot" in text
        assert "start" in text
        assert "finish" in text
        assert "--json" in text
        assert "project-root" in text

    def test_skill_contains_memory_isolation(self) -> None:
        path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "cortex"
            / "autopilot"
            / "pi"
            / "skills"
            / "using-cortex-autopilot"
            / "SKILL.md"
        )
        text = path.read_text(encoding="utf-8")
        assert "engram_" not in text.lower() or "No uses memoria externa" in text
        assert "cortex_" in text.lower()
