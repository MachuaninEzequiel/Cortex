"""
cortex.retrieval.hybrid_search
-------------------------------
Combines episodic memory search and semantic vault search using
**true cross-source Reciprocal Rank Fusion (RRF)** to produce a
single, unified, ranked context list.

RRF works by:
1. Ranking each source independently
2. Computing a fused score: score = Σ weight / (k + rank)
3. Returning one unified list ranked by fused score

v2.4 — Adaptive RRF Weighting
------------------------------
When ``adaptive_weights=True`` (the default), the retriever detects
the *semantic intent* of the query and adjusts source weights before
fusion:

- Episodic intent ("last bug", "what did we fix", "PR #42")
  → episodic_weight ×2, semantic_weight ×0.6 — pulls from memory
- Semantic intent ("how does auth work", "runbook", "architecture")
  → episodic_weight ×0.6, semantic_weight ×2 — pulls from vault
- Mixed / ambiguous
  → weights unchanged (1.0 / 1.0) — balanced fusion

The adaptation is additive on top of any manually configured weights,
so existing consumers that pass explicit weights are unaffected when
``adaptive_weights=False``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from cortex.models import EpisodicHit, RetrievalResult, SemanticDocument, UnifiedHit
from cortex.retrieval.intent import IntentResult, QueryIntentDetector

if TYPE_CHECKING:
    from cortex.episodic.memory_store import EpisodicMemoryStore
    from cortex.semantic.vault_reader import VaultReader

logger = logging.getLogger(__name__)

# RRF constant — 60 is the standard value from the original paper
_RRF_K = 60

# Module-level singleton — instantiated once, used on every search call
_intent_detector = QueryIntentDetector()


class HybridSearch:
    """
    Retrieves and fuses results from episodic and semantic memory
    using **true cross-source Reciprocal Rank Fusion**.

    Supports **adaptive weight adjustment** based on query intent:
    episodic-flavoured queries receive higher episodic weight;
    documentation/concept queries receive higher semantic weight.

    Args:
        episodic:         EpisodicMemoryStore instance.
        semantic:         VaultReader instance.
        top_k:            Total number of unified results to return.
        episodic_weight:  Base RRF weight multiplier for episodic results.
        semantic_weight:  Base RRF weight multiplier for semantic results.
        adaptive_weights: If True (default), automatically adjust weights
                          based on detected query intent.
    """

    def __init__(
        self,
        episodic: EpisodicMemoryStore,
        semantic: VaultReader,
        top_k: int = 5,
        episodic_weight: float = 1.0,
        semantic_weight: float = 1.0,
        adaptive_weights: bool = True,
    ) -> None:
        self.episodic = episodic
        self.semantic = semantic
        self.top_k = top_k
        self.episodic_weight = episodic_weight
        self.semantic_weight = semantic_weight
        self.adaptive_weights = adaptive_weights

    def search(
        self,
        query: str,
        top_k: int | None = None,
        use_embeddings: bool = True,
    ) -> RetrievalResult:
        """
        Run hybrid search with adaptive RRF and return a fused RetrievalResult.

        When ``adaptive_weights`` is enabled, the query intent is detected
        and source weights are adjusted before RRF fusion. The detected
        intent is stored in ``result.intent`` for observability.

        Args:
            query:          Natural-language query.
            top_k:          Override instance top_k for this call.
            use_embeddings: If False, both sources use keyword-only search.

        Returns:
            RetrievalResult with:
            - episodic_hits: ranked episodic results (original scores)
            - semantic_hits: ranked semantic results (original scores)
            - unified_hits: cross-source adaptive-RRF-fused ranked list
            - intent:       detected query intent (if adaptive_weights=True)
        """
        k = top_k or self.top_k

        # ── Adaptive weight resolution ──────────────────────────────
        intent: IntentResult | None = None
        ep_weight = self.episodic_weight
        sem_weight = self.semantic_weight

        if self.adaptive_weights:
            intent = _intent_detector.detect(query)
            # Scale the base weights by the intent-detected multipliers
            ep_weight  = self.episodic_weight  * intent.episodic_weight
            sem_weight = self.semantic_weight  * intent.semantic_weight
            logger.debug(
                "Adaptive RRF: query='%s' intent=%s (%.2f) ep_w=%.2f sem_w=%.2f",
                query[:60], intent.intent.name, intent.confidence,
                ep_weight, sem_weight,
            )
        else:
            logger.debug(
                "Hybrid search: '%s' (top_k=%d, embeddings=%s)",
                query, k, use_embeddings,
            )

        # ── Fetch from both sources ─────────────────────────────────
        # Over-fetch to give adaptive RRF enough candidates to re-rank
        fetch_k = k * 3
        episodic_hits = self.episodic.search(query, top_k=fetch_k, use_embeddings=use_embeddings)
        semantic_hits = self.semantic.search(query, top_k=fetch_k, use_embeddings=use_embeddings)

        # ── Build unified adaptive-RRF ranking ──────────────────────
        unified = self._rrf_fuse(
            episodic_hits, semantic_hits,
            top_k=k,
            episodic_weight=ep_weight,
            semantic_weight=sem_weight,
        )

        result = RetrievalResult(
            query=query,
            episodic_hits=episodic_hits[:k],
            semantic_hits=semantic_hits[:k],
            unified_hits=unified,
            intent=intent,  # None when adaptive_weights=False
        )
        return result

    def detect_intent(self, query: str) -> IntentResult:
        """
        Expose intent detection as a public method for observability and testing.

        Args:
            query: Natural-language query to classify.

        Returns:
            IntentResult with intent, weights, confidence, and signals.
        """
        return _intent_detector.detect(query)

    # ------------------------------------------------------------------
    # True cross-source RRF fusion
    # ------------------------------------------------------------------

    def _rrf_fuse(
        self,
        episodic_hits: list[EpisodicHit],
        semantic_hits: list[SemanticDocument],
        top_k: int,
        episodic_weight: float | None = None,
        semantic_weight: float | None = None,
    ) -> list[UnifiedHit]:
        """
        Build a single ranked list from both sources using adaptive RRF.

        For each source, every result contributes:
            score += source_weight / (RRF_K + rank_in_source)

        When called from ``search()``, source weights are already
        adjusted by the intent detector. When called directly in tests
        or from external code, the instance weights are used as fallback.

        Args:
            episodic_hits:   Ranked episodic results.
            semantic_hits:   Ranked semantic results.
            top_k:           Max items to return.
            episodic_weight: Per-call weight override (intent-adjusted).
            semantic_weight: Per-call weight override (intent-adjusted).
        """
        ep_w  = episodic_weight  if episodic_weight  is not None else self.episodic_weight
        sem_w = semantic_weight  if semantic_weight  is not None else self.semantic_weight

        fused_scores: dict[str, float] = {}
        episodic_map: dict[str, EpisodicHit] = {}
        semantic_map: dict[str, SemanticDocument] = {}

        # Score episodic hits by rank using adaptive weight
        for rank, hit in enumerate(episodic_hits, start=1):
            key = f"episodic:{hit.entry.id}"
            fused_scores[key] = fused_scores.get(key, 0.0) + ep_w * (1.0 / (_RRF_K + rank))
            episodic_map[key] = hit

        # Score semantic hits by rank using adaptive weight
        for rank, doc in enumerate(semantic_hits, start=1):
            key = f"semantic:{doc.path}"
            fused_scores[key] = fused_scores.get(key, 0.0) + sem_w * (1.0 / (_RRF_K + rank))
            semantic_map[key] = doc

        # Sort all candidates by fused score
        ranked_keys = sorted(fused_scores, key=lambda k_: fused_scores[k_], reverse=True)

        unified: list[UnifiedHit] = []
        for key in ranked_keys[:top_k]:
            score = fused_scores[key]
            if key in episodic_map:
                hit = episodic_map[key]
                unified.append(UnifiedHit(
                    source="episodic",
                    score=score,
                    entry=hit.entry,
                    metadata={
                        "scope": hit.origin_scope,
                        "project_id": hit.origin_project_id,
                        "origin_vault": hit.origin_vault,
                        "origin_persist_dir": hit.origin_persist_dir,
                        **(hit.entry.metadata if isinstance(hit.entry.metadata, dict) else {}),
                    },
                ))
            elif key in semantic_map:
                doc = semantic_map[key]
                unified.append(UnifiedHit(
                    source="semantic",
                    score=score,
                    doc=doc,
                    metadata={
                        "scope": doc.origin_scope,
                        "project_id": doc.origin_project_id,
                        "origin_vault": doc.origin_vault,
                        "origin_persist_dir": doc.origin_persist_dir,
                    },
                ))

        return unified
