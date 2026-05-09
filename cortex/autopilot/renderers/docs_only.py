"""cortex.autopilot.renderers.docs_only — Renderer for documentation-only tasks."""
from __future__ import annotations

from cortex.autopilot.models import AutopilotSessionState, SessionDraft


class DocsOnlySessionRenderer:
    """Render a session note for tasks that only touched documentation.

    Used for docs-only tasks.
    """

    name = "docs_only"

    def render(self, state: AutopilotSessionState) -> SessionDraft:
        title = state.title_hint or state.user_request or "Documentation update"
        if len(title) > 80:
            title = title[:77] + "..."

        lines: list[str] = [f"# {title}", ""]

        if state.user_request:
            lines.append("## Request")
            lines.append(state.user_request)
            lines.append("")

        # Documentation files
        doc_files = [f for f in state.changed_files if f.endswith((".md", ".rst", ".txt", ".adoc"))]
        other_files = [f for f in state.changed_files if f not in doc_files]

        if doc_files:
            lines.append("## Documents created / modified")
            for f in doc_files:
                lines.append(f"- `{f}`")
            lines.append("")

        if other_files:
            lines.append("## Other files touched")
            for f in other_files:
                lines.append(f"- `{f}`")
            lines.append("")

        if state.checkpoints:
            lines.append("## Checkpoints")
            for ck in state.checkpoints:
                verified = "✅" if ck.verified else "⏳"
                lines.append(f"- {verified} {ck.summary}")
            lines.append("")

        body = "\n".join(lines)
        warnings: list[str] = []
        confidence: str = "medium"

        if not doc_files:
            confidence = "auto-draft"
            if state.changed_files:
                warnings.append("No documentation files observed (only non-doc files)")
            else:
                warnings.append("No documentation files observed")

        return SessionDraft(
            title=title,
            body=body,
            confidence=confidence,  # type: ignore[arg-type]
            warnings=warnings,
            source_events=len(state.checkpoints),
        )
