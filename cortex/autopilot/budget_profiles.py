"""cortex.autopilot.budget_profiles — Budget profile application and state helpers.

Extends ``context_budget`` with runtime helpers that operate on
``AutopilotSessionState`` and ``EnrichedContext``.
"""
from __future__ import annotations

from cortex.autopilot.context_budget import get_budget_profile, profile_for_task_type
from cortex.autopilot.models import AutopilotBudgetSnapshot, AutopilotSessionState


def profile_for_state(state: AutopilotSessionState) -> str:
    """Derive the budget profile name from the current session state."""
    if state.detected_task_type:
        return profile_for_task_type(state.detected_task_type)
    if state.complexity == "deep":
        return "deep_code"
    return "fast_code"


def apply_budget(
    enriched: object,
    profile_name: str,
    *,
    deep_track_reason: str | None = None,
) -> tuple[str, AutopilotBudgetSnapshot]:
    """Format *enriched* context according to *profile_name* limits.

    Returns a ``(prompt_text, budget_snapshot)`` tuple.
    """
    profile = get_budget_profile(profile_name)
    max_chars: int = profile["max_chars"]

    # Build compact prompt text
    if max_chars == 0:
        prompt_text = ""
    else:
        prompt_text = _format_enriched(enriched, compact=True, max_chars=max_chars)

    items_retrieved = _item_count(enriched)
    snapshot = AutopilotBudgetSnapshot(
        chars_injected=len(prompt_text),
        items_retrieved=items_retrieved,
        embeddings_used=bool(profile["embeddings"]),
        subagents_spawned=0,
        deep_track_reason=deep_track_reason,
    )
    return prompt_text, snapshot


def _format_enriched(enriched: object, compact: bool, max_chars: int) -> str:
    """Call ``to_prompt_format`` or fall back to ``to_prompt`` on *enriched*."""
    if enriched is None:
        return ""
    if hasattr(enriched, "to_prompt_format"):
        text = enriched.to_prompt_format(compact=compact)
    elif hasattr(enriched, "to_prompt"):
        text = enriched.to_prompt(max_chars=max_chars)
    else:
        text = str(enriched)
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars]
    return text


def _item_count(enriched: object) -> int:
    """Return the number of items in *enriched* if available."""
    if enriched is None:
        return 0
    if hasattr(enriched, "total_items"):
        return int(getattr(enriched, "total_items", 0))
    if hasattr(enriched, "items"):
        return len(getattr(enriched, "items", []))
    return 0
