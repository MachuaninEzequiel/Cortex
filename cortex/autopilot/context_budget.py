"""cortex.autopilot.context_budget — Budget profiles and helpers."""
from __future__ import annotations

from typing import TypedDict


class BudgetProfile(TypedDict):
    max_items: int
    max_chars: int
    embeddings: bool
    subagents: bool


BUDGET_PROFILES: dict[str, BudgetProfile] = {
    "question_only": {"max_items": 0, "max_chars": 0, "embeddings": False, "subagents": False},
    "docs_only": {"max_items": 3, "max_chars": 1200, "embeddings": True, "subagents": False},
    "fast_code": {"max_items": 5, "max_chars": 2000, "embeddings": True, "subagents": False},
    "deep_code": {"max_items": 8, "max_chars": 3500, "embeddings": True, "subagents": True},
    "finish_only": {"max_items": 0, "max_chars": 2000, "embeddings": False, "subagents": False},
}


def get_budget_profile(profile_name: str) -> BudgetProfile:
    """Return a budget profile by name, falling back to ``fast_code``."""
    return BUDGET_PROFILES.get(profile_name, BUDGET_PROFILES["fast_code"])


def profile_for_task_type(task_type: str) -> str:
    """Map a detected task type to a default budget profile name."""
    mapping = {
        "question-only": "question_only",
        "docs-only": "docs_only",
        "fast-code": "fast_code",
        "deep-code": "deep_code",
        "security": "deep_code",
        "ambiguous": "question_only",
        "noop": "question_only",
    }
    return mapping.get(task_type, "fast_code")
