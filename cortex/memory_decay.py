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
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

# Default compartido entre el campo de :class:`DecayConfig` y su validación
# en ``__post_init__`` (ver bug #9).
_DEFAULT_DECAY_RATE = 0.995


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
    decay_rate: float = _DEFAULT_DECAY_RATE
    
    # Half-life in hours (time to reach 50% of original score)
    # Default: 7 days = 168 hours
    half_life_hours: float = 168.0
    
    # Minimum floor for permanent knowledge (e.g., ADRs, architecture)
    floor: float = 0.10
    
    # Minimum age in hours to apply decay (memories younger are full score)
    min_age_hours: float = 24.0

    def __post_init__(self) -> None:
        """Derive decay rate from half-life unless explicitly overridden.

        Bug #9 (deep review 2026-08): antes se derivaba SIEMPRE, pisando
        cualquier ``decay_rate`` explícito. Regla actual: un decay_rate
        distinto del default se interpreta como intención del caller y se
        respeta; con el default (o sin pasarlo), manda ``half_life_hours``
        — que es el knob que usan los enrichers.
        """
        import math
        if self.decay_rate == _DEFAULT_DECAY_RATE and self.half_life_hours > 0:
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
    "design", "tech-spec",
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
        factor = decay.calculate_decay_factor("bugfix", [], timestamp)
    """

    def __init__(
        self,
        config: DecayConfig | None = None,
        now: datetime | None = None,
    ) -> None:
        self.config = config or DecayConfig()
        self.now = now or datetime.now(UTC)

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
        return "permanent" not in tags_lower

    def get_age_hours(self, timestamp: datetime) -> float:
        """Calculate age in hours."""
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        
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
