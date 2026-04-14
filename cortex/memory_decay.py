"""
cortex.memory_decay
-----------------
Memory Decay system for temporal relevance.

Applies exponential decay to memory retrieval scores based on age:
  - Recent memories: full relevance
  - Old memories: progressively lower scores
  - Permanent knowledge: floor minimum (10%)

This ensures the system prioritizes recent work while still
surfacing important historical context.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Literal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Decay Configuration
# ---------------------------------------------------------------------------

@dataclass
class DecayConfig:
    """
    Configuration for memory decay.
    
    The decay formula is:
        score = base_score * (decay_rate ^ hours_old)
    
    Decay rate of 0.99 means ~10% reduction per day.
    """
    
    # Decay rate per hour (0.99 = ~10% per day, ~50% per week)
    decay_rate: float = 0.995
    
    # Half-life in hours (time to reach 50% of original score)
    # Default: 7 days = 168 hours
    half_life_hours: float = 168.0
    
    # Minimum floor for permanent knowledge (e.g., ADRs, architecture)
    floor: float = 0.10
    
    # Minimum age in hours to apply decay (memories younger are full score)
    min_age_hours: float = 24.0
    
    # Maximum boost for multi-match items
    max_multimatch_boost: float = 2.0
    
    def __post_init__(self) -> None:
        """Calculate decay rate from half-life."""
        import math
        if self.half_life_hours > 0:
            self.decay_rate = math.pow(0.5, 1.0 / self.half_life_hours)


# ---------------------------------------------------------------------------
# Memory Types & Tags
# ---------------------------------------------------------------------------

# Memory types that should have reduced/no decay (permanent knowledge)
PERMANENT_TYPES: set[str] = {
    "adr",           # Architecture Decision Records
    "architecture",  # Architecture documentation
    "decision",     # Technical decisions
    "project_intro", # Project introduction
    "vault_doc",   # Vault documentation
}

# Tags that indicate permanent knowledge
PERMANENT_TAGS: set[str] = {
    "adr", "architecture", "decision", "permanent",
    "onboarding", "getting-started", "runbook",
    "architecture", "design", "tech-spec",
}

# Memory types with full decay (temporal work)
TEMPORAL_TYPES: set[str] = {
    "general", "bugfix", "feature", "refactor",
    "conversation", "ci", "deployment", "pr",
}


# ---------------------------------------------------------------------------
# Decay Calculator
# ---------------------------------------------------------------------------

class MemoryDecay:
    """
    Applies temporal decay to memory retrieval scores.
    
    Uses exponential decay with floor for permanent knowledge.
    The decay formula is:
        effective_score = base_score * decay_rate^hours_old
    
    For a memory created 7 days ago with half_life=7 days:
        effective_score = base_score * 0.5 (50% of original)
    
    For permanent knowledge (ADRs, architecture):
        effective_score = base_score * floor (never goes below floor)
    
    Usage:
        decay = MemoryDecay()
        decay.apply(hit.entry, base_score=0.8)
    """

    def __init__(
        self,
        config: DecayConfig | None = None,
        now: datetime | None = None,
    ) -> None:
        self.config = config or DecayConfig()
        self.now = now or datetime.now(timezone.utc)

    def should_decay(self, memory_type: str, tags: list[str]) -> bool:
        """
        Check if this memory should decay.
        
        Args:
            memory_type: The memory type (e.g., "bugfix", "adr")
            tags: List of tags
            
        Returns:
            True if memory should decay, False if it has floor
        """
        # Check memory type
        if memory_type.lower() in PERMANENT_TYPES:
            return False
        
        # Check tags
        tags_lower = {t.lower() for t in tags}
        if tags_lower & PERMANENT_TAGS:
            return False
        
        # Special tag: "permanent" always has floor
        if "permanent" in tags_lower:
            return False
        
        return True

    def get_age_hours(self, timestamp: datetime) -> float:
        """Calculate age in hours."""
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        
        delta = self.now - timestamp
        return delta.total_seconds() / 3600

    def calculate_decay_factor(
        self,
        memory_type: str,
        tags: list[str],
        timestamp: datetime,
    ) -> float:
        """
        Calculate the decay factor for a memory.
        
        Args:
            memory_type: The memory type
            tags: Tags on the memory
            timestamp: When the memory was created
            
        Returns:
            Decay factor [floor, 1.0]
        """
        # Check if this memory has floor (permanent knowledge)
        if not self.should_decay(memory_type, tags):
            return 1.0  # No decay, but also no boost below current
        
        # Calculate age
        age_hours = self.get_age_hours(timestamp)
        
        # If younger than min_age, no decay
        if age_hours < self.config.min_age_hours:
            return 1.0
        
        # Apply exponential decay
        import math
        # decay_rate ^ hours = e^(hours * ln(decay_rate))
        hours_since_decay = age_hours - self.config.min_age_hours
        decay_factor = math.pow(self.config.decay_rate, hours_since_decay)
        
        # Apply floor
        return max(decay_factor, self.config.floor)

    def apply(
        self,
        entry: Any,
        base_score: float,
    ) -> float:
        """
        Apply decay to a memory.
        
        Args:
            entry: MemoryEntry object
            base_score: Original relevance score
            
        Returns:
            Decayed score [floor, 1.0]
        """
        memory_type = getattr(entry, "memory_type", "general")
        tags = getattr(entry, "tags", [])
        timestamp = getattr(entry, "timestamp", None)
        
        if timestamp is None:
            return base_score
        
        decay_factor = self.calculate_decay_factor(
            memory_type,
            tags,
            timestamp,
        )
        
        return base_score * decay_factor

    def apply_to_hits(
        self,
        hits: list[Any],
    ) -> list[tuple[Any, float]]:
        """
        Apply decay to search hits.
        
        Args:
            hits: List of EpisodicHit objects
            
        Returns:
            List of (hit, decayed_score) tuples, sorted by score
        """
        decayed: list[tuple[Any, float]] = []
        
        for hit in hits:
            entry = hit.entry
            base_score = hit.score
            
            # Apply decay
            decayed_score = self.apply(entry, base_score)
            
            if decayed_score > 0:
                decayed.append((hit, decayed_score))
        
        # Sort by decayed score
        decayed.sort(key=lambda x: x[1], reverse=True)
        
        return decayed

    def get_stats(self, hits: list[Any]) -> dict:
        """
        Get decay statistics for a list of hits.
        
        Returns:
            Dict with decay stats
        """
        if not hits:
            return {"total": 0}
        
        stats = {
            "total": len(hits),
            "applying_decay": 0,
            "at_floor": 0,
            "no_decay": 0,
            "avg_age_hours": 0.0,
            "avg_decay_factor": 0.0,
        }
        
        total_age = 0.0
        total_decay = 0.0
        
        for hit in hits:
            entry = hit.entry
            memory_type = getattr(entry, "memory_type", "general")
            tags = getattr(entry, "tags", [])
            timestamp = getattr(entry, "timestamp", None)
            
            if timestamp:
                age = self.get_age_hours(timestamp)
                total_age += age
                
                decay = self.calculate_decay_factor(memory_type, tags, timestamp)
                total_decay += decay
                
                if self.should_decay(memory_type, tags):
                    stats["applying_decay"] += 1
                if decay <= self.config.floor:
                    stats["at_floor"] += 1
                if not self.should_decay(memory_type, tags):
                    stats["no_decay"] += 1
        
        if hits:
            stats["avg_age_hours"] = total_age / len(hits)
            stats["avg_decay_factor"] = total_decay / len(hits)
        
        return stats


# ---------------------------------------------------------------------------
# Score Adjustment with Multi-match
# ---------------------------------------------------------------------------

class ScoringWithDecay:
    """
    Combines decay with multi-match boost and other scoring factors.
    
    The final score is:
        final_score = base_score * decay_factor * multi_match_boost
    """

    def __init__(
        self,
        decay_config: DecayConfig | None = None,
    ) -> None:
        self.decay = MemoryDecay(decay_config)

    def calculate_final_score(
        self,
        entry: Any,
        base_score: float,
        matched_strategies: list[str],
    ) -> float:
        """
        Calculate final score with decay and multi-match boost.
        
        Args:
            entry: MemoryEntry
            base_score: Similarity search score
            matched_strategies: List of strategies that matched
            
        Returns:
            Final adjusted score
        """
        # Apply decay
        decayed_score = self.decay.apply(entry, base_score)
        
        # Apply multi-match boost (don't boost if already at floor)
        if matched_strategies and len(matched_strategies) > 1:
            boost = min(
                len(matched_strategies) - 1,
                3,  # Max 3 extra boosts
            ) * 0.15 + 1.0
            decayed_score = min(decayed_score * boost, 1.0)
        
        return decayed_score


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def create_decay_config(
    decay_rate: float | None = None,
    half_life_hours: float | None = None,
    floor: float = 0.10,
) -> DecayConfig:
    """
    Create a DecayConfig with sensible defaults.
    
    Example presets:
    
    # Aggressive decay (1 week half-life)
    config = create_decay_config(half_life_hours=168)
    
    # Conservative decay (1 month half-life)  
    config = create_decay_config(half_life_hours=720)
    
    # No decay (permanent)
    config = create_decay_config(decay_rate=1.0)
    """
    return DecayConfig(
        decay_rate=decay_rate,
        half_life_hours=half_life_hours or 168.0,  # 1 week
        floor=floor,
    )


# ---------------------------------------------------------------------------
# Configuration for ContextEnricher
# ---------------------------------------------------------------------------

@dataclass
class EnricherDecayConfig:
    """
    Decay configuration for the context enricher.
    
    Integrates with ContextEnricherConfig.
    """
    
    enabled: bool = True
    decay_rate: float = 0.995
    half_life_hours: float = 168.0
    floor: float = 0.10
    min_age_hours: float = 24.0
    
    def to_decay_config(self) -> DecayConfig:
        return DecayConfig(
            decay_rate=self.decay_rate,
            half_life_hours=self.half_life_hours,
            floor=self.floor,
            min_age_hours=self.min_age_hours,
        )
    
    @classmethod
    def from_dict(cls, data: dict) -> "EnricherDecayConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})