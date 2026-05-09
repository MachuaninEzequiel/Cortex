"""cortex.autopilot.context — Context retrieval with aggressive budget enforcement.

Delegates to ``AgentMemory.enrich()`` but caps ``top_k`` and prompt length
according to the session's budget profile.  Falls back gracefully when
``AgentMemory`` is unavailable.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cortex.autopilot.budget_profiles import apply_budget, profile_for_state
from cortex.autopilot.context_budget import get_budget_profile
from cortex.autopilot.models import AutopilotBudgetSnapshot, AutopilotSessionState


@dataclass
class ContextResult:
    """Result of a budget-aware context fetch."""

    prompt_text: str
    budget: AutopilotBudgetSnapshot
    profile_name: str


def fetch_context(
    state: AutopilotSessionState,
    *,
    memory: object | None = None,
    changed_files: list[str] | None = None,
) -> ContextResult:
    """Fetch enriched context for *state* respecting the budget profile.

    Args:
        state: Current session state.
        memory: Optional ``AgentMemory`` instance.  If ``None``, one is
            created from ``state.project_root`` if possible.
        changed_files: Override list of changed files.  Defaults to
            ``state.changed_files``.

    Returns:
        ``ContextResult`` with formatted prompt text and budget snapshot.
    """
    profile_name = profile_for_state(state)
    profile = get_budget_profile(profile_name)

    # Short-circuit profiles that forbid retrieval
    if profile_name == "question_only" or profile["max_items"] == 0:
        return ContextResult(
            prompt_text="",
            budget=AutopilotBudgetSnapshot(
                chars_injected=0,
                items_retrieved=0,
                embeddings_used=False,
            ),
            profile_name=profile_name,
        )

    # Resolve memory instance
    mem = memory
    if mem is None:
        mem = _create_memory(state.project_root)

    if mem is None:
        return ContextResult(
            prompt_text="",
            budget=AutopilotBudgetSnapshot(chars_injected=0, items_retrieved=0),
            profile_name=profile_name,
        )

    # Build top_k from profile (None means "use enricher default")
    top_k: int | None = profile["max_items"] if profile["max_items"] > 0 else None

    try:
        enriched = mem.enrich(
            changed_files=changed_files or state.changed_files,
            keywords=_extract_keywords(state.user_request),
            top_k=top_k,
        )
    except Exception:
        return ContextResult(
            prompt_text="",
            budget=AutopilotBudgetSnapshot(chars_injected=0, items_retrieved=0),
            profile_name=profile_name,
        )

    deep_reason = state.budget.deep_track_reason if state.budget else None
    prompt_text, budget = apply_budget(
        enriched,
        profile_name,
        deep_track_reason=deep_reason,
    )
    return ContextResult(prompt_text=prompt_text, budget=budget, profile_name=profile_name)


def _create_memory(project_root: str) -> object | None:
    """Try to instantiate ``AgentMemory`` for *project_root*."""
    try:
        from cortex.core import AgentMemory
        config_path = Path(project_root) / "config.yaml"
        if not config_path.exists():
            # Fallback: let AgentMemory discover from cwd/project_root
            return AgentMemory(config_path=config_path)
        return AgentMemory(config_path=config_path)
    except Exception:
        return None


def _extract_keywords(user_request: str | None) -> list[str]:
    """Naive keyword extraction from the user request."""
    if not user_request:
        return []
    # Simple heuristic: split and filter short words
    words = [w.strip(".,!?;:") for w in user_request.split()]
    return [w.lower() for w in words if len(w) > 3]
