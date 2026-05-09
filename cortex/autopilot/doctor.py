"""cortex.autopilot.doctor — Diagnostic toolkit for Autopilot installation.

Read-only checks.  Does not modify files unless an explicit repair flag
is passed (and even then, only with user confirmation).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from cortex.workspace.layout import WorkspaceLayout
from cortex.autopilot.adapters.registry import list_adapters
from cortex.autopilot.config import load_autopilot_config
from cortex.autopilot.service import AutopilotService


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
            action="Run `cortex setup agent` or create config.yaml",
        )


def _check_run_dir(layout: WorkspaceLayout) -> DoctorCheck:
    run_dir = layout.workspace_root / "run" / "autopilot"
    try:
        run_dir.mkdir(parents=True, exist_ok=True)
        if os.access(run_dir, os.W_OK):
            return DoctorCheck(name="run_dir", ok=True, detail=str(run_dir))
        return DoctorCheck(
            name="run_dir",
            ok=False,
            detail=f"Run directory not writable: {run_dir}",
            action="Ensure the workspace root is writable",
        )
    except Exception as exc:
        return DoctorCheck(
            name="run_dir",
            ok=False,
            detail=str(exc),
            action="Ensure the workspace root is writable",
        )


def _check_skills(layout: WorkspaceLayout) -> DoctorCheck:
    skills_dir = layout.skills_dir
    required = {"using-cortex-autopilot"}
    found = {p.stem for p in skills_dir.glob("*.md")} if skills_dir.exists() else set()
    missing = required - found
    if missing:
        return DoctorCheck(
            name="skills",
            ok=False,
            detail=f"Missing skills: {missing}",
            action="Run `cortex autopilot install` or copy skills manually",
        )
    return DoctorCheck(name="skills", ok=True, detail=f"Found: {found}")


def _check_hooks_installed(layout: WorkspaceLayout) -> DoctorCheck:
    """Detect which adapters have hooks installed in the workspace."""
    installed: list[str] = []
    repo = layout.repo_root

    # Cursor
    if (repo / ".cursorrules").exists():
        text = (repo / ".cursorrules").read_text(encoding="utf-8")
        if "AUTOPILOT-CURSOR" in text:
            installed.append("cursor")

    # Claude Code
    if (repo / ".claude" / "autopilot-hook.md").exists():
        installed.append("claude-code")

    # OpenCode
    if (repo / ".opencode" / "hooks.md").exists():
        text = (repo / ".opencode" / "hooks.md").read_text(encoding="utf-8")
        if "AUTOPILOT-OPENCODE" in text:
            installed.append("opencode")

    # Codex
    if (repo / ".codex" / "autopilot.md").exists():
        installed.append("codex")

    # Pi
    if (repo / ".pi" / "settings.json").exists():
        import json
        try:
            data = json.loads((repo / ".pi" / "settings.json").read_text(encoding="utf-8"))
            exts = data.get("defaultExtensions", [])
            if "extensions/cortex-autopilot.ts" in exts:
                installed.append("pi")
        except Exception:
            pass

    if installed:
        return DoctorCheck(
            name="hooks",
            ok=True,
            detail=f"Installed adapters: {installed}",
        )
    return DoctorCheck(
        name="hooks",
        ok=False,
        detail="No Autopilot hooks detected",
        action="Run `cortex autopilot install --ide <name>`",
    )


def _check_adapter_recognized(layout: WorkspaceLayout) -> DoctorCheck:
    known = list_adapters()
    return DoctorCheck(
        name="adapters",
        ok=True,
        detail=f"Known adapters: {known}",
    )


def _check_mcp_tools() -> DoctorCheck:
    try:
        from cortex.mcp.server import CortexMCPServer
        return DoctorCheck(name="mcp_tools", ok=True, detail="CortexMCPServer importable")
    except Exception as exc:
        return DoctorCheck(
            name="mcp_tools",
            ok=False,
            detail=str(exc),
            action="Check MCP dependencies are installed",
        )


def _check_last_finish(layout: WorkspaceLayout) -> DoctorCheck:
    try:
        svc = AutopilotService.from_project_root(layout.repo_root)
        st = svc.status()
        if st.active and st.state:
            if st.state.status in ("documented", "finished"):
                return DoctorCheck(
                    name="last_finish",
                    ok=True,
                    detail=f"Session {st.state.session_id} status={st.state.status}",
                )
            return DoctorCheck(
                name="last_finish",
                ok=False,
                detail=f"Latest session {st.state.session_id} status={st.state.status} (not closed)",
                action="Run `cortex autopilot finish --session-id <id>`",
            )
        return DoctorCheck(
            name="last_finish",
            ok=False,
            detail="No sessions found",
        )
    except Exception as exc:
        return DoctorCheck(name="last_finish", ok=False, detail=str(exc))


def _check_budget_warnings(layout: WorkspaceLayout) -> DoctorCheck:
    try:
        svc = AutopilotService.from_project_root(layout.repo_root)
        st = svc.status()
        if st.active and st.state and st.state.warnings:
            return DoctorCheck(
                name="budget_warnings",
                ok=False,
                detail=f"{len(st.state.warnings)} warning(s): {'; '.join(st.state.warnings)}",
                action="Review session warnings and adjust budget profile",
            )
        return DoctorCheck(name="budget_warnings", ok=True, detail="No warnings")
    except Exception as exc:
        return DoctorCheck(name="budget_warnings", ok=False, detail=str(exc))


def _check_superpowers_conflict(layout: WorkspaceLayout) -> DoctorCheck:
    repo = layout.repo_root
    indicators = [
        repo / ".claude" / "plugins" / "superpowers",
        repo / ".cursor" / "plugins" / "superpowers",
    ]
    if os.environ.get("CLAUDE_PLUGIN_ROOT", "").endswith("superpowers"):
        return DoctorCheck(
            name="superpowers_conflict",
            ok=False,
            detail="Superpowers detected via CLAUDE_PLUGIN_ROOT env var",
            action="Disable one plugin: `cortex autopilot uninstall` or remove Superpowers",
        )
    for path in indicators:
        if path.exists():
            return DoctorCheck(
                name="superpowers_conflict",
                ok=False,
                detail=f"Superpowers detected at {path}",
                action="Disable one plugin: `cortex autopilot uninstall` or remove Superpowers",
            )
    return DoctorCheck(name="superpowers_conflict", ok=True, detail="No conflict detected")


def _check_jsonl_rotation(layout: WorkspaceLayout) -> DoctorCheck:
    events_dir = layout.workspace_root / "run" / "autopilot" / "events"
    if not events_dir.exists():
        return DoctorCheck(name="jsonl_rotation", ok=True, detail="No events dir yet")

    oversized: list[str] = []
    old_files: list[str] = []
    for path in events_dir.glob("*.jsonl"):
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > 5:
            oversized.append(f"{path.name} ({size_mb:.1f}MB)")
        # Check age (simple mtime check, > 30 days)
        import time
        age_days = (time.time() - path.stat().st_mtime) / 86400
        if age_days > 30:
            old_files.append(f"{path.name} ({age_days:.0f}d)")

    details: list[str] = []
    if oversized:
        details.append(f"Oversized (>5MB): {oversized}")
    if old_files:
        details.append(f"Old (>30d): {old_files}")

    if details:
        return DoctorCheck(
            name="jsonl_rotation",
            ok=False,
            detail="; ".join(details),
            action="Run `cortex autopilot cleanup --older-than 30`",
        )
    return DoctorCheck(name="jsonl_rotation", ok=True, detail="All JSONL files within limits")


def run_diagnosis(project_root: Path | None = None) -> DoctorReport:
    """Run all diagnostic checks and return a ``DoctorReport``."""
    root = project_root or Path.cwd()
    layout = WorkspaceLayout.discover(root)

    checks = [
        _check_config(layout),
        _check_run_dir(layout),
        _check_skills(layout),
        _check_hooks_installed(layout),
        _check_adapter_recognized(layout),
        _check_mcp_tools(),
        _check_last_finish(layout),
        _check_budget_warnings(layout),
        _check_superpowers_conflict(layout),
        _check_jsonl_rotation(layout),
    ]

    warnings = [c.detail for c in checks if not c.ok]
    return DoctorReport(
        ok=all(c.ok for c in checks),
        checks=checks,
        warnings=warnings,
    )
