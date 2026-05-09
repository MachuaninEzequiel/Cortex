"""cortex.autopilot.renderers.base — Renderer protocol."""
from __future__ import annotations

from typing import Protocol

from cortex.autopilot.models import AutopilotSessionState, SessionDraft


class SessionRenderer(Protocol):
    """Protocol for session-note renderers.

    Renderers produce text, they never write files directly.
    """

    name: str

    def render(self, state: AutopilotSessionState) -> SessionDraft:
        ...
