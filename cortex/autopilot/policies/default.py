"""cortex.autopilot.policies.default — Built-in policies."""
from __future__ import annotations

from cortex.autopilot.models import AutopilotSessionState, PolicyDecision


class BudgetPolicy:
    """Blocks or warns when the context budget is exceeded."""

    name = "budget"

    PROFILE_LIMITS = {
        "question_only": {"chars": 0, "items": 0},
        "docs_only": {"chars": 1200, "items": 3},
        "fast_code": {"chars": 2000, "items": 5},
        "deep_code": {"chars": 3500, "items": 8},
        "finish_only": {"chars": 2000, "items": 0},
    }

    def evaluate(self, state: AutopilotSessionState) -> PolicyDecision:
        budget = state.budget
        profile = self.PROFILE_LIMITS.get("fast_code")  # default profile
        if profile is None:
            return PolicyDecision(allowed=True, reason="ok", action="proceed")

        if budget.chars_injected > profile["chars"]:
            return PolicyDecision(
                allowed=False,
                reason=f"Chars injected ({budget.chars_injected}) exceeds limit ({profile['chars']})",
                action="block" if state.mode == "autopilot" else "warn",
                degrade_to="fast",
            )

        if budget.items_retrieved > profile["items"]:
            return PolicyDecision(
                allowed=False,
                reason=f"Items retrieved ({budget.items_retrieved}) exceeds limit ({profile['items']})",
                action="block" if state.mode == "autopilot" else "warn",
                degrade_to="fast",
            )

        return PolicyDecision(allowed=True, reason="ok", action="proceed")


class DocumentationRequiredPolicy:
    """Blocks finish if no session note exists for a task with changes."""

    name = "documentation_required"

    def evaluate(self, state: AutopilotSessionState) -> PolicyDecision:
        # Only enforce at finish time, not during start/preflight/implementation
        if state.status not in ("finished", "documented"):
            return PolicyDecision(allowed=True, reason="ok", action="proceed")

        if state.changed_files and not state.session_note_path:
            return PolicyDecision(
                allowed=False,
                reason="Task has file changes but no session note",
                action="block" if state.mode == "autopilot" else "warn",
            )

        return PolicyDecision(allowed=True, reason="ok", action="proceed")


class SpecRequiredPolicy:
    """Requires a spec for deep-code tasks."""

    name = "spec_required"

    def evaluate(self, state: AutopilotSessionState) -> PolicyDecision:
        if state.complexity == "deep" and not state.spec_path:
            return PolicyDecision(
                allowed=False,
                reason="Deep task requires a spec",
                action="warn",
            )
        return PolicyDecision(allowed=True, reason="ok", action="proceed")


class HumanApprovalPolicy:
    """Requires human confirmation for security or deep tasks."""

    name = "human_approval"

    def evaluate(self, state: AutopilotSessionState) -> PolicyDecision:
        if state.detected_task_type == "security" or state.complexity == "deep":
            return PolicyDecision(
                allowed=True,
                reason="Human approval recommended for security/deep task",
                action="warn",
            )
        return PolicyDecision(allowed=True, reason="ok", action="proceed")
