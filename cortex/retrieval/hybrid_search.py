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

This means an episodic hit at rank 1 and a semantic hit at rank 2
actually compete on the same scale — the user sees the best results
from *both* sources interleaved correctly.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from cortex.models import EpisodicHit, RetrievalResult, SemanticDocument, UnifiedHit

if TYPE_CHECKING:
    from cortex.episodic.memory_store import EpisodicMemoryStore
    from cortex.semantic.vault_reader import VaultReader

logger = logging.getLogger(__name__)

# RRF constant — 60 is the standard value from the original paper
_RRF_K = 60


class HybridSearch:
    """
    Retrieves and fuses results from episodic and semantic memory
    using **true cross-source Reciprocal Rank Fusion**.

    Unlike the previous implementation that applied RRF separately
    to each source, this version builds a single ranked list where
    episodic and semantic results compete on equal footing.

    Args:
        episodic:         EpisodicMemoryStore instance.
        semantic:         VaultReader instance.
        top_k:            Total number of unified results to return.
        episodic_weight:  RRF weight multiplier for episodic results.
        semantic_weight:  RRF weight multiplier for semantic results.
    """

    def __init__(
        self,
        episodic: EpisodicMemoryStore,
        semantic: VaultReader,
        top_k: int = 5,
        episodic_weight: float = 1.0,
        semantic_weight: float = 1.0,
    ) -> None:
        self.episodic = episodic
        self.semantic = semantic
        self.top_k = top_k
        self.episodic_weight = episodic_weight
        self.semantic_weight = semantic_weight

    def search(self, query: str, top_k: int | None = None, use_embeddings: bool = True) -> RetrievalResult:
        """
        Run hybrid search and return a fused RetrievalResult.

        The unified_hits list contains results from both sources
        interleaved by true RRF score.

        Args:
            query:  Natural-language query.
            top_k:  Override instance top_k for this call.
            use_embeddings: If False, both sources perform keyword-only search.

        Returns:
            RetrievalResult with:
            - episodic_hits: ranked episodic results (original scores)
            - semantic_hits: ranked semantic results (original scores)
            - unified_hits: cross-source RRF-fused ranked list
        """
        k = top_k or self.top_k
        logger.debug("Hybrid search: '%s' (top_k=%d, embeddings=%s)", query, k, use_embeddings)

        # Fetch from both sources (over-fetch to give RRF enough candidates)
        fetch_k = k * 2
        episodic_hits = self.episodic.search(query, top_k=fetch_k, use_embeddings=use_embeddings)
        semantic_hits = self.semantic.search(query, top_k=fetch_k, use_embeddings=use_embeddings)

        # Build unified RRF-fused ranking
        unified = self._rrf_fuse(episodic_hits, semantic_hits, top_k=k)

        return RetrievalResult(
            query=query,
            episodic_hits=episodic_hits[:k],  # keep original-scored lists for backward compat
            semantic_hits=semantic_hits[:k],
            unified_hits=unified,
        )

    # ------------------------------------------------------------------
    # True cross-source RRF fusion
    # ------------------------------------------------------------------

    def _rrf_fuse(
        self,
        episodic_hits: list[EpisodicHit],
        semantic_hits: list[SemanticDocument],
        top_k: int,
    ) -> list[UnifiedHit]:
        """
        Build a single ranked list from both sources using RRF.

        For each source, every result contributes:
            score += source_weight / (RRF_K + rank_in_source)

        All results are then sorted by their fused score globally.
        """
        fused_scores: dict[str, float] = {}
        # Track which source each key came from
        episodic_map: dict[str, EpisodicHit] = {}
        semantic_map: dict[str, SemanticDocument] = {}

        # Score episodic hits by rank
        for rank, hit in enumerate(episodic_hits, start=1):
            key = f"episodic:{hit.entry.id}"
            fused_scores[key] = fused_scores.get(key, 0.0) + self.episodic_weight * (1.0 / (_RRF_K + rank))
            episodic_map[key] = hit

        # Score semantic hits by rank
        for rank, doc in enumerate(semantic_hits, start=1):
            key = f"semantic:{doc.path}"
            fused_scores[key] = fused_scores.get(key, 0.0) + self.semantic_weight * (1.0 / (_RRF_K + rank))
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
                ))
            elif key in semantic_map:
                doc = semantic_map[key]
                unified.append(UnifiedHit(
                    source="semantic",
                    score=score,
                    doc=doc,
                ))

        return unified
