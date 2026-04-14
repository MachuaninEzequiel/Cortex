"""
cortex.context_enricher.enricher
---------------------------------
Multi-strategy search engine for the Context Enricher.

Takes a WorkContext, executes parallel searches across multiple
strategies (topic, files, keywords, pr_title), deduplicates results
by ID, applies multi-match boost and co-occurrence boost, enforces
threshold and budget, and returns an EnrichedContext.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import TYPE_CHECKING

from cortex.context_enricher.config import ContextEnricherConfig
from cortex.models import EnrichedContext, EnrichedItem, EpisodicHit

if TYPE_CHECKING:
    from cortex.episodic.memory_store import EpisodicMemoryStore
    from cortex.models import WorkContext
    from cortex.semantic.vault_reader import VaultReader

logger = logging.getLogger(__name__)


class ContextEnricher:
    """
    Multi-strategy context enrichment engine.

    Executes parallel searches across topic, files, keywords, and
    PR title strategies. Deduplicates by ID, boosts items that appear
    in multiple strategies, applies co-occurrence boost from file
    graphs, and enforces budget constraints.

    Args:
        episodic: EpisodicMemoryStore instance.
        semantic: VaultReader instance.
        config: Enricher configuration.
    """

    def __init__(
        self,
        episodic: EpisodicMemoryStore,
        semantic: VaultReader,
        config: ContextEnricherConfig | None = None,
    ) -> None:
        self.episodic = episodic
        self.semantic = semantic
        self.config = config or ContextEnricherConfig()

    def enrich(
        self,
        work: WorkContext,
        *,
        top_k: int | None = None,
    ) -> EnrichedContext:
        """
        Execute multi-strategy search and return enriched context.

        Args:
            work: WorkContext from the Observer.
            top_k: Override max items.

        Returns:
            EnrichedContext with deduplicated, ranked items.
        """
        max_items = top_k or self.config.max_items

        # Phase 1: Execute all strategies
        strategy_results: dict[str, list] = {}
        total_raw_hits = 0

        queries = work.search_queries
        fetch_k = max_items * 2  # Over-fetch for RRF

        # Strategy 1: Topic search
        if self.config.topic and len(queries) >= 1:
            hits = self._search_hybrid(queries[0], fetch_k)
            strategy_results["topic_search"] = hits
            total_raw_hits += len(hits)

        # Strategy 2: File search
        if self.config.files and len(queries) >= 2:
            hits = self._search_hybrid(queries[1], fetch_k)
            strategy_results["file_search"] = hits
            total_raw_hits += len(hits)

        # Strategy 3: Keyword search
        if self.config.keywords and len(queries) >= 3:
            hits = self._search_hybrid(queries[2], fetch_k)
            strategy_results["keyword_search"] = hits
            total_raw_hits += len(hits)

        # Strategy 4: PR title search
        if self.config.pr_title and len(queries) >= 4:
            hits = self._search_hybrid(queries[3], fetch_k)
            strategy_results["pr_title_search"] = hits
            total_raw_hits += len(hits)

        # Strategy 5: Entity search - comprehensive entity-based retrieval
        # Searches for functions, classes, errors, endpoints, etc. mentioned in current work
        if self.config.entity_search and (work.function_names or work.class_names or work.keywords):
            entity_hits = []
            
            # Map of entity types to search and their sources
            entity_sources = [
                # (search_as_type, values_to_search, max_results_per_value)
                ("function", work.function_names[:5], 3),
                ("class", work.class_names[:3], 2),
                ("function", work.imports[:5], 2),  # Import names as potential functions
                ("class", work.keywords[:3], 1),  # Keywords as potential class refs
            ]
            
            for search_type, values, max_results in entity_sources:
                if not values:
                    continue
                for value in values:
                    if not value or len(value) < 2:
                        continue
                    try:
                        hits = self.episodic.search_by_entity(
                            search_type, 
                            str(value), 
                            top_k=max_results
                        )
                        entity_hits.extend(hits)
                    except Exception as e:
                        logger.debug(f"Entity search failed for {search_type}/{value}: {e}")
            
            # Deduplicate by entry ID while preserving highest score
            seen_ids: dict[str, EpisodicHit] = {}
            for hit in entity_hits:
                if not hit.entry:
                    continue
                entry_id = hit.entry.id
                if entry_id not in seen_ids or hit.score > seen_ids[entry_id].score:
                    seen_ids[entry_id] = hit
            
            entity_hits = list(seen_ids.values())
            entity_hits.sort(key=lambda x: x.score, reverse=True)
            
            if entity_hits:
                strategy_results["entity_search"] = entity_hits
                total_raw_hits += len(entity_hits)

        # Phase 2: Convert to EnrichedItem format
        all_items: dict[str, EnrichedItem] = {}  # keyed by source_id
        item_strategies: dict[str, list[str]] = defaultdict(list)  # source_id → strategies

        for strategy_name, hits in strategy_results.items():
            for hit in hits:
                item = self._hit_to_enriched_item(hit, strategy_name)
                if item is None:
                    continue
                item_strategies[item.source_id].append(strategy_name)

                if item.source_id in all_items:
                    # Merge: keep higher score
                    existing = all_items[item.source_id]
                    if item.score > existing.score:
                        all_items[item.source_id] = item
                else:
                    all_items[item.source_id] = item

        # Phase 3: Apply multi-match boost
        for source_id, item in all_items.items():
            strategies_matched = item_strategies[source_id]
            unique_strategies = list(set(strategies_matched))
            item.matched_by = unique_strategies

            # Boost: 1.5x per extra strategy beyond the first
            boost_factor = 1.0
            if len(unique_strategies) > 1:
                boost_factor = self.config.multi_match_boost ** (len(unique_strategies) - 1)
            item.enriched_score = item.score * boost_factor

        # Phase 4: Apply co-occurrence boost (graph expansion)
        if self.config.graph_expansion and work.changed_files:
            # Legacy co-occurrence (simple count-based)
            co_occurrence = self._build_co_occurrence()
            for _, item in all_items.items():
                co_score = self._co_occurrence_score(
                    work.changed_files, item.files_mentioned, co_occurrence,
                )
                item.enriched_score += co_score * self.config.co_occurrence_boost

        # Phase 4b: Apply typed co-occurrence graph (semantic relationships)
        if self.config.typed_graph and work.changed_files:
            typed_graph = self._build_typed_graph()
            for _, item in all_items.items():
                if item.files_mentioned:
                    typed_score = typed_graph.calculate_relationship_score(
                        work.changed_files,
                        item.files_mentioned,
                    )
                    # Typed graph gets smaller boost (more nuanced)
                    item.enriched_score += typed_score * self.config.co_occurrence_boost * 0.5

        # Phase 4c: Apply temporal decay (recent memories rank higher)
        if self.config.memory_decay:
            from cortex.memory_decay import MemoryDecay, DecayConfig
            
            decay_config = DecayConfig(
                decay_rate=0.995,
                half_life_hours=self.config.decay_half_life_hours,
                floor=self.config.decay_floor,
            )
            decay_calculator = MemoryDecay(config=decay_config)
            
            for _, item in all_items.items():
                if item.source == "episodic" and item.date:
                    decay_factor = decay_calculator.calculate_decay_factor(
                        memory_type="general",  # Could extract from title/tags
                        tags=item.tags,
                        timestamp=item.date,
                    )
                    # Apply decay but preserve any minimum floor effect
                    item.enriched_score *= decay_factor

        # Phase 4d: Apply feedback loop boost (if enabled)
        if self.config.feedback_loop and work.changed_files:
            from cortex.feedback_loop import FeedbackCollector
            
            # Build work context for implicit feedback analysis
            work_context = {
                "keywords": work.keywords[:10],
                "files": work.changed_files,
                "entities": work.function_names + work.class_names,
            }
            
            # Get items as dicts for analysis
            items_as_dicts = []
            for item in all_items.values():
                items_as_dicts.append({
                    "id": item.source_id,
                    "content": item.content,
                    "title": item.title,
                    "files": item.files_mentioned,
                })
            
            # Process implicit feedback
            collector = FeedbackCollector()
            implicit_feedback = collector.process_implicit(work_context, items_as_dicts)
            
            # Apply boost based on feedback
            for item in all_items.values():
                fb = implicit_feedback.get(item.source_id)
                if fb and fb.is_useful:
                    item.enriched_score *= (1.0 + self.config.implicit_boost)

        # Phase 5: Filter by threshold and sort
        filtered = [
            item for item in all_items.values()
            if item.enriched_score >= self.config.min_score
        ]
        filtered.sort(key=lambda x: x.enriched_score, reverse=True)

        # Phase 6: Apply budget (max items + max chars)
        budget_items: list[EnrichedItem] = []
        total_chars = 0
        for item in filtered:
            item_chars = len(item.content) + len(item.title) + 50  # metadata overhead
            if len(budget_items) >= max_items:
                break
            if total_chars + item_chars > self.config.max_chars and budget_items:
                break  # Stop adding, but keep what we have
            budget_items.append(item)
            total_chars += item_chars

        return EnrichedContext(
            work=work,
            items=budget_items,
            total_searches=len(strategy_results),
            total_raw_hits=total_raw_hits,
            total_items=len(budget_items),
            total_chars=total_chars,
            within_budget=total_chars <= self.config.max_chars,
        )

    # ------------------------------------------------------------------
    # Internal: search helpers
    # ------------------------------------------------------------------

    def _search_hybrid(self, query: str, top_k: int) -> list:
        """
        Run a hybrid search (episodic + semantic) for a query.

        Returns unified hits from the RRF-fused retrieval.
        """
        from cortex.models import RetrievalResult

        # Use the existing retriever infrastructure
        from cortex.retrieval.hybrid_search import HybridSearch

        retriever = HybridSearch(
            episodic=self.episodic,
            semantic=self.semantic,
            top_k=top_k,
        )
        result: RetrievalResult = retriever.search(query, top_k=top_k)

        # Return unified hits if available, else combine
        if result.unified_hits:
            return result.unified_hits

        # Fallback: combine episodic + semantic
        hits = []
        for hit in result.episodic_hits:
            hits.append(("episodic", hit))
        for hit in result.semantic_hits:
            hits.append(("semantic", hit))
        return hits

    def _hit_to_enriched_item(self, hit, strategy: str) -> EnrichedItem | None:
        """
        Convert a search hit (UnifiedHit or raw hit) to EnrichedItem.
        """
        from cortex.models import UnifiedHit

        if isinstance(hit, UnifiedHit):
            return self._unified_hit_to_enriched(hit, strategy)

        # Handle tuple (source_type, hit_object) from fallback
        if isinstance(hit, tuple) and len(hit) == 2:
            source_type, hit_obj = hit
            if source_type == "episodic":
                return self._episodic_hit_to_enriched(hit_obj, strategy)
            elif source_type == "semantic":
                return self._semantic_hit_to_enriched(hit_obj, strategy)

        return None

    def _unified_hit_to_enriched(self, hit, strategy: str) -> EnrichedItem | None:
        """Convert a UnifiedHit to EnrichedItem."""
        if hit.source == "episodic" and hit.entry:
            return EnrichedItem(
                source="episodic",
                source_id=hit.entry.id,
                title=f"[{hit.entry.memory_type}] {hit.entry.content[:100]}",
                content=hit.entry.content,
                score=hit.score,
                enriched_score=hit.score,
                matched_by=[strategy],
                files_mentioned=hit.entry.files,
                date=hit.entry.timestamp,
                tags=hit.entry.tags,
            )
        elif hit.source == "semantic" and hit.doc:
            return EnrichedItem(
                source="semantic",
                source_id=hit.doc.path,
                title=hit.doc.title,
                content=hit.doc.content,
                score=hit.doc.score,
                enriched_score=hit.doc.score,
                matched_by=[strategy],
                files_mentioned=[],
                date=None,
                tags=hit.doc.tags,
            )
        return None

    def _episodic_hit_to_enriched(self, hit, strategy: str) -> EnrichedItem:
        """Convert an EpisodicHit to EnrichedItem."""
        entry = hit.entry
        return EnrichedItem(
            source="episodic",
            source_id=entry.id,
            title=f"[{entry.memory_type}] {entry.content[:100]}",
            content=entry.content,
            score=hit.score,
            enriched_score=hit.score,
            matched_by=[strategy],
            files_mentioned=entry.files,
            date=entry.timestamp,
            tags=entry.tags,
        )

    def _semantic_hit_to_enriched(self, hit, strategy: str) -> EnrichedItem:
        """Convert a SemanticDocument to EnrichedItem."""
        return EnrichedItem(
            source="semantic",
            source_id=hit.path,
            title=hit.title,
            content=hit.content,
            score=hit.score,
            enriched_score=hit.score,
            matched_by=[strategy],
            files_mentioned=[],
            date=None,
            tags=hit.tags,
        )

    # ------------------------------------------------------------------
    # Internal: Graph Expansion (co-occurrence)
    # ------------------------------------------------------------------

    def _build_co_occurrence(self) -> dict[str, dict[str, int]]:
        """
        Build a co-occurrence map from existing episodic memories.

        Returns:
            {file_a: {file_b: count, ...}, ...}
        """
        co_occurrence: dict[str, dict[str, int]] = {}

        try:
            # Get all episodic memories to build co-occurrence
            # We search with an empty query to get all memories
            all_hits = self.episodic.search("", top_k=1000)
            for hit in all_hits:
                files = hit.entry.files
                if len(files) < 2:
                    continue
                for f1 in files:
                    if f1 not in co_occurrence:
                        co_occurrence[f1] = {}
                    for f2 in files:
                        if f1 != f2:
                            co_occurrence[f1][f2] = co_occurrence[f1].get(f2, 0) + 1
        except Exception as exc:
            logger.debug("Could not build co-occurrence map: %s", exc)

        return co_occurrence

    def _build_entity_index(self) -> dict[str, dict[str, list[str]]]:
        """
        Build an entity index from existing episodic memories.
        
        Returns:
            {entity_type: {entity_value: [memory_ids, ...]}, ...}
        """
        entity_index: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        
        try:
            # Get all episodic memories to build entity index
            all_hits = self.episodic.search("", top_k=1000)
            for hit in all_hits:
                entry = hit.entry
                entities = entry.metadata.get("entities", {})
                for entity_type, values in entities.items():
                    for value in values:
                        entity_index[entity_type][value].append(entry.id)
        except Exception as exc:
            logger.debug("Could not build entity index: %s", exc)

        return entity_index

    def _build_typed_graph(self):
        """
        Build a typed co-occurrence graph from project files.
        
        Uses AST parsing to extract semantic relationships:
        - imported_by: file imports from another
        - tested_by: test file tests source file
        - extends/implements: class inheritance
        - uses: function/utility usage
        
        Returns:
            TypedCooccurrenceGraph instance
        """
        from cortex.context_enricher.co_occurrence import TypedCooccurrenceGraph
        
        try:
            graph = TypedCooccurrenceGraph(project_root=None)
            
            # Get all files from existing memories
            all_hits = self.episodic.search("", top_k=500)
            
            # Collect unique files
            all_files: set[str] = set()
            for hit in all_hits:
                all_files.update(hit.entry.files)
            
            if not all_files:
                return graph
            
            # Build graph from files using heuristics (AST would require file access)
            graph.build_from_memories(
                [hit.entry for hit in all_hits],
                files_extractor=lambda m: m.files,
            )
            
            return graph
            
        except Exception as exc:
            logger.debug("Could not build typed graph: %s", exc)
            return TypedCooccurrenceGraph()

    @staticmethod
    def _co_occurrence_score(
        current_files: list[str],
        memory_files: list[str],
        co_occurrence: dict[str, dict[str, int]],
    ) -> float:
        """
        Calculate co-occurrence score between current and memory files.

        Returns:
            Normalized score [0, 1].
        """
        if not current_files or not memory_files or not co_occurrence:
            return 0.0

        total = 0.0
        for f1 in current_files:
            for f2 in memory_files:
                if f2 in co_occurrence.get(f1, {}):
                    total += co_occurrence[f1][f2]

        max_possible = len(current_files) * len(memory_files)
        return total / max_possible if max_possible > 0 else 0.0
