"""cortex.autopilot.policies.auto_checkpoint — Auto-checkpoint policy."""
from __future__ import annotations

from datetime import datetime

from cortex.autopilot.models import AutopilotSessionState, PolicyDecision


class AutoCheckpointPolicy:
    """Forces or warns about checkpoints when too many files change.

    Rules (from §7.2.1 of the global plan):
    - If > 5 files changed without checkpoint → block (autopilot) or warn (assist).
    - If > 10 min since last checkpoint and files changed → warn.
    """

    name = "auto_checkpoint"
    MAX_FILES_WITHOUT_CHECKPOINT = 5
    MAX_MINUTES_WITHOUT_CHECKPOINT = 10

    def _files_at_last_checkpoint(self, state: AutopilotSessionState) -> int:
        if not state.checkpoints:
            return 0
        return len(state.checkpoints[-1].files_at_checkpoint)

    def evaluate(self, state: AutopilotSessionState) -> PolicyDecision:
        if not state.changed_files:
            return PolicyDecision(allowed=True, reason="ok", action="proceed")

        files_since = len(state.changed_files) - self._files_at_last_checkpoint(state)

        if files_since > self.MAX_FILES_WITHOUT_CHECKPOINT:
            return PolicyDecision(
                allowed=False,
                reason=f"{files_since} files changed without checkpoint",
                action="block" if state.mode == "autopilot" else "warn",
            )

        # Time-based warning
        if not state.checkpoints:
            minutes = (datetime.now() - state.created_at).total_seconds() / 60
        else:
            last = state.checkpoints[-1]
            minutes = (datetime.now() - last.timestamp).total_seconds() / 60

        if minutes > self.MAX_MINUTES_WITHOUT_CHECKPOINT and files_since > 0:
            return PolicyDecision(
                allowed=True,
                reason=f"{minutes:.0f}min since last checkpoint, {files_since} files changed",
                action="warn",
            )

        return PolicyDecision(allowed=True, reason="ok", action="proceed")
