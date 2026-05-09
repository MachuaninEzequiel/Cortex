"""Tests for cortex.autopilot.doctor and reporting."""
from __future__ import annotations

from pathlib import Path

import pytest

from cortex.autopilot.doctor import run_diagnosis, DoctorCheck
from cortex.autopilot.reporting import generate_report


class TestDoctor:
    def test_run_diagnosis_basic(self, tmp_path: Path) -> None:
        report = run_diagnosis(tmp_path)
        assert isinstance(report.ok, bool)
        assert len(report.checks) > 0
        check_names = {c.name for c in report.checks}
        assert "config" in check_names
        assert "run_dir" in check_names
        assert "skills" in check_names
        assert "hooks" in check_names
        assert "adapters" in check_names
        assert "mcp_tools" in check_names
        assert "last_finish" in check_names
        assert "budget_warnings" in check_names
        assert "superpowers_conflict" in check_names
        assert "jsonl_rotation" in check_names

    def test_superpowers_conflict_detected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", "/plugins/superpowers")
        report = run_diagnosis(tmp_path)
        sp_check = next(c for c in report.checks if c.name == "superpowers_conflict")
        assert sp_check.ok is False
        assert "Superpowers" in sp_check.detail

    def test_superpowers_conflict_not_detected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
        report = run_diagnosis(tmp_path)
        sp_check = next(c for c in report.checks if c.name == "superpowers_conflict")
        assert sp_check.ok is True

    def test_hooks_detect_cursor(self, tmp_path: Path) -> None:
        cursorrules = tmp_path / ".cursorrules"
        cursorrules.write_text("<!-- AUTOPILOT-CURSOR -->\n", encoding="utf-8")
        report = run_diagnosis(tmp_path)
        hooks_check = next(c for c in report.checks if c.name == "hooks")
        assert hooks_check.ok is True
        assert "cursor" in hooks_check.detail

    def test_hooks_detect_pi(self, tmp_path: Path) -> None:
        pi_dir = tmp_path / ".pi"
        pi_dir.mkdir(parents=True, exist_ok=True)
        settings = pi_dir / "settings.json"
        settings.write_text(
            '{"defaultExtensions": ["extensions/cortex-autopilot.ts"]}',
            encoding="utf-8",
        )
        report = run_diagnosis(tmp_path)
        hooks_check = next(c for c in report.checks if c.name == "hooks")
        assert hooks_check.ok is True
        assert "pi" in hooks_check.detail

    def test_jsonl_rotation_warning_on_oversized(self, tmp_path: Path) -> None:
        run_dir = tmp_path / ".cortex" / "run" / "autopilot" / "events"
        run_dir.mkdir(parents=True, exist_ok=True)
        big_file = run_dir / "s1.jsonl"
        big_file.write_text("x" * (6 * 1024 * 1024), encoding="utf-8")  # 6MB
        report = run_diagnosis(tmp_path)
        rot_check = next(c for c in report.checks if c.name == "jsonl_rotation")
        assert rot_check.ok is False
        assert "Oversized" in rot_check.detail

    def test_adapters_listed(self, tmp_path: Path) -> None:
        report = run_diagnosis(tmp_path)
        adapter_check = next(c for c in report.checks if c.name == "adapters")
        assert adapter_check.ok is True
        assert "cursor" in adapter_check.detail

    def test_mcp_tools_importable(self, tmp_path: Path) -> None:
        report = run_diagnosis(tmp_path)
        mcp_check = next(c for c in report.checks if c.name == "mcp_tools")
        assert mcp_check.ok is True

    def test_skills_missing(self, tmp_path: Path) -> None:
        report = run_diagnosis(tmp_path)
        skills_check = next(c for c in report.checks if c.name == "skills")
        assert skills_check.ok is False
        assert "using-cortex-autopilot" in skills_check.detail


class TestReporting:
    def test_generate_report_empty(self, tmp_path: Path) -> None:
        reports = generate_report(tmp_path, last_n=10)
        assert reports == []

    def test_generate_report_with_session(self, tmp_path: Path) -> None:
        from cortex.autopilot.lifecycle import StartRequest
        from cortex.autopilot.service import AutopilotService

        svc = AutopilotService.from_project_root(tmp_path)
        start_res = svc.start(
            StartRequest(project_root=str(tmp_path), workspace_root=str(tmp_path))
        )
        reports = generate_report(tmp_path, last_n=10)
        assert len(reports) == 1
        assert reports[0].session_id == start_res.session_id
        assert reports[0].status == "started"

    def test_generate_report_limits_last_n(self, tmp_path: Path) -> None:
        from cortex.autopilot.lifecycle import StartRequest
        from cortex.autopilot.service import AutopilotService

        svc = AutopilotService.from_project_root(tmp_path)
        for _ in range(5):
            svc.start(StartRequest(project_root=str(tmp_path), workspace_root=str(tmp_path)))

        reports = generate_report(tmp_path, last_n=3)
        assert len(reports) == 3


class TestCleanup:
    def test_cleanup_archives_old_files(self, tmp_path: Path) -> None:
        import time
        from cortex.autopilot.state_store import StateStore
        from cortex.workspace.layout import WorkspaceLayout

        # Create workspace layout
        workspace = tmp_path / ".cortex"
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "workspace.yaml").write_text("layout_version: 2\n", encoding="utf-8")

        layout = WorkspaceLayout.discover(tmp_path)
        store = StateStore(layout.workspace_root)

        events_dir = layout.workspace_root / "run" / "autopilot" / "events"
        events_dir.mkdir(parents=True, exist_ok=True)

        old_file = events_dir / "old.jsonl"
        old_file.write_text("event\n", encoding="utf-8")
        # Set mtime to 40 days ago
        old_mtime = time.time() - 40 * 86400
        old_file.touch()
        import os
        os.utime(old_file, (old_mtime, old_mtime))

        result = store.cleanup(older_than_days=30)
        assert len(result["archived"]) == 1
        assert not old_file.exists()

    def test_cleanup_archives_oversized(self, tmp_path: Path) -> None:
        from cortex.autopilot.state_store import StateStore
        from cortex.workspace.layout import WorkspaceLayout

        workspace = tmp_path / ".cortex"
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "workspace.yaml").write_text("layout_version: 2\n", encoding="utf-8")

        layout = WorkspaceLayout.discover(tmp_path)
        store = StateStore(layout.workspace_root)

        events_dir = layout.workspace_root / "run" / "autopilot" / "events"
        events_dir.mkdir(parents=True, exist_ok=True)

        big_file = events_dir / "big.jsonl"
        big_file.write_text("x" * (6 * 1024 * 1024), encoding="utf-8")

        result = store.cleanup(older_than_days=30, max_size_mb=5.0)
        assert len(result["archived"]) == 1
        assert not big_file.exists()
