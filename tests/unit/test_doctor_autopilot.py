"""Tests for the Phase-03 doctor extensions (T3.12).

Covers ``_validate_autopilot_policy`` and ``_validate_session_hooks`` —
the two check groups added to ``cortex doctor`` by the Pluggable Middle
Fase 03.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from cortex.doctor import (
    _validate_autopilot_policy,
    _validate_session_hooks,
    run_doctor,
)
from cortex.session.hooks import default_installer
from cortex.workspace.layout import WorkspaceLayout


@pytest.fixture
def cortex_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".cortex" / "sessions").mkdir(parents=True)
    (repo / "config.yaml").write_text(
        "episodic:\n  persist_dir: .memory/chroma\n", encoding="utf-8"
    )
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "e@e"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "e"], cwd=repo, check=True)
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "i"], cwd=repo, check=True)
    return repo


# ── _validate_autopilot_policy ────────────────────────────────────────


class TestValidateAutopilotPolicy:
    def test_default_config_reports_assist(self, cortex_repo: Path) -> None:
        layout = WorkspaceLayout.discover(cortex_repo)
        checks = _validate_autopilot_policy(layout)
        names = {c.name for c in checks}
        assert "autopilot_policy" in names
        policy_check = next(c for c in checks if c.name == "autopilot_policy")
        assert policy_check.ok is True
        assert "mode=assist" in policy_check.detail

    def test_known_mode_does_not_warn(self, cortex_repo: Path) -> None:
        (cortex_repo / "autopilot.yaml").write_text("mode: autopilot\n", encoding="utf-8")
        layout = WorkspaceLayout.discover(cortex_repo)
        checks = _validate_autopilot_policy(layout)
        names = {c.name for c in checks}
        assert "autopilot_mode_typo" not in names

    def test_typo_in_mode_surfaces_warning(self, cortex_repo: Path) -> None:
        (cortex_repo / "autopilot.yaml").write_text("mode: hyperdrive\n", encoding="utf-8")
        layout = WorkspaceLayout.discover(cortex_repo)
        checks = _validate_autopilot_policy(layout)
        typo = [c for c in checks if c.name == "autopilot_mode_typo"]
        assert len(typo) == 1
        assert typo[0].ok is False
        assert "hyperdrive" in typo[0].detail


# ── _validate_session_hooks ──────────────────────────────────────────


class TestValidateSessionHooks:
    def test_reports_no_hooks_when_clean(self, cortex_repo: Path) -> None:
        layout = WorkspaceLayout.discover(cortex_repo)
        checks = _validate_session_hooks(layout)
        installed_check = next(c for c in checks if c.name == "session_hooks_installed")
        assert installed_check.ok is False
        assert "none installed" in installed_check.detail

    def test_reports_installed_after_install(self, cortex_repo: Path) -> None:
        default_installer().install("cursor", cortex_repo)
        layout = WorkspaceLayout.discover(cortex_repo)
        checks = _validate_session_hooks(layout)
        installed_check = next(c for c in checks if c.name == "session_hooks_installed")
        assert installed_check.ok is True
        assert "cursor" in installed_check.detail

    def test_recent_events_appears_when_session_active(
        self, cortex_repo: Path
    ) -> None:
        from cortex.session.service import SessionService
        from cortex.session.storage import SessionStorage

        spec = cortex_repo / "vault" / "specs" / "2026-05-16_demo.md"
        spec.parent.mkdir(parents=True)
        spec.write_text("# demo\n", encoding="utf-8")
        storage = SessionStorage(cortex_repo / ".cortex" / "sessions")
        svc = SessionService(storage, cortex_repo)
        svc.open(spec_id="2026-05-16_demo", spec_path=spec, spec_summary="demo")
        layout = WorkspaceLayout.discover(cortex_repo)
        checks = _validate_session_hooks(layout)
        names = {c.name for c in checks}
        assert "session_hooks_recent_events" in names


# ── run_doctor integration ───────────────────────────────────────────


class TestRunDoctorIntegration:
    def test_run_doctor_includes_phase_03_checks(self, cortex_repo: Path) -> None:
        report = run_doctor(cortex_repo)
        names = {c.name for c in report.checks}
        assert "autopilot_policy" in names
        assert "session_hooks_installed" in names


# ── Phase 04 pm_* checks ─────────────────────────────────────────────


class TestPluggableMiddleHealth:
    def test_pluggable_middle_checks_present(self, cortex_repo: Path) -> None:
        report = run_doctor(cortex_repo)
        names = {c.name for c in report.checks}
        expected = {
            "pm_workspace_layout_v2",
            "pm_documenter_module",
            "pm_documenter_interactive",
            "pm_documenter_default_mode",
            "pm_verification_runner",
            "pm_mcp_tools_registered",
        }
        assert expected.issubset(names), f"missing: {expected - names}"

    def test_documenter_module_check_passes(self, cortex_repo: Path) -> None:
        report = run_doctor(cortex_repo)
        check = next(c for c in report.checks if c.name == "pm_documenter_module")
        assert check.ok is True

    def test_documenter_interactive_check_passes(self, cortex_repo: Path) -> None:
        report = run_doctor(cortex_repo)
        check = next(c for c in report.checks if c.name == "pm_documenter_interactive")
        assert check.ok is True

    def test_default_mode_check_default_auto(self, cortex_repo: Path) -> None:
        report = run_doctor(cortex_repo)
        check = next(c for c in report.checks if c.name == "pm_documenter_default_mode")
        assert check.ok is True
        assert "auto" in check.detail

    def test_default_mode_check_interactive(self, cortex_repo: Path) -> None:
        cfg = cortex_repo / "config.yaml"
        cfg.write_text(
            "episodic:\n  persist_dir: .memory/chroma\n"
            "documenter:\n  default_mode: interactive\n",
            encoding="utf-8",
        )
        report = run_doctor(cortex_repo)
        check = next(c for c in report.checks if c.name == "pm_documenter_default_mode")
        assert check.ok is True
        assert "interactive" in check.detail

    def test_default_mode_check_invalid_warns(self, cortex_repo: Path) -> None:
        cfg = cortex_repo / "config.yaml"
        cfg.write_text(
            "episodic:\n  persist_dir: .memory/chroma\n"
            "documenter:\n  default_mode: cuckoo\n",
            encoding="utf-8",
        )
        report = run_doctor(cortex_repo)
        check = next(c for c in report.checks if c.name == "pm_documenter_default_mode")
        assert check.ok is False
        assert "cuckoo" in check.detail

    def test_mcp_tools_registered_check_passes(self, cortex_repo: Path) -> None:
        report = run_doctor(cortex_repo)
        check = next(c for c in report.checks if c.name == "pm_mcp_tools_registered")
        assert check.ok is True
        assert "registered" in check.detail

    def test_verification_runner_check_passes(self, cortex_repo: Path) -> None:
        report = run_doctor(cortex_repo)
        check = next(c for c in report.checks if c.name == "pm_verification_runner")
        assert check.ok is True
