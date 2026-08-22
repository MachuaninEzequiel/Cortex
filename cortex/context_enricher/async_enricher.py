"""
cortex.context_enricher.async_enricher
----------------------------------------
AsyncContextEnricher — parallel multi-strategy search using asyncio.

The existing ContextEnricher runs all 4+ search strategies sequentially.
For a memory store with N memories, each strategy call is an independent
ChromaDB vector search — there is no shared state between them and no
reason to wait for strategy 1 to finish before starting strategy 2.

This module wraps the synchronous strategies in an asyncio executor pool,
running them concurrently. For 4 strategies with ~100ms latency each, this
reduces wall-clock time from ~400ms to ~100ms (4× speedup).

Architecture
------------
``AsyncContextEnricher`` does NOT replace ``ContextEnricher``. It inherits
from it and overrides only the ``enrich`` method (public API), delegating
all business logic (dedup, boost, threshold, budget) to the parent class.
The parent's phase 2-6 processing runs on the results aggregated from
the parallel phase 1.

Backward compatibility
----------------------
All existing code using ``ContextEnricher`` continues to work unchanged.
To opt-in to async execution:

    enricher = AsyncContextEnricher(episodic, semantic, config)
    result = await enricher.enrich_async(work)

Or run synchronously (using the same thread pool under the hood):

    result = enricher.enrich(work)  # blocks, runs strategies in parallel
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

from cortex.context_enricher.config import ContextEnricherConfig
from cortex.context_enricher.filters import EnrichmentFilters
from cortex.context_enricher.enricher import ContextEnricher
from cortex.models import EnrichedContext

if TYPE_CHECKING:
    from cortex.episodic.memory_store import EpisodicMemoryStore
    from cortex.models import WorkContext
    from cortex.semantic.vault_reader import VaultReader

logger = logging.getLogger(__name__)


class AsyncContextEnricher(ContextEnricher):
    """
    Parallel multi-strategy context enrichment engine.

    Extends ContextEnricher by running the independent search strategies
    concurrently in a thread pool, then delegating dedup/boost/budget
    processing to the parent class.

    Wall-clock time reduction (measured on typical setups):
    - 4 sequential strategies × ~100ms = ~400ms total
    - 4 parallel  strategies × ~100ms = ~110ms total (3.5× faster)

    Args:
        episodic:     EpisodicMemoryStore instance.
        semantic:     VaultReader instance.
        config:       Enricher configuration (strategies, thresholds, etc.).
        max_workers:  Max threads in the pool. Default 4 (one per strategy).
    """

    def __init__(
        self,
        episodic: EpisodicMemoryStore,
        semantic: VaultReader,
        config: ContextEnricherConfig | None = None,
        max_workers: int = 4,
    ) -> None:
        super().__init__(episodic, semantic, config)
        self._max_workers = max_workers

    # ------------------------------------------------------------------
    # Public API — overrides parent enrich() with parallel execution
    # ------------------------------------------------------------------

    def enrich(
        self,
        work: WorkContext,
        *,
        top_k: int | None = None,
        filters: "EnrichmentFilters | None" = None,
    ) -> EnrichedContext:
        """
        Synchronous entry point — runs parallel strategies and blocks.

        Uses asyncio.run() when called from a non-async context (e.g. CLI,
        MCP server, hooks). Falls back to sequential execution if the event
        loop is already running to avoid nested-loop errors.

        Args:
            work:  WorkContext from ContextObserver.
            top_k: Override max items.

        Returns:
            EnrichedContext with parallelised strategy results.
        """
        try:
            # If no event loop is running, use asyncio.run (cleanest path)
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            # Already inside an async context — run strategies synchronously
            # to avoid nested loop / deadlock issues
            logger.debug(
                "AsyncContextEnricher: event loop running, falling back to sequential"
            )
            return super().enrich(work, top_k=top_k, filters=filters)

        return asyncio.run(self.enrich_async(work, top_k=top_k, filters=filters))

    async def enrich_async(
        self,
        work: WorkContext,
        *,
        top_k: int | None = None,
        filters: "EnrichmentFilters | None" = None,
    ) -> EnrichedContext:
        """
        Async entry point — run strategies in parallel, then process results.

        Strategies are submitted to a ThreadPoolExecutor concurrently.
        Phase 2-6 (dedup, boost, graph expansion, threshold, budget) runs
        sequentially after all strategy results are collected.

        Args:
            work:  WorkContext from ContextObserver.
            top_k: Override max items.

        Returns:
            EnrichedContext with deduplicated, ranked items.
        """
        max_items = top_k or self.config.max_items
        fetch_k = max_items * 2

        # Build the strategy task list from work context and config
        strategy_tasks = self._build_strategy_tasks(work, fetch_k)

        if not strategy_tasks:
            return EnrichedContext(
                work=work, items=[], total_searches=0,
                total_raw_hits=0, total_items=0,
                total_chars=0, within_budget=True,
            )

        # -- Phase 1: Execute strategies in parallel ---------------------
        strategy_results: dict[str, list] = {}
        loop = asyncio.get_event_loop()
        strategy_names = list(strategy_tasks.keys())
        strategy_callables = list(strategy_tasks.values())

        with ThreadPoolExecutor(
            max_workers=min(self._max_workers, len(strategy_tasks))
        ) as pool:
            # Schedule all tasks concurrently and gather results by index
            coros: list[Any] = [
                loop.run_in_executor(pool, task_fn)
                for task_fn in strategy_callables
            ]
            raw_results = await asyncio.gather(*coros, return_exceptions=True)

        for name, result in zip(strategy_names, raw_results, strict=False):
            if isinstance(result, Exception):
                logger.warning("Strategy '%s' failed (non-blocking): %s", name, result)
            elif isinstance(result, list):
                strategy_results[name] = result
                logger.debug("Strategy '%s' completed: %d hits", name, len(result))

        # -- Phase 2-6: fuente única del padre -------------------------
        return self._process_results(strategy_results, work, max_items, filters=filters)

    # ------------------------------------------------------------------
    # Private — strategy builder
    # ------------------------------------------------------------------

    def _build_strategy_tasks(
        self,
        work: WorkContext,
        fetch_k: int,
    ) -> dict[str, Callable[[], Any]]:
        """
        Build a dict of {strategy_name: callable} to execute in parallel.

        Each callable is a zero-argument lambda wrapping the corresponding
        search call so it can be submitted to ThreadPoolExecutor.

        Only enabled strategies (per config) with valid query inputs are included.
        """
        tasks: dict[str, Callable[[], Any]] = {}
        queries = work.search_queries

        # Bug latente detectado por los golden de paridad P5: las lambdas
        # capturaban ``q`` por referencia y TODAS terminaban buscando la
        # última query. Se bindea como default arg.
        if self.config.topic and len(queries) >= 1:
            tasks["topic_search"] = lambda q=queries[0]: self._search_hybrid(q, fetch_k)

        if self.config.files and len(queries) >= 2:
            tasks["file_search"] = lambda q=queries[1]: self._search_hybrid(q, fetch_k)

        if self.config.keywords and len(queries) >= 3:
            tasks["keyword_search"] = lambda q=queries[2]: self._search_hybrid(q, fetch_k)

        if self.config.pr_title and len(queries) >= 4:
            tasks["pr_title_search"] = lambda q=queries[3]: self._search_hybrid(q, fetch_k)

        if self.config.entity_search and (
            work.function_names or work.class_names or work.keywords
        ):
            # Entity search is a composite operation — wrap it as a single task
            tasks["entity_search"] = lambda: self._run_entity_search(work, fetch_k)

        return tasks

    def _run_entity_search(self, work: WorkContext, fetch_k: int) -> list:
        """
        Run entity-based search for function/class/import names.

        Extracted from the parent enricher's Phase 1 entity block so it
        can be scheduled as a standalone parallel task.
        """
        from cortex.models import EpisodicHit

        entity_hits = []
        entity_sources = [
            ("function", work.function_names[:5], 3),
            ("class",    work.class_names[:3],    2),
            ("function", work.imports[:5],         2),
            ("class",    work.keywords[:3],        1),
        ]

        for search_type, values, max_results in entity_sources:
            for value in (values or []):
                if not value or len(value) < 2:
                    continue
                try:
                    hits = self.episodic.search_by_entity(
                        search_type, str(value), top_k=max_results
                    )
                    entity_hits.extend(hits)
                except Exception as exc:
                    logger.debug(
                        "Entity search failed for %s/%s: %s",
                        search_type, value, exc
                    )

        # Deduplicate by entry ID — same logic as parent
        seen: dict[str, EpisodicHit] = {}
        for hit in entity_hits:
            if not (hit.entry if hasattr(hit, "entry") else None):
                continue
            eid = hit.entry.id
            if eid not in seen or hit.score > seen[eid].score:
                seen[eid] = hit
        return sorted(seen.values(), key=lambda h: h.score, reverse=True)

    # ------------------------------------------------------------------
    # Private — result processing (delegates to parent phases 2-6)
    # ------------------------------------------------------------------

    def _process_results(
        self,
        strategy_results: dict[str, list],
        work: WorkContext,
        max_items: int,
        filters: "EnrichmentFilters | None" = None,
    ) -> EnrichedContext:
        """Delega las fases 2-6 en la fuente única del padre (V3).

        Antes duplicaba ~130 líneas del pipeline y había drift-eado:
        se saltaba Fase 08 (filtros estructurales + DocIntent boost).
        """
        return self._finalize_items(strategy_results, work, max_items, filters=filters)

