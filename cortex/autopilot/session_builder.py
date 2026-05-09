"""cortex.autopilot.session_builder — Build session notes from observed state.

The ``SessionBuilder`` selects the appropriate renderer, runs self-review,
and returns a ``SessionDraft`` ready for persistence.
"""
from __future__ import annotations

from cortex.autopilot.models import AutopilotSessionState, SessionDraft
from cortex.autopilot.renderers.docs_only import DocsOnlySessionRenderer
from cortex.autopilot.renderers.fallback_draft import FallbackDraftRenderer
from cortex.autopilot.renderers.implementation import ImplementationSessionRenderer
from cortex.autopilot.renderers.minimal import MinimalSessionRenderer


# Placeholder markers used by the self-review scanner.
_PLACEHOLDERS = {"tbd", "todo", "fixme", "[pendiente]", "xxx", "???", "fill me"}

# Spanish / English success claims that require verification evidence.
_SUCCESS_CLAIMS = {
    "tests pass", "test passed", "build exitoso", "build successful",
    "linter clean", "lint passed", "verificado", "verified",
    "checks pass", "ci passed",
}


def _scan_placeholders(body: str) -> list[str]:
    """Return a list of placeholder markers found in *body*."""
    body_lower = body.lower()
    found: list[str] = []
    for marker in _PLACEHOLDERS:
        if marker in body_lower:
            found.append(marker.upper())
    return found


def _check_file_consistency(state: AutopilotSessionState, body: str) -> list[str]:
    """Warn if files listed in state are missing from the draft body."""
    warnings: list[str] = []
    # Naive check: see if each changed file appears somewhere in the body.
    missing = [f for f in state.changed_files if f not in body]
    if missing:
        warnings.append(f"Files in state but not in draft: {missing}")
    return warnings


def _check_evidence(state: AutopilotSessionState, body: str) -> list[str]:
    """Warn if the body makes success claims without verification events."""
    warnings: list[str] = []
    body_lower = body.lower()
    has_claim = any(claim in body_lower for claim in _SUCCESS_CLAIMS)

    # We can't directly access events from state (state doesn't hold events).
    # We approximate by checking if any checkpoint is marked verified.
    has_verification = any(ck.verified for ck in state.checkpoints)

    if has_claim and not has_verification:
        warnings.append("Success claim without verification event")
    return warnings


def self_review(draft: SessionDraft, state: AutopilotSessionState) -> SessionDraft:
    """Run the self-review protocol on a draft.

    Rules (from §7.3.1 of the global plan):
    1. Placeholder scan.
    2. File consistency (state vs body).
    3. Evidence check (success claims need verified checkpoints).

    If problems are found, confidence is downgraded to ``auto-draft``.
    """
    warnings = list(draft.warnings)

    # 1. Placeholder scan
    placeholders = _scan_placeholders(draft.body)
    for ph in placeholders:
        warnings.append(f"Placeholder found: {ph}")

    # 2. File consistency
    warnings.extend(_check_file_consistency(state, draft.body))

    # 3. Evidence check
    warnings.extend(_check_evidence(state, draft.body))

    confidence: str = draft.confidence
    if warnings and confidence != "auto-draft":
        confidence = "auto-draft"

    return SessionDraft(
        title=draft.title,
        body=draft.body,
        confidence=confidence,  # type: ignore[arg-type]
        warnings=warnings,
        source_events=draft.source_events,
    )


# Mapping from task type → default renderer.
_DEFAULT_RENDERER_MAP: dict[str, str] = {
    "question-only": "minimal",
    "docs-only": "docs_only",
    "fast-code": "implementation",
    "deep-code": "implementation",
    "security": "implementation",
    "ambiguous": "fallback_draft",
    "noop": "fallback_draft",
}

_RENDERERS: dict[str, object] = {
    "minimal": MinimalSessionRenderer(),
    "docs_only": DocsOnlySessionRenderer(),
    "implementation": ImplementationSessionRenderer(),
    "fallback_draft": FallbackDraftRenderer(),
}


class SessionBuilder:
    """Orchestrate renderer selection, rendering, and self-review."""

    def __init__(self, renderers: dict[str, object] | None = None) -> None:
        self._renderers = renderers if renderers is not None else dict(_RENDERERS)

    def select_renderer_name(self, state: AutopilotSessionState) -> str:
        """Pick the most appropriate renderer for *state*."""
        task_type = state.detected_task_type or "noop"
        return _DEFAULT_RENDERER_MAP.get(task_type, "fallback_draft")

    def build(self, state: AutopilotSessionState) -> SessionDraft:
        """Render and self-review a session draft from *state*."""
        renderer_name = self.select_renderer_name(state)
        renderer = self._renderers.get(renderer_name, FallbackDraftRenderer())
        draft = renderer.render(state)  # type: ignore[union-attr]
        draft = self_review(draft, state)
        return draft
