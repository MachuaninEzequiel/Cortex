"""cortex.autopilot.renderers.fallback_draft — Safe fallback renderer."""
from __future__ import annotations

from cortex.autopilot.models import AutopilotSessionState, SessionDraft


class FallbackDraftRenderer:
    """Generate a safe draft with ``auto-draft`` confidence when data is missing.

    This is the renderer of last resort. It never invents information.
    """

    name = "fallback_draft"

    def render(self, state: AutopilotSessionState) -> SessionDraft:
        title = state.title_hint or state.user_request or "Autopilot session (draft)"
        if len(title) > 80:
            title = title[:77] + "..."

        lines: list[str] = [
            f"# {title}",
            "",
            "_This is an auto-generated draft.  The session was closed "
            "automatically but some expected data was not observed._",
            "",
        ]

        if state.user_request:
            lines.append("## Request")
            lines.append(state.user_request)
            lines.append("")

        if state.changed_files:
            lines.append("## Files changed")
            for f in state.changed_files:
                lines.append(f"- `{f}`")
            lines.append("")

        lines.append("## Session state")
        lines.append(f"- Status: `{state.status}`")
        lines.append(f"- Mode: `{state.mode}`")
        lines.append(f"- Detected task type: `{state.detected_task_type or 'none'}`")
        lines.append(f"- Complexity: `{state.complexity}`")
        lines.append("")

        body = "\n".join(lines)

        warnings: list[str] = [
            "Auto-draft: session closed with incomplete data",
        ]

        return SessionDraft(
            title=title,
            body=body,
            confidence="auto-draft",
            warnings=warnings,
            source_events=0,
        )
