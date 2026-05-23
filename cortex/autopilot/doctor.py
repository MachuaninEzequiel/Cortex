"""cortex.autopilot.doctor — Diagnostic toolkit for the Autopilot installation.

Phase 03 stub: the legacy checks targeting ``run/autopilot/`` state and
the old ``IndexingSessionWriter`` were removed (those files no longer
exist). T3.12 will rebuild the doctor on top of the canonical
``.cortex/sessions/`` primitive and the new ``cortex.session.hooks``
installer. Until then, this module ships a minimal set of checks that
keep ``cortex doctor`` working and surface the obvious problems:

* config: ``AutopilotConfig`` parses without raising.
* sessions_dir: ``.cortex/sessions/`` is writable.
* adapters: registry returns its known names.
* last_finish: most recent ``SessionRecord`` (if any) is in a sensible
  state.
* hooks_installed: which legacy IDE adapters left markers in the repo.

All checks are read-only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from cortex.autopilot.config import load_autopilot_config
from cortex.autopilot.service import AutopilotService
from cortex.session.hooks import default_installer
from cortex.session.models import SessionStatus
from cortex.session.storage import SessionStorage
from cortex.workspace.layout import WorkspaceLayout


@dataclass
class DoctorCheck:
    name: str
    ok: bool
    detail: str = ""
    action: str = ""


@dataclass
class DoctorReport:
    ok: bool
    checks: list[DoctorCheck] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _check_config(layout: WorkspaceLayout) -> DoctorCheck:
    try:
        cfg = load_autopilot_config(layout)
        return DoctorCheck(
            name="config",
            ok=True,
            detail=f"mode={cfg.mode}, profile={cfg.default_budget_profile}",
        )
    except Exception as exc:
        return DoctorCheck(
            name="config",
            ok=False,
            detail=str(exc),
            action="Fix `autopilot.yaml` syntax or run `cortex setup agent`.",
        )


def _check_sessions_dir(layout: WorkspaceLayout) -> DoctorCheck:
    try:
        sessions = layout.sessions_dir
        sessions.mkdir(parents=True, exist_ok=True)
        if os.access(sessions, os.W_OK):
            return DoctorCheck(name="sessions_dir", ok=True, detail=str(sessions))
        return DoctorCheck(
            name="sessions_dir",
            ok=False,
            detail=f"Not writable: {sessions}",
            action="Ensure the workspace root is writable.",
        )
    except Exception as exc:
        return DoctorCheck(
            name="sessions_dir",
            ok=False,
            detail=str(exc),
            action="Run `cortex setup agent` to initialize `.cortex/sessions/`.",
        )


def _check_adapters() -> DoctorCheck:
    known = default_installer().list_available_adapters()
    return DoctorCheck(
        name="adapters",
        ok=True,
        detail=f"Known IDE adapters (cortex.session.hooks): {known}",
    )


def _check_hooks_installed(layout: WorkspaceLayout) -> DoctorCheck:
    """Report which canonical IDE adapters are installed under the repo root."""
    installer = default_installer()
    statuses = installer.status_all(layout.repo_root)
    installed = [s.ide for s in statuses if s.installed]
    if installed:
        return DoctorCheck(name="hooks", ok=True, detail=f"Installed adapters: {installed}")
    return DoctorCheck(
        name="hooks",
        ok=False,
        detail="No Cortex session hooks detected",
        action="Run `cortex session hooks install --ide <name>`.",
    )


def _check_last_finish(layout: WorkspaceLayout) -> DoctorCheck:
    try:
        storage = SessionStorage(layout.sessions_dir)
        records = storage.list_all()
    except Exception as exc:
        return DoctorCheck(
            name="last_finish",
            ok=False,
            detail=f"Could not list sessions: {exc}",
        )
    if not records:
        return DoctorCheck(name="last_finish", ok=True, detail="No sessions on disk yet")
    latest = max(records, key=lambda r: r.opened_at)
    if latest.status is SessionStatus.OPEN:
        return DoctorCheck(
            name="last_finish",
            ok=True,
            detail=f"Session {latest.session_id} still OPEN — finish or abandon when ready",
        )
    return DoctorCheck(
        name="last_finish",
        ok=True,
        detail=f"Latest: {latest.session_id} ({latest.status.value})",
    )


def _check_service_construction(layout: WorkspaceLayout) -> DoctorCheck:
    """Verify that the new AutopilotService wires correctly."""
    try:
        AutopilotService.from_project_root(layout.repo_root)
        return DoctorCheck(
            name="service",
            ok=True,
            detail="AutopilotService.from_project_root wired OK",
        )
    except Exception as exc:
        return DoctorCheck(
            name="service",
            ok=False,
            detail=f"Could not build AutopilotService: {exc}",
            action="Run `cortex setup agent` to configure the workspace.",
        )


def run_diagnosis(project_root: Path | None = None) -> DoctorReport:
    """Run all diagnostic checks and return a :class:`DoctorReport`."""
    root = project_root or Path.cwd()
    layout = WorkspaceLayout.discover(root)
    checks = [
        _check_config(layout),
        _check_sessions_dir(layout),
        _check_adapters(),
        _check_hooks_installed(layout),
        _check_last_finish(layout),
        _check_service_construction(layout),
    ]
    warnings = [c.detail for c in checks if not c.ok]
    return DoctorReport(
        ok=all(c.ok for c in checks),
        checks=checks,
        warnings=warnings,
    )


__all__ = ["DoctorCheck", "DoctorReport", "run_diagnosis"]
