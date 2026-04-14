"""
Cortex — Hybrid Memory System for AI Agents.

Combines episodic memory (vector DB) and semantic memory (markdown knowledge base)
into a unified cognitive layer for LLM-based agents.
"""

from cortex.core import AgentMemory
from cortex.episodic.memory_store import EpisodicMemoryStore
from cortex.models import (
    EnrichedContext,
    EnrichedItem,
    GeneratedDoc,
    PRContext,
    UnifiedHit,
    WorkContext,
)
from cortex.retrieval.hybrid_search import HybridSearch
from cortex.semantic.vault_reader import VaultReader

__version__ = "0.1.0"
__author__ = "cortex contributors"

__all__ = [
    "AgentMemory",
    "EpisodicMemoryStore",
    "VaultReader",
    "HybridSearch",
    "UnifiedHit",
    "PRContext",
    "GeneratedDoc",
    "WorkContext",
    "EnrichedItem",
    "EnrichedContext",
]
