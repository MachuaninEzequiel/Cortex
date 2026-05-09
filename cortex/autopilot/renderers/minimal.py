"""cortex.autopilot.renderers.minimal — Minimal session-note renderer."""
from __future__ import annotations

from cortex.autopilot.models import AutopilotSessionState, SessionDraft


class MinimalSessionRenderer:
    """Render a minimal session note: title, summary, files, events.

    Used for simple tasks (question-only resolved with small changes,
    fast-code with few files, etc.).
    """

    name = "minimal"

    def render(self, state: AutopilotSessionState) -> SessionDraft:
        title = state.title_hint or state.user_request or "Autopilot session"
        if len(title) > 80:
            title = title[:77] + "..."

        lines: list[str] = [f"# {title}", ""]

        if state.user_request:
            lines.append("## Request")
            lines.append(state.user_request)
            lines.append("")

        if state.changed_files:
            lines.append("## Files changed")
            for f in state.changed_files:
                lines.append(f"- `{f}`")
            lines.append("")

        if state.checkpoints:
            lines.append("## Checkpoints")
            for ck in state.checkpoints:
                verified = "✅" if ck.verified else "⏳"
                lines.append(f"- {verified} {ck.summary}")
            lines.append("")

        if state.spec_path:
            lines.append("## Spec reference")
            lines.append(f"- {state.spec_path}")
            lines.append("")

        body = "\n".join(lines)
        confidence: str = "medium"
        warnings: list[str] = []

        if not state.changed_files and not state.user_request:
            confidence = "auto-draft"
            warnings.append("No user request or file changes observed")

        return SessionDraft(
            title=title,
            body=body,
            confidence=confidence,  # type: ignore[arg-type]
            warnings=warnings,
            source_events=len(state.checkpoints),
        )
