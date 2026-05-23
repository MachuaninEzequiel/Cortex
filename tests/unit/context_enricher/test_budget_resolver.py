"""Tests for :func:`cortex.context_enricher.budget_resolver.resolve_budget_profile`.

Cover every documented profile, the unknown-task-type fallback, and the
``None`` fallback. The profiles are data; once a value is fixed by a
test, future PRs must update both the data and its test together.
"""

from __future__ import annotations

import pytest

from cortex.context_enricher.budget_resolver import resolve_budget_profile


@pytest.mark.parametrize(
    ("task_type", "expected_top_k", "expected_max_chars"),
    [
        ("question-only", 0, 0),
        ("docs-only", 3, 1200),
        ("fast-code", 5, 2000),
        ("deep-code", 8, 3500),
        ("security", 8, 3500),
        ("ambiguous", 3, 1500),
        ("noop", 0, 0),
    ],
)
def test_known_profiles_match_spec(
    task_type: str, expected_top_k: int, expected_max_chars: int
) -> None:
    """Each profile must match the values declared in Phase 08 / T8.4."""
    profile = resolve_budget_profile(task_type)
    assert profile["top_k"] == expected_top_k
    assert profile["max_chars"] == expected_max_chars


def test_unknown_task_type_falls_back_to_default() -> None:
    profile = resolve_budget_profile("some-future-type")
    assert profile == {"top_k": 5, "max_chars": 2000}


def test_none_task_type_falls_back_to_default() -> None:
    profile = resolve_budget_profile(None)
    assert profile == {"top_k": 5, "max_chars": 2000}


def test_resolver_returns_a_fresh_dict_each_call() -> None:
    """Mutating the returned dict must not affect subsequent calls."""
    first = resolve_budget_profile("docs-only")
    first["top_k"] = 999
    second = resolve_budget_profile("docs-only")
    assert second["top_k"] == 3


def test_complexity_argument_is_accepted_but_does_not_change_today() -> None:
    """Forward-compatible knob: declared but not consulted in Phase 08."""
    base = resolve_budget_profile("fast-code")
    with_complexity = resolve_budget_profile("fast-code", complexity="high")
    assert base == with_complexity
