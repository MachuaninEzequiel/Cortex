"""
cortex.context_enricher.config
-------------------------------
Configuration for the Context Enricher: thresholds, budget, boosts,
and enabled strategies.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ContextEnricherConfig(BaseModel):
    """
    Configuration for the Context Enricher pipeline.

    Controls thresholds, budget limits, scoring boosts, and which
    search strategies are enabled.
    """

    # Thresholds
    min_score: float = Field(default=0.1, gt=0, le=1.0,
                             description="Minimum score to consider an item relevant.")
    domain_confidence: float = Field(default=0.5, gt=0, le=1.0,
                                     description="Min confidence for domain detection.")

    # Budget
    max_items: int = Field(default=8, ge=1, le=20,
                           description="Max items of context to show.")
    max_chars: int = Field(default=2000, ge=200, le=10000,
                           description="Max characters of injected context.")

    # Scoring
    multi_match_boost: float = Field(default=1.5, gt=1.0,
                                     description="Boost per extra strategy match.")
    co_occurrence_boost: float = Field(default=0.3, gt=0,
                                       description="Max boost from co-occurrence.")

    # Strategies
    topic: bool = Field(default=True, description="Search by domain/topic.")
    files: bool = Field(default=True, description="Search by file names.")
    keywords: bool = Field(default=True, description="Search by extracted keywords.")
    pr_title: bool = Field(default=True, description="Search by PR title.")
    graph_expansion: bool = Field(default=True, description="Co-occurrence boost.")
    entity_search: bool = Field(default=True, description="Search by entity match.")
    typed_graph: bool = Field(default=True, description="Use typed co-occurrence graph.")
    
    # Memory Decay
    memory_decay: bool = Field(default=True, description="Apply temporal decay to scores.")
    decay_half_life_hours: float = Field(default=168.0, ge=24.0, description="Half-life for decay (hours).")
    decay_floor: float = Field(default=0.10, ge=0.0, le=0.5, description="Minimum floor for permanent knowledge.")
    
    # Feedback Loop
    feedback_loop: bool = Field(default=True, description="Learn from feedback (implicit + explicit).")
    implicit_boost: float = Field(default=0.15, ge=0.0, le=0.5, description="Boost for implicit positive feedback.")
