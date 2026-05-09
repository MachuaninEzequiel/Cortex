"""cortex.autopilot.renderers.implementation — Renderer for code tasks."""
from __future__ import annotations

from cortex.autopilot.models import AutopilotSessionState, SessionDraft


class ImplementationSessionRenderer:
    """Render an implementation session note with changes, decisions, and spec ref.

    Used for fast-code and deep-code tasks.
    """

    name = "implementation"

    def render(self, state: AutopilotSessionState) -> SessionDraft:
        title = state.title_hint or state.user_request or "Implementation session"
        if len(title) > 80:
            title = title[:77] + "..."

        lines: list[str] = [f"# {title}", ""]

        # Request
        if state.user_request:
            lines.append("## Request")
            lines.append(state.user_request)
            lines.append("")

        # Task type and complexity
        lines.append("## Classification")
        if state.detected_task_type:
            lines.append(f"- Task type: `{state.detected_task_type}`")
        if state.complexity:
            lines.append(f"- Complexity: `{state.complexity}`")
        lines.append("")

        # Files changed
        if state.changed_files:
            lines.append("## Files changed")
            for f in state.changed_files:
                lines.append(f"- `{f}`")
            lines.append("")
        else:
            lines.append("## Files changed")
            lines.append("_No files recorded in state._")
            lines.append("")

        # Checkpoints
        if state.checkpoints:
            lines.append("## Checkpoints")
            for ck in state.checkpoints:
                verified = "✅" if ck.verified else "⏳"
                lines.append(f"- {verified} {ck.summary}")
                if ck.files_at_checkpoint:
                    lines.append(f"  - Files: {', '.join(ck.files_at_checkpoint)}")
            lines.append("")

        # Spec reference
        if state.spec_path:
            lines.append("## Spec reference")
            lines.append(f"- {state.spec_path}")
            lines.append("")
        else:
            lines.append("## Spec reference")
            lines.append("_No spec associated._")
            lines.append("")

        # Tools used
        if state.tools_seen:
            lines.append("## Tools used")
            for t in state.tools_seen:
                lines.append(f"- `{t}`")
            lines.append("")

        # Commands seen
        if state.commands_seen:
            lines.append("## Commands executed")
            for c in state.commands_seen:
                lines.append(f"- `{c}`")
            lines.append("")

        # Budget snapshot
        lines.append("## Context budget")
        b = state.budget
        lines.append(f"- Chars injected: {b.chars_injected}")
        lines.append(f"- Items retrieved: {b.items_retrieved}")
        lines.append(f"- Embeddings used: {'yes' if b.embeddings_used else 'no'}")
        lines.append(f"- Subagents spawned: {b.subagents_spawned}")
        if b.deep_track_reason:
            lines.append(f"- Deep track reason: {b.deep_track_reason}")
        lines.append("")

        body = "\n".join(lines)
        warnings: list[str] = []

        # Epistemic guard: if no checkpoints are verified, warn
        if state.checkpoints and not any(ck.verified for ck in state.checkpoints):
            warnings.append("No verified checkpoints")

        confidence: str = "medium"
        if not state.changed_files:
            confidence = "auto-draft"
            warnings.append("No file changes observed")

        return SessionDraft(
            title=title,
            body=body,
            confidence=confidence,  # type: ignore[arg-type]
            warnings=warnings,
            source_events=len(state.checkpoints) + len(state.tools_seen) + len(state.commands_seen),
        )
