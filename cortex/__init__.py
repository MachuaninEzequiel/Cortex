"""
Cortex — Hybrid Memory System for AI Agents.

Combines episodic memory (vector DB) and semantic memory (markdown knowledge base)
into a unified cognitive layer for LLM-based agents.

v2.4 — Pipeline Module Architecture
-------------------------------------
Business logic is distributed across dedicated domain services and pipeline stages:

- :mod:`cortex.services.SpecService`    → specification lifecycle
- :mod:`cortex.services.SessionService` → session note lifecycle
- :mod:`cortex.services.PRService`      → PR intake & fallback docs

Embedding backends are managed via the Strategy pattern:

- :mod:`cortex.embedders.EmbedderFactory` → selects ONNX / local / OpenAI

CI/CD pipeline stages:

- :mod:`cortex.pipeline.PipelineOrchestrator` → runs stages, enforces gates
- :mod:`cortex.pipeline.stages`               → SecurityStage, LintStage, TestStage, DocumentationStage
- :mod:`cortex.pipeline.runners`              → GitHubActionsRunner (YAML generator)
"""

from cortex.core import AgentMemory
from cortex.embedders import EmbedderFactory, EmbeddingConfig
from cortex.episodic.memory_store import EpisodicMemoryStore
from cortex.models import (
    EnrichedContext,
    EnrichedItem,
    GeneratedDoc,
    PRContext,
    UnifiedHit,
    WorkContext,
)
from cortex.pipeline import (
    PipelineContext,
    PipelineOrchestrator,
    PipelineReport,
    PipelineStage,
    StageResult,
    StageStatus,
    StageType,
)
from cortex.retrieval.hybrid_search import HybridSearch
from cortex.semantic.vault_reader import VaultReader
from cortex.services import PRService, SessionService, SpecService

__version__ = "0.1.0"
__author__ = "cortex contributors"

__all__ = [
    # Core façade
    "AgentMemory",
    # Infrastructure
    "EpisodicMemoryStore",
    "VaultReader",
    "HybridSearch",
    # Domain services
    "SpecService",
    "SessionService",
    "PRService",
    # Embedder strategy
    "EmbedderFactory",
    "EmbeddingConfig",
    # Pipeline
    "PipelineOrchestrator",
    "PipelineContext",
    "PipelineStage",
    "StageResult",
    "StageType",
    "StageStatus",
    "PipelineReport",
    # Models
    "UnifiedHit",
    "PRContext",
    "GeneratedDoc",
    "WorkContext",
    "EnrichedItem",
    "EnrichedContext",
]
