"""cortex.context_enricher.budget_resolver — Task-aware retrieval budget.

Pure function that maps a detected ``task_type`` (and optional
``complexity``) to a retrieval envelope (``top_k`` and ``max_chars``).
The mapping comes verbatim from the budget profiles that used to live in
the deleted ``cortex/autopilot/context_budget.py`` (see
``docs/pluggable-middle/fases/_internal/autopilot-audit.md`` §11.4) —
Phase 08 / T8.4 reinstates them as data without re-introducing the
original module.

The orchestrator (SDDwork) passes the detected ``task_type`` when it
calls ``cortex_context``; the MCP server uses this resolver to size the
enrichment proportionally. Without it, the enricher always runs at
``fast-code`` defaults — which wastes tokens on docs-only / question
tasks and under-serves deep refactors and security audits.
"""

from __future__ import annotations

# Profile envelope = ``top_k`` (max items returned) + ``max_chars``
# (rendered prompt budget). The caller (MCP server) only enforces
# ``top_k`` today; ``max_chars`` is exposed for future budget-aware
# rendering work (Phase 09).
_BUDGET_PROFILES: dict[str, dict[str, int]] = {
    "question-only": {"top_k": 0, "max_chars": 0},
    "docs-only": {"top_k": 3, "max_chars": 1200},
    "fast-code": {"top_k": 5, "max_chars": 2000},
    "deep-code": {"top_k": 8, "max_chars": 3500},
    "security": {"top_k": 8, "max_chars": 3500},
    "ambiguous": {"top_k": 3, "max_chars": 1500},
    "noop": {"top_k": 0, "max_chars": 0},
}

# Fallback profile when ``task_type`` is unknown or ``None`` — sized to
# match the fast-code defaults so we never starve a caller of context.
_DEFAULT: dict[str, int] = {"top_k": 5, "max_chars": 2000}


def resolve_budget_profile(
    task_type: str | None = None,
    complexity: str | None = None,  # noqa: ARG001 — reserved for future tuning
) -> dict[str, int]:
    """Map a detected ``task_type`` to a budget envelope.

    Unknown / ``None`` task types fall back to the fast-code defaults
    so we never accidentally starve the caller of context.

    The ``complexity`` argument is accepted for forward compatibility
    (Phase 09 may tune the envelope per complexity within a task type)
    but is not consulted today — the profiles are flat.
    """
    if task_type and task_type in _BUDGET_PROFILES:
        return dict(_BUDGET_PROFILES[task_type])
    return dict(_DEFAULT)


__all__ = ["resolve_budget_profile"]
