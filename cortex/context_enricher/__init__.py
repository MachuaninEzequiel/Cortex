"""
cortex.context_enricher
-----------------------
Proactive context engine for AI agents.

Observes what the agent is working on, searches the project's memory
across multiple strategies, deduplicates, ranks, and injects relevant
context automatically.

Components
----------
ContextObserver    → Extracts work context from git/PR/manual input
DomainDetector     → Maps files/keywords to thematic domains
ContextEnricher    → Multi-strategy search + dedup + rank
ContextPresenter   → Formats context for CLI, LLM prompt, or JSON
"""

from cortex.context_enricher.domain_detector import DomainDetector, DomainMatch
from cortex.context_enricher.enricher import ContextEnricher, ContextEnricherConfig
from cortex.context_enricher.observer import ContextObserver
from cortex.context_enricher.presenter import ContextPresenter

__all__ = [
    "DomainDetector",
    "DomainMatch",
    "ContextObserver",
    "ContextEnricher",
    "ContextEnricherConfig",
    "ContextPresenter",
]
