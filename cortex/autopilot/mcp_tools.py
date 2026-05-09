"""cortex.autopilot.mcp_tools — MCP tool wrappers for Autopilot.

All tools delegate to ``AutopilotService``.  No business logic is duplicated.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cortex.autopilot.errors import AutopilotError, SessionNotFoundError
from cortex.autopilot.lifecycle import (
    CheckpointRequest,
    FinishRequest,
    PreflightRequest,
    StartRequest,
)
from cortex.autopilot.service import AutopilotService


class AutopilotMCPTools:
    """Thin MCP adapters for the Autopilot lifecycle.

    Each method receives the raw *arguments* dict from the MCP layer,
    validates required fields, delegates to ``AutopilotService``, and
    returns a compact human-readable string.
    """

    def __init__(self, service: AutopilotService) -> None:
        self._svc = service

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _req(arguments: dict[str, Any], key: str) -> Any:
        """Return *key* from *arguments* or raise ValueError."""
        if key not in arguments or arguments[key] is None:
            raise ValueError(f"Missing required argument: {key}")
        return arguments[key]

    @staticmethod
    def _opt(arguments: dict[str, Any], key: str, default: Any = None) -> Any:
        return arguments.get(key, default)

    @staticmethod
    def _str_list(arguments: dict[str, Any], key: str) -> list[str]:
        val = arguments.get(key, [])
        if not isinstance(val, list):
            return []
        return [str(v) for v in val if v is not None]

    # ------------------------------------------------------------------
    # start
    # ------------------------------------------------------------------
    def start(self, arguments: dict[str, Any]) -> str:
        try:
            result = self._svc.start(
                StartRequest(
                    project_root=self._req(arguments, "project_root"),
                    workspace_root=self._req(arguments, "workspace_root"),
                    mode=self._opt(arguments, "mode", "assist"),
                    user_request=self._opt(arguments, "user_request"),
                    title_hint=self._opt(arguments, "title_hint"),
                )
            )
            return (
                f"Session started: {result.session_id}\n"
                f"Mode: {result.state.mode} | Status: {result.state.status}"
            )
        except Exception as exc:
            return _format_error("cortex_autopilot_start", exc)

    # ------------------------------------------------------------------
    # preflight
    # ------------------------------------------------------------------
    def preflight(self, arguments: dict[str, Any]) -> str:
        try:
            result = self._svc.preflight(
                PreflightRequest(
                    session_id=self._req(arguments, "session_id"),
                    user_request=self._opt(arguments, "user_request"),
                    changed_files=self._str_list(arguments, "changed_files"),
                    git_diff_stat=self._opt(arguments, "git_diff_stat"),
                )
            )
            lines = [
                f"Preflight: {result.detection.task_type} (confidence={result.detection.confidence:.2f})",
                f"Can proceed: {result.can_proceed}",
            ]
            if result.detection.reason:
                lines.append(f"Reason: {result.detection.reason}")
            worst = next(
                (d for d in result.policy_decisions if d.action in ("block", "degrade")),
                None,
            )
            if worst:
                lines.append(f"Policy: {worst.action} — {worst.reason}")
            return "\n".join(lines)
        except Exception as exc:
            return _format_error("cortex_autopilot_preflight", exc)

    # ------------------------------------------------------------------
    # checkpoint
    # ------------------------------------------------------------------
    def checkpoint(self, arguments: dict[str, Any]) -> str:
        try:
            result = self._svc.checkpoint(
                CheckpointRequest(
                    session_id=self._req(arguments, "session_id"),
                    summary=self._req(arguments, "summary"),
                    files_at_checkpoint=self._str_list(arguments, "files_at_checkpoint"),
                    verified=self._opt(arguments, "verified", False),
                )
            )
            return (
                f"Checkpoint recorded for {result.state.session_id}\n"
                f"Total checkpoints: {len(result.state.checkpoints)} | "
                f"Status: {result.state.status}"
            )
        except Exception as exc:
            return _format_error("cortex_autopilot_checkpoint", exc)

    # ------------------------------------------------------------------
    # finish
    # ------------------------------------------------------------------
    def finish(self, arguments: dict[str, Any]) -> str:
        try:
            result = self._svc.finish(
                FinishRequest(
                    session_id=self._req(arguments, "session_id"),
                    auto=self._opt(arguments, "auto", False),
                )
            )
            lines = [
                f"Finish: {result.state.session_id}",
                f"Status: {result.state.status} | Saved: {result.saved}",
            ]
            if result.draft:
                lines.append(f"Draft: {result.draft.title} ({result.draft.confidence})")
                if result.draft.warnings:
                    lines.append(f"Warnings: {'; '.join(result.draft.warnings)}")
            if result.state.warnings:
                lines.append(f"State warnings: {'; '.join(result.state.warnings)}")
            return "\n".join(lines)
        except Exception as exc:
            return _format_error("cortex_autopilot_finish", exc)

    # ------------------------------------------------------------------
    # status
    # ------------------------------------------------------------------
    def status(self, arguments: dict[str, Any]) -> str:
        try:
            result = self._svc.status(self._opt(arguments, "session_id"))
            if not result.active:
                return "No active Autopilot session found."
            assert result.state is not None
            return (
                f"Session: {result.state.session_id}\n"
                f"Status: {result.state.status} | Mode: {result.state.mode}\n"
                f"Task: {result.state.detected_task_type or 'none'} | "
                f"Complexity: {result.state.complexity}\n"
                f"Events: {result.event_count} | "
                f"Warnings: {len(result.state.warnings)}"
            )
        except Exception as exc:
            return _format_error("cortex_autopilot_status", exc)


def _format_error(tool_name: str, exc: Exception) -> str:
    """Return a compact error string for MCP consumers."""
    if isinstance(exc, SessionNotFoundError):
        return f"Error ({tool_name}): Session not found — {exc}"
    if isinstance(exc, AutopilotError):
        return f"Error ({tool_name}): {exc}"
    return f"Error ({tool_name}): {type(exc).__name__}: {exc}"


def _safe_call(tool_name: str, fn: Any, arguments: dict[str, Any]) -> str:
    """Call *fn* with *arguments*, catching Autopilot exceptions."""
    try:
        return fn(arguments)
    except Exception as exc:
        return _format_error(tool_name, exc)
