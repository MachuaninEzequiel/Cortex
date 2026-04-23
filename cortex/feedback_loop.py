"""
cortex.feedback_loop
--------------------
Feedback Loop system for learning from context usefulness.

Two types of feedback:
  1. Implicit: Analyzes overlap between work context and retrieved memories
  2. Explicit: GitHub reactions, user ratings, query refinements

The system learns which memories are useful and boosts similar
future retrievals automatically.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Feedback Types
# ---------------------------------------------------------------------------

@dataclass
class ImplicitFeedback:
    """
    Implicit feedback analyzed from context.
    
    Analyzes:
    - Keyword overlap: How many keywords from work appear in memory
    - File overlap: How many files from work appear in memory
    - Entity overlap: How many entities match
    """
    
    # Work context keywords
    work_keywords: list[str] = field(default_factory=list)
    
    # Retrieved memory keywords
    memory_keywords: list[str] = field(default_factory=list)
    
    # Overlap metrics
    keyword_overlap: float = 0.0        # 0.0 - 1.0
    file_overlap: float = 0.0           # 0.0 - 1.0
    entity_overlap: float = 0.0         # 0.0 - 1.0
    
    # Inferred usefulness
    usefulness_score: float = 0.0       # Combined score
    
    @property
    def is_useful(self) -> bool:
        """Whether this memory appears useful."""
        return self.usefulness_score >= 0.3  # Lowered from 0.5


@dataclass
class ExplicitFeedback:
    """
    Explicit feedback from users or systems.
    
    Sources:
    - GitHub reactions 👍👎 on PR comments
    - User ratings (thumbs up/down)
    - Query refinements (user searching again with similar terms)
    """
    
    source: str                    # "github", "user", "system"
    feedback_type: str             # "positive", "negative", "neutral"
    score: float = 0.0             # -1.0 to 1.0
    context: str = ""              # Additional context
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def is_positive(self) -> bool:
        return self.score > 0
    
    @property
    def is_negative(self) -> bool:
        return self.score < 0


@dataclass
class MemoryFeedback:
    """
    Aggregated feedback for a specific memory.
    
    Tracks:
    - Positive count
    - Negative count  
    - Last feedback time
    - Calculated usefulness
    """
    
    memory_id: str
    
    # Feedback counts
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    
    # Timestamps
    first_feedback: datetime | None = None
    last_feedback: datetime | None = None
    
    # Calculated metrics
    usefulness_score: float = 0.5  # 0.0 - 1.0
    times_shown: int = 0
    
    @property
    def net_score(self) -> int:
        """Net positive - negative."""
        return self.positive_count - self.negative_count
    
    @property
    def display_score(self) -> str:
        """Human-readable score."""
        if self.usefulness_score >= 0.7:
            return "🟢 High"
        elif self.usefulness_score >= 0.4:
            return "🟡 Medium"
        elif self.usefulness_score >= 0.2:
            return "🟠 Low"
        return "�� Ignore"


# ---------------------------------------------------------------------------
# Feedback Analyzer
# ---------------------------------------------------------------------------

class ImplicitFeedbackAnalyzer:
    """
    Analyzes implicit feedback from context.
    
    Compares current work with retrieved memories to
    infer usefulness without explicit user input.
    """

    def __init__(self) -> None:
        self.stopwords = {
            # Common English
            "the", "a", "an", "and", "or", "but", "in", "on", "at",
            "to", "for", "of", "with", "by", "from", "as", "is", "was",
            "are", "were", "been", "be", "have", "has", "had", "do", "does",
            "did", "will", "would", "could", "should", "may", "might", "must",
            # Common code
            "function", "return", "class", "def", "import", "export", "const",
            "let", "var", "if", "else", "while", "switch", "case",
        }

    def analyze(
        self,
        work_context: dict[str, Any],
        retrieved_items: list[dict[str, Any]],
    ) -> list[ImplicitFeedback]:
        """
        Analyze implicit feedback for retrieved items.
        
        Args:
            work_context: Current work context
            retrieved_items: Items retrieved for context
            
        Returns:
            List of ImplicitFeedback for each item
        """
        # Extract work keywords
        work_keywords = self._extract_keywords(
            work_context.get("keywords", [])
        )
        
        feedback_results: list[ImplicitFeedback] = []
        
        for item in retrieved_items:
            # Extract item keywords
            item_keywords = self._extract_keywords(
                item.get("content", "") + " " + item.get("title", "")
            )
            
            # Calculate overlaps
            kw_overlap = self._calculate_overlap(
                work_keywords, item_keywords
            )
            
            # File overlap
            work_files = set(work_context.get("files", []))
            item_files = set(item.get("files", []))
            file_overlap = self._calculate_set_overlap(work_files, item_files)
            
            # Entity overlap
            work_entities = set(work_context.get("entities", []))
            item_entities = set(item.get("entities", []))
            entity_overlap = self._calculate_set_overlap(work_entities, item_entities)
            
            # Combined usefulness score
            usefulness = (
                kw_overlap * 0.4 +
                file_overlap * 0.4 +
                entity_overlap * 0.2
            )
            
            feedback = ImplicitFeedback(
                work_keywords=work_keywords,
                memory_keywords=item_keywords,
                keyword_overlap=kw_overlap,
                file_overlap=file_overlap,
                entity_overlap=entity_overlap,
                usefulness_score=usefulness,
            )
            feedback_results.append(feedback)
        
        return feedback_results

    def _extract_keywords(self, text_or_list: str | list[str]) -> list[str]:
        """Extract keywords from text or list."""
        import re
        
        if isinstance(text_or_list, list):
            return [k.lower() for k in text_or_list if k.lower() not in self.stopwords]
        
        # Extract from text
        text = text_or_list.lower()
        words = re.findall(r"\b[a-z][a-z0-9_]{2,}\b", text)
        
        # Filter stopwords
        return [w for w in words if w not in self.stopwords and len(w) > 2]

    def _calculate_overlap(self, list1: list[str], list2: list[str]) -> float:
        """Calculate keyword overlap [0, 1]."""
        set1 = set(list1)
        set2 = set(list2)
        
        if not set1 or not set2:
            return 0.0
        
        intersection = set1 & set2
        union = set1 | set2
        
        # Jaccard similarity
        if not union:
            return 0.0
        
        return len(intersection) / len(union)

    def _calculate_set_overlap(
        self,
        set1: set[str],
        set2: set[str],
    ) -> float:
        """Calculate set overlap [0, 1]."""
        if not set1 or not set2:
            return 0.0
        
        intersection = set1 & set2
        union = set1 | set2
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)


class FeedbackCollector:
    """
    Collects and aggregates feedback for memories.
    
    Maintains a feedback history that can be used
    to boost or demote future retrievals.
    """

    def __init__(self) -> None:
        # memory_id -> MemoryFeedback
        self._feedback: dict[str, MemoryFeedback] = defaultdict(
            lambda: MemoryFeedback(memory_id="")
        )
        
        # Recent feedback for learning
        self._recent: list[tuple[str, ExplicitFeedback]] = []
        
        self._analyzer = ImplicitFeedbackAnalyzer()

    def add_feedback(
        self,
        memory_id: str,
        feedback: ExplicitFeedback,
    ) -> None:
        """Add explicit feedback for a memory."""
        mf = self._feedback[memory_id]
        
        if mf.memory_id == "":
            mf.memory_id = memory_id
        
        # Update counts
        if feedback.is_positive:
            mf.positive_count += 1
        elif feedback.is_negative:
            mf.negative_count += 1
        else:
            mf.neutral_count += 1
        
        # Update timestamps
        now = feedback.timestamp
        if mf.first_feedback is None:
            mf.first_feedback = now
        mf.last_feedback = now
        
        # Recalculate usefulness
        self._recalculate_usefulness(mf)
        
        # Track in recent
        self._recent.append((memory_id, feedback))
        
        logger.debug(f"Added feedback for {memory_id}: {feedback.feedback_type}")

    def process_implicit(
        self,
        work_context: dict[str, Any],
        retrieved_items: list[dict[str, Any]],
    ) -> dict[str, ImplicitFeedback]:
        """
        Process implicit feedback from work context.
        
        Returns:
            Dict of memory_id -> ImplicitFeedback
        """
        results = self._analyzer.analyze(work_context, retrieved_items)
        
        feedback_by_id: dict[str, ImplicitFeedback] = {}
        
        for item, feedback in zip(retrieved_items, results, strict=False):
            mem_id = item.get("id", "")
            if mem_id:
                feedback_by_id[mem_id] = feedback
                
                # If marked as useful, boost positive count
                if feedback.is_useful:
                    mf = self._feedback[mem_id]
                    mf.positive_count += 1
                    self._recalculate_usefulness(mf)
        
        return feedback_by_id

    def get_usefulness(self, memory_id: str) -> float:
        """Get usefulness score for a memory."""
        mf = self._feedback.get(memory_id)
        if mf is None:
            return 0.5  # Default neutral
        return mf.usefulness_score

    def get_boost(self, memory_id: str) -> float:
        """
        Get boost factor for a memory based on feedback.
        
        Returns:
            Multiplier [0.5, 1.5] to apply to retrieval score
        """
        usefulness = self.get_usefulness(memory_id)
        
        # Map usefulness to boost
        # 0.0 -> 0.5x (demote)
        # 0.5 -> 1.0x (neutral)
        # 1.0 -> 1.5x (boost)
        
        if usefulness >= 0.7:
            return 1.0 + (usefulness - 0.5)  # 1.2 - 1.5
        elif usefulness >= 0.4:
            return 1.0
        else:
            return 0.5 + (usefulness * 0.5)  # 0.5 - 0.7

    def get_stats(self) -> dict:
        """Get feedback statistics."""
        if not self._feedback:
            return {"total_memories": 0}
        
        # Count categories
        high = sum(1 for mf in self._feedback.values() if mf.usefulness_score >= 0.7)
        medium = sum(
            1 for mf in self._feedback.values() 
            if 0.4 <= mf.usefulness_score < 0.7
        )
        low = sum(1 for mf in self._feedback.values() if mf.usefulness_score < 0.4)
        
        return {
            "total_memories": len(self._feedback),
            "high_usefulness": high,
            "medium_usefulness": medium,
            "low_usefulness": low,
        }

    def _recalculate_usefulness(self, mf: MemoryFeedback) -> None:
        """Recalculate usefulness from feedback counts."""
        total = mf.positive_count + mf.negative_count + mf.neutral_count
        
        if total == 0:
            mf.usefulness_score = 0.5
            return
        
        # Weighted score: more recent feedback counts more
        base_score = (
            mf.positive_count * 1.0 +
            mf.neutral_count * 0.5 +
            mf.negative_count * -0.5
        ) / total
        
        # Normalize to 0-1
        mf.usefulness_score = max(0.0, min(1.0, (base_score + 1) / 2))

    def clear(self) -> None:
        """Clear feedback history."""
        self._feedback.clear()
        self._recent.clear()


# ---------------------------------------------------------------------------
# GitHub Reactions
# ---------------------------------------------------------------------------

def parse_github_reaction(reaction: str) -> ExplicitFeedback | None:
    """
    Parse a GitHub reaction into feedback.
    
    Args:
        reaction: GitHub reaction emoji (👍, 👎, ❤️, 🎉, 😕, 👀)
        
    Returns:
        ExplicitFeedback or None if not parseable
    """
    reaction_map = {
        "👍": ("positive", 1.0, "thumbs up"),
        "❤️": ("positive", 1.0, "heart"),
        "🎉": ("positive", 0.8, "party"),
        "👎": ("negative", -1.0, "thumbs down"),
        "😕": ("negative", -0.5, "confused"),
        "👀": ("neutral", 0.0, "eyes"),
    }
    
    if reaction not in reaction_map:
        return None
    
    fb_type, score, context = reaction_map[reaction]
    
    return ExplicitFeedback(
        source="github",
        feedback_type=fb_type,
        score=score,
        context=context,
    )


# ---------------------------------------------------------------------------
# Integration with ContextEnricher
# ---------------------------------------------------------------------------

class FeedbackEnricherIntegration:
    """
    Integrates feedback with context enricher.
    
    Used to:
    - Boost memories with positive feedback
    - Demote memories with negative feedback
    - Learn from implicit feedback
    """

    def __init__(self) -> None:
        self.collector = FeedbackCollector()

    def apply_feedback_boost(
        self,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Apply feedback boost to enriched items.
        
        Args:
            items: List of EnrichedItem dicts
            
        Returns:
            Items with boosted scores
        """
        for item in items:
            mem_id = item.get("id", "")
            if not mem_id:
                continue
            
            boost = self.collector.get_boost(mem_id)
            original_score = item.get("score", 0.0)
            item["score"] = original_score * boost
        
        # Re-sort by boosted score
        items.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        
        return items

    def record_feedback(
        self,
        memory_id: str,
        feedback: ExplicitFeedback,
    ) -> None:
        """Record explicit feedback for a memory."""
        self.collector.add_feedback(memory_id, feedback)

    def process_work_and_results(
        self,
        work_context: dict[str, Any],
        results: list[dict[str, Any]],
    ) -> None:
        """Process implicit feedback and update scores."""
        self.collector.process_implicit(work_context, results)