"""cortex.autopilot.mcp_tools — MCP tool wrappers for Autopilot.

Phase 03 refactor: every tool delegates to the new :class:`AutopilotService`.
Tool signatures are kept identical to the legacy version so existing MCP
consumers (Claude Code, custom skills) don't observe a breaking change in
the output schema beyond the natural shift from JSONL state files to
``SessionRecord`` shape.

Tools:
    cortex_autopilot_start      — adopt active session.
    cortex_autopilot_preflight  — dry-run the detector pipeline.
    cortex_autopilot_checkpoint — append a checkpoint.
    cortex_autopilot_finish     — close the session (``auto=True`` →
                                  documenter pipeline).
    cortex_autopilot_status     — describe the active session.

T3.5 will polish the human-readable formatting; this module ensures the
tools stay invokable end-to-end after the Phase 03 fusion.
"""

from __future__ import annotations

from typing import Any

from cortex.autopilot.errors import AutopilotError, NoActiveSessionError
from cortex.autopilot.lifecycle import (
    AutopilotCheckpointRequest,
    AutopilotFinishRequest,
    AutopilotPreflightRequest,
    AutopilotStartRequest,
)
from cortex.autopilot.policies import AutopilotMode
from cortex.autopilot.service import AutopilotService
from cortex.session.errors import SessionNotFound


class AutopilotMCPTools:
    """Thin MCP adapters for the Autopilot lifecycle."""

    def __init__(self, service: AutopilotService) -> None:
        self._svc = service

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _opt(arguments: dict[str, Any], key: str, default: Any = None) -> Any:
        return arguments.get(key, default)

    @staticmethod
    def _str_list(arguments: dict[str, Any], key: str) -> list[str]:
        val = arguments.get(key, [])
        if not isinstance(val, list):
            return []
        return [str(v) for v in val if v is not None]

    @staticmethod
    def _parse_mode(raw: str | None) -> AutopilotMode | None:
        if raw is None:
            return None
        try:
            return AutopilotMode(raw)
        except ValueError as exc:
            valid = ", ".join(m.value for m in AutopilotMode)
            raise AutopilotError(f"unknown mode {raw!r}; valid: {valid}") from exc

    # ── start ────────────────────────────────────────────────────

    def start(self, arguments: dict[str, Any]) -> str:
        try:
            mode = self._parse_mode(self._opt(arguments, "mode"))
            result = self._svc.start(AutopilotStartRequest(mode=mode))
            lines = [
                f"Session adopted: {result.session.session_id}",
                f"Mode: {result.policy.mode.value} | Status: {result.session.status.value}",
            ]
            if result.warnings:
                lines.append("Warnings: " + "; ".join(result.warnings))
            return "\n".join(lines)
        except Exception as exc:
            return _format_error("cortex_autopilot_start", exc)

    # ── preflight ────────────────────────────────────────────────

    def preflight(self, arguments: dict[str, Any]) -> str:
        try:
            result = self._svc.preflight(
                AutopilotPreflightRequest(
                    user_request=self._opt(arguments, "user_request"),
                    changed_files=self._str_list(arguments, "changed_files"),
                    git_diff_stat=self._opt(arguments, "git_diff_stat"),
                )
            )
            d = result.detection
            return (
                f"Preflight (dry-run): {d.task_type} "
                f"(confidence={d.confidence:.2f}, complexity={d.suggested_complexity})\n"
                f"Reason: {d.reason}"
            )
        except Exception as exc:
            return _format_error("cortex_autopilot_preflight", exc)

    # ── checkpoint ───────────────────────────────────────────────

    def checkpoint(self, arguments: dict[str, Any]) -> str:
        try:
            files_in_scope = self._str_list(arguments, "files_in_scope") or None
            result = self._svc.checkpoint(
                AutopilotCheckpointRequest(
                    source=str(self._opt(arguments, "source", "manual")),
                    verified_claims=self._str_list(arguments, "verified_claims"),
                    unverified_claims=self._str_list(arguments, "unverified_claims"),
                    artifacts_touched=self._str_list(arguments, "artifacts_touched"),
                    note=str(self._opt(arguments, "note", "")),
                    files_in_scope=files_in_scope,
                )
            )
            lines = [
                f"Checkpoint recorded for {result.session.session_id}",
                f"Total checkpoints: {len(result.session.checkpoints)} | "
                f"Status: {result.session.status.value}",
            ]
            if result.warnings:
                lines.append("Warnings: " + "; ".join(result.warnings))
            return "\n".join(lines)
        except Exception as exc:
            return _format_error("cortex_autopilot_checkpoint", exc)

    # ── finish ───────────────────────────────────────────────────

    def finish(self, arguments: dict[str, Any]) -> str:
        try:
            result = self._svc.finish(
                AutopilotFinishRequest(
                    session_id=self._opt(arguments, "session_id"),
                    auto=bool(self._opt(arguments, "auto", False)),
                    intent=str(self._opt(arguments, "intent", "closed")),
                    reason=str(self._opt(arguments, "reason", "")),
                )
            )
            if result.blocked:
                return f"Finish blocked by policy: {result.blocked_reason}"
            lines = [
                f"Finish: {result.session.session_id}",
                f"Status: {result.session.status.value} | Documented: {result.documented}",
            ]
            if result.session_note_path:
                lines.append(f"Note: {result.session_note_path}")
            if result.warnings:
                lines.append("Warnings: " + "; ".join(result.warnings))
            return "\n".join(lines)
        except Exception as exc:
            return _format_error("cortex_autopilot_finish", exc)

    # ── status ───────────────────────────────────────────────────

    def status(self, arguments: dict[str, Any]) -> str:
        try:
            result = self._svc.status(self._opt(arguments, "session_id"))
            if not result.active or result.session is None:
                return "No active Autopilot session found."
            session = result.session
            return (
                f"Session: {session.session_id}\n"
                f"Status: {session.status.value} | "
                f"Mode: {result.policy.mode.value if result.policy else 'unknown'}\n"
                f"Inferred mode: {result.inferred_mode}\n"
                f"Checkpoints: {result.checkpoint_count} | "
                f"Branch: {session.start_branch}"
            )
        except Exception as exc:
            return _format_error("cortex_autopilot_status", exc)


def _format_error(tool_name: str, exc: Exception) -> str:
    if isinstance(exc, NoActiveSessionError):
        return f"Error ({tool_name}): {exc}"
    if isinstance(exc, SessionNotFound):
        return f"Error ({tool_name}): Session not found — {exc}"
    if isinstance(exc, AutopilotError):
        return f"Error ({tool_name}): {exc}"
    return f"Error ({tool_name}): {type(exc).__name__}: {exc}"
