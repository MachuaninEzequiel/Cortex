"""
cortex.retrieval.intent
------------------------
Query intent detector for adaptive RRF weight computation.

Analyzes a natural-language query and returns an IntentResult
that the HybridSearch uses to adaptively weight episodic vs.
semantic sources before fusing with RRF.

Intent taxonomy
---------------
EPISODIC    → Queries about past events, decisions, bugs, fixes.
              Examples: "what did we decide", "last time this broke",
                        "fix login token", "PR #42"
SEMANTIC    → Queries about concepts, architecture, runbooks, specs.
              Examples: "how does auth work", "architecture diagram",
                        "deployment runbook", "API contract"
MIXED       → Ambiguous queries that benefit from both sources equally.
              Examples: "authentication", "token refresh"

Weight mapping (episodic_weight, semantic_weight)
-------------------------------------------------
EPISODIC → (2.0, 0.6)  ← pull hard from episodic, light semantic
SEMANTIC → (0.6, 2.0)  ← pull hard from semantic vault
MIXED    → (1.0, 1.0)  ← balanced (original behavior preserved)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto


class QueryIntent(Enum):
    """Semantic classification of a search query."""
    EPISODIC = auto()    # Past events, bugs, decisions, PRs
    SEMANTIC = auto()    # Concepts, docs, architecture, runbooks
    MIXED    = auto()    # Ambiguous — balanced sources


@dataclass(frozen=True)
class IntentResult:
    """
    Result of intent detection for a single query.

    Attributes:
        intent:           Detected intent class.
        episodic_weight:  Recommended RRF weight for episodic source.
        semantic_weight:  Recommended RRF weight for semantic source.
        confidence:       Detection confidence [0.0, 1.0].
        matched_signals:  Which signals triggered this classification.
    """
    intent:           QueryIntent
    episodic_weight:  float
    semantic_weight:  float
    confidence:       float
    matched_signals:  list[str]


# ------------------------------------------------------------------
# Signal lexicons
# ------------------------------------------------------------------

# Signals that strongly suggest the user wants PAST EVENTS (episodic)
_EPISODIC_SIGNALS: list[tuple[re.Pattern, str]] = [
    # Temporal references
    (re.compile(r"\b(last|previous|past|before|yesterday|ago|recently|when we)\b", re.I), "temporal_ref"),
    # Change references
    (re.compile(r"\b(fixed|broke|bugfix|patch|hotfix|resolved|introduced|changed|refactor)\b", re.I), "change_ref"),
    # PR / commit references
    (re.compile(r"\b(pr|pull request|commit|sha|merge|branch|#\d+)\b", re.I), "pr_ref"),
    # Decision references
    (re.compile(r"\b(decided|decision|chose|choice|why did|rationale|reasoning)\b", re.I), "decision_ref"),
    # Error / incident references
    (re.compile(r"\b(error|exception|incident|outage|crash|failure|broke|failed)\b", re.I), "incident_ref"),
    # Author references
    (re.compile(r"\b(implemented by|authored by|written by|who wrote|who fixed)\b", re.I), "author_ref"),
]

# Signals that strongly suggest the user wants KNOWLEDGE (semantic)
_SEMANTIC_SIGNALS: list[tuple[re.Pattern, str]] = [
    # How/What conceptual questions
    (re.compile(r"\b(how does|how to|what is|explain|describe|overview|summary)\b", re.I), "conceptual_q"),
    # Architecture / design docs
    (re.compile(r"\b(architecture|design|diagram|schema|spec|contract|api|interface)\b", re.I), "arch_ref"),
    # Runbooks / procedures
    (re.compile(r"\b(runbook|procedure|playbook|guide|tutorial|steps|deploy|setup)\b", re.I), "runbook_ref"),
    # Requirements / specs
    (re.compile(r"\b(requirement|specification|acceptance criteria|definition of done|adr)\b", re.I), "spec_ref"),
    # Concepts
    (re.compile(r"\b(concept|pattern|principle|convention|standard|best practice|best practices)\b", re.I), "concept_ref"),
]

# Weight presets per intent
_WEIGHTS: dict[QueryIntent, tuple[float, float]] = {
    QueryIntent.EPISODIC: (2.0, 0.6),
    QueryIntent.SEMANTIC: (0.6, 2.0),
    QueryIntent.MIXED:    (1.0, 1.0),
}


class QueryIntentDetector:
    """
    Detects the intent of a search query to enable adaptive RRF weighting.

    Uses a lexicon-based approach: counts matching signals from
    episodic and semantic signal sets and compares totals.

    The detector is intentionally lightweight (regex-only, no ML) to
    ensure sub-millisecond latency — it runs on every search call.

    Args:
        episodic_threshold: Minimum episodic signal count to classify
                            as EPISODIC (rather than MIXED).
        semantic_threshold: Minimum semantic signal count to classify
                            as SEMANTIC (rather than MIXED).
    """

    def __init__(
        self,
        episodic_threshold: int = 1,
        semantic_threshold: int = 1,
    ) -> None:
        self._ep_threshold = episodic_threshold
        self._sem_threshold = semantic_threshold

    def detect(self, query: str) -> IntentResult:
        """
        Classify the intent of a query and return adaptive weights.

        Args:
            query: Natural-language search query.

        Returns:
            IntentResult with intent, weights, confidence, and signals.
        """
        query = query.strip()
        ep_signals: list[str] = []
        sem_signals: list[str] = []

        for pattern, label in _EPISODIC_SIGNALS:
            if pattern.search(query):
                ep_signals.append(label)

        for pattern, label in _SEMANTIC_SIGNALS:
            if pattern.search(query):
                sem_signals.append(label)

        ep_count  = len(ep_signals)
        sem_count = len(sem_signals)
        total     = ep_count + sem_count

        # Determine intent by signal majority
        if ep_count >= self._ep_threshold and ep_count > sem_count:
            intent = QueryIntent.EPISODIC
            confidence = ep_count / max(total, 1)
        elif sem_count >= self._sem_threshold and sem_count > ep_count:
            intent = QueryIntent.SEMANTIC
            confidence = sem_count / max(total, 1)
        else:
            intent = QueryIntent.MIXED
            # Confidence is low when signals are balanced or absent
            confidence = 0.5 if total > 0 else 0.3

        ep_w, sem_w = _WEIGHTS[intent]

        return IntentResult(
            intent=intent,
            episodic_weight=ep_w,
            semantic_weight=sem_w,
            confidence=round(confidence, 3),
            matched_signals=ep_signals + sem_signals,
        )
