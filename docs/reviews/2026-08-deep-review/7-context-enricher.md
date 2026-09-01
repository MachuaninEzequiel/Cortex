# Review: `cortex/context_enricher` (Context Enricher subsystem)

**Scope:** all 11 modules under `cortex/context_enricher/` (~3,570 LOC): `__init__.py`, `async_enricher.py`, `budget_resolver.py`, `config.py`, `co_occurrence.py`, `doc_intent.py`, `domain_detector.py`, `enricher.py`, `filters.py`, `observer.py`, `presenter.py`, `telemetry.py`.

**Mode:** read-only review. All findings cite `file:line` relative to `/home/chucho/Cortex/cortex/context_enricher/`.

---

## 1. Purpose

The Context Enricher is Cortex's **proactive context engine**: given "what the agent is working on" (a `WorkContext`), it searches episodic + semantic memory with several independent strategies, deduplicates, applies a chain of score boosts and filters, enforces a budget (max items / max chars), and returns an `EnrichedContext` ready for LLM prompt injection or CLI/CI display.

Sub-responsibilities:

| Module | Responsibility |
|---|---|
| `observer.py` | Build `WorkContext` from git diff / PR metadata / manual input; extract keywords, imports, functions, classes; run domain detection; build 4 search queries. |
| `domain_detector.py` | Map files+keywords → thematic domain (`auth`, `database`, …) via weighted rules, with an embedding-similarity fallback. |
| `enricher.py` | Core engine: 5 strategies (topic/files/keywords/pr_title/entity) → dedup → multi-match boost → co-occurrence boost → typed-graph boost → temporal decay → implicit-feedback boost → structural filters → DocIntent boost → threshold → budget. |
| `async_enricher.py` | `AsyncContextEnricher`: runs Phase-1 strategies in a thread pool; re-implements Phases 2–6 inline instead of delegating to the parent. |
| `co_occurrence.py` | `TypedCooccurrenceGraph`: file-to-file relationship graph (`imported_by`, `tested_by`, `extends`, …) built from memory co-occurrence heuristics or AST parsing. |
| `filters.py` | `EnrichmentFilters` + `apply_filters`: post-retrieval structural predicates (doc_type, status, tags AND/OR, vault scope, age, project, strict). |
| `doc_intent.py` | `DocIntentDetector`: regex lexicon mapping query → `DocIntent` (RUNBOOK, DECISION, INCIDENT…) used as per-DocType score multiplier. |
| `budget_resolver.py` | Pure function: `task_type` → `{top_k, max_chars}` envelope (reinstated from deleted autopilot module). |
| `presenter.py` | Format `EnrichedContext` as markdown, compact, grouped variants, or JSON. |
| `telemetry.py` | `PersistentObserver`: append-only JSONL of enrichment/citation events + aggregation (hit rate per strategy, latency percentiles); citation detection from wiki/md links; `make_observer` factory. |

## 2. Architecture and data flow

### Entry points (who calls this subsystem)

- **`cortex/core.py:843-863`** — `CortexMemory.enrich()` builds a `ContextObserver`, calls `observe_from_files(...)`, then `ContextEnricher(...).enrich(work, top_k=top_k)`. Config comes from YAML `context_enricher:` block (`core.py:866-874`). **Note: no `observer=` is passed — telemetry is not recorded here.**
- **`cortex/mcp/server.py`** — MCP tool flow: `_enrich_context` (server.py:1605-1646) resolves `task_type` → budget profile via `resolve_budget_profile`, then calls `self.memory.enrich(...)`; a second path builds `ContextEnricher` directly (server.py:1769-1792). Also no observer.
- **`cortex/cli/main.py:1618-1642`** — `cortex context` command: same construction, renders via `ContextPresenter.to_json / to_compact_grouped / to_markdown_grouped`.
- **`cortex/cli/_search_filters.py`** and **`cortex/cli/docs_search.py`** — build `EnrichmentFilters` from CLI flags and pass them into the enricher.
- **`cortex/cli/main.py:2105-2107`** — `make_observer(...).aggregate(...)` for the enterprise memory report (read side only).

### Outputs (who this subsystem calls)

- `cortex.retrieval.hybrid_search.HybridSearch` (enricher.py:353-360) — RRF-fused episodic+semantic search.
- `cortex.episodic.memory_store.EpisodicMemoryStore` — `search_by_entity`, `search`, `list_entries`, `count`, `cache_token`.
- `cortex.semantic.vault_reader.VaultReader` — semantic document search.
- `cortex.memory_decay.MemoryDecay` (enricher.py:218-225), `cortex.feedback_loop.FeedbackCollector` (enricher.py:239), `cortex.documentation.routing.resolve_route` + `DocType` (enricher.py:279-289), `cortex.documentation.doc_type.infer_doc_type_from_path` (enricher.py:649), `cortex.episodic.embedder.Embedder` (domain_detector.py:191).
- Models from `cortex.models`: `WorkContext`, `EnrichedItem`, `EnrichedContext`, `UnifiedHit`, `EpisodicHit`.

### Internal pipeline (sync path, `enricher.enrich`)

1. Phase 1 (enricher.py:87-161): up to 5 strategy searches; queries[0..3] map positionally to topic/file/keyword/pr_title strategies; entity search is composite over function/class/import/keyword values.
2. Phase 2 (163-181): convert hits → `EnrichedItem`, dedup by `source_id`, keep highest raw score.
3. Phase 3 (183-192): multi-match boost = `multi_match_boost^(n_strategies-1)`.
4. Phase 4/4b (195-214): legacy co-occurrence boost + typed graph boost (0.5× weight).
5. Phase 4c (217-235): temporal decay on episodic items.
6. Phase 4d (238-266): implicit feedback boost.
7. Phase 4.5 (269-272): `apply_filters`.
8. Phase 4.6 (278-296): DocIntent boost via `RouteSpec.retrieval_boost_per_intent`.
9. Phase 5-6 (299-315): min-score threshold, sort desc, greedy char/item budget.
10. Phase 7 (329-336): optional telemetry `record_enrichment`, non-blocking.

### Async variant

`AsyncContextEnricher` (async_enricher.py:56) inherits from `ContextEnricher`, overrides `enrich()` (runs `asyncio.run(enrich_async)` when no loop is running; falls back to sequential parent when inside a running loop, async_enricher.py:109-123). Strategies execute in a per-call `ThreadPoolExecutor`; exceptions are swallowed per-strategy (async_enricher.py:174-179). Then `_process_results` (async_enricher.py:274-402) re-implements Phases 2–6.

---

## 3. Invariants and design decisions

- **Dedup key is `source_id`** (episodic entry id or vault path) — one item per source regardless of how many strategies matched; `matched_by` records provenance (enricher.py:172-186).
- **Boosts are multiplicative/additive on `enriched_score`; raw `score` is preserved** — explainability contract relied upon by presenters and telemetry.
- **Budget is greedy, not optimal**: iterate score-descending, stop at first item that would overflow chars once at least one item was added (enricher.py:308-315).
- **Telemetry and entity search must never break enrichment** — wrapped in try/except (enricher.py:144-145, 335-336).
- **Filters are pure and non-mutating**, no-op when empty (filters.py:76-84); applied *after* boosts but *before* threshold/budget.
- **Caches are class-level, keyed by `(id(store), cache_token)`** (enricher.py:45-46, 481-503, 544-570) — co-occurrence and typed graphs rebuilt only when store token changes.
- **Async enricher is opt-in and additive** — sync API preserved; documented 3.5× wall-clock win (async_enricher.py:64-66).
- **Budget resolver is data-only** reinstatement of deleted autopilot profiles; unknown task types fall back to fast-code defaults so callers are "never starved" (budget_resolver.py:33-57).
- **Two orthogonal intent layers**: `QueryIntent` (RRF weights, in retrieval) vs `DocIntent` (per-DocType multipliers, here) — doc_intent.py:3-13.

---

## 4. Bugs and potential defects

### High impact

1. **`top_k=0` is impossible to express through the public pipeline** — `enricher.py:84`: `max_items = top_k or self.config.max_items`. `resolve_budget_profile("question-only")` / `"noop"` return `top_k=0` intending *zero* retrieval (budget_resolver.py:20-23), and `mcp/server.py:1635-1646` passes it straight through to `memory.enrich(top_k=0)`. Because `0 or default` → default (8), question-only tasks still pay for full 5-strategy enrichment. Same bug pattern duplicated at async_enricher.py:145.

2. **Async/sync behavioral divergence — missing phases in `_process_results`.** The async path silently drops Phase 4.5 (structural filters), Phase 4.6 (DocIntent boost) and Phase 7 (telemetry) that the parent applies (compare enricher.py:269-336 vs async_enricher.py:274-402). Any caller that switches to `AsyncContextEnricher` gets different ranking and loses filters. Currently `AsyncContextEnricher` has **no production callers** (only tests), which contains the blast radius — but the class advertises itself as a drop-in replacement ("does NOT replace ... inherits", async_enricher.py:17-21 docstring says delegating business logic to parent, which is false).

3. **`AsyncContextEnricher.__init__` drops the `observer` argument** — async_enricher.py:75-83 calls `super().__init__(episodic, semantic, config)` without forwarding an observer, and its signature doesn't even accept one. Even if phase 7 existed in `_process_results`, telemetry could never work on the async path. Also breaks LSP: `AsyncContextEnricher(episodic, semantic, config, observer=o)` raises `TypeError`.

4. **`enrich()` signature mismatch between parent and child** — parent accepts `filters: EnrichmentFilters | None` keyword (enricher.py:65); child's override does not (async_enricher.py:89-94). Passing `filters=` to the async version is a runtime `TypeError`. This violates the substitutability the module docstring promises (async_enricher.py:25-29).

### Medium impact

5. **Class-level mutable caches keyed by `id(self.episodic)`** — enricher.py:45-46. Risks:
   - `id()` reuse after GC: a freed store's slot can be reused by a new store whose `cache_token` (entry count, enricher.py:588-591) coincidentally matches the stale token → stale graph served. Token via `count()` can also collide after delete+add.
   - Not thread-safe: `AsyncContextEnricher._build_typed_graph` may be invoked concurrently... actually phases 4+ run on the calling thread, but two threads enriching simultaneously (e.g., MCP server) mutate shared dicts unsynchronized.
   - Cache never evicted → unbounded growth across many stores (long-lived process).
   - Additionally `_store_cache_token` calls `episodic.count()` on every single `enrich()` call (enricher.py:591) — extra DB roundtrip per request.

6. **Silent exception swallowing with wrong tuple** — enricher.py:290: `except (ValueError, Exception):` is just `except Exception`; a bad `doc_type` value aborts DocIntent boosting for that item with zero signal (not even debug log). Similarly broad catches at enricher.py:144, 500-501, 524-525, 573-574 mask systemic failures (e.g., broken store) behind `logger.debug`.

7. **Observer git extraction is fragile and silent** — observer.py:187-196 `_run_git` swallows timeout/FileNotFoundError and returns `""`, indistinguishable from "no changes". `_get_diff_content` diffs against `base_branch="main"` (observer.py:71); on repos without `main` (e.g., `master`, detached HEAD) every git call fails silently → empty WorkContext → empty enrichment with `total_searches=0`, no error anywhere.

8. **Keyword/function filters have substring false positives** — observer.py:249 excludes any function whose name *contains* "for"/"if"/"while" etc.: `format`, `performance`, `before_save`, `notify_if_ready` are all dropped. domain_detector.py:296 keyword matching uses `dkw in kw.lower()` (substring both ways): testing keyword `"it"` matches `"iteration"`, `"with"`; logging `"log"` matches `"catalog"`, `"logic"`; api `"get"` matches `"budget"`, `"target"`. Domain detection confidence is therefore inflated by noise words.

9. **Typo in domain lexicon** — domain_detector.py:41: `"credentiv2"` (should be `"credential"`); auth keyword never matches.

10. **Typed graph relationship inference is directionally wrong** — co_occurrence.py:151-155 builds pairs `(f1, f2)` in arbitrary list order, then `_infer_relationship` (401-424) decides type from names alone: if *either* name contains "test", `TESTED_BY` is returned with arbitrary from/to orientation; `IMPORTED_BY` is emitted without any import information (name heuristic only: "model"/"db" in name). The relation labels are thus mostly fiction when `build_from_memories` is used — and that is the only build path used in production (enricher.py:565-568); `build_from_ast` is never called from the enricher despite the module docstring claiming "Uses AST parsing to extract relationships" (co_occurrence.py:14).

11. **Relationship counts never accumulate; duplicates pile up** — co_occurrence.py:366-399 `_add_relationship` always appends a new `Relationship` (never increments `count` of an existing edge), so `rel.count == 1` forever and `strength = base * (1/3)` (line 381) for every pair. Consequence: `calculate_relationship_score`'s `min(rel.count/3, 1.0)` factor (line 344) is constant ⅓, and `relationships`, `_outgoing`, `_incoming`, `_by_type` grow linearly with memories × pairs². The "count-based strength" feature is effectively dead logic.

12. **Dead code in JS extractor** — co_occurrence.py:530-532: a second `re.compile(...)` result is discarded; the require() pattern is never used. Also `build_from_ast`, `get_path`, `get_related`, `get_files_by_type`, `node_count`, `DEFINES`/`EXTENDS` machinery has no production caller (only `build_from_memories` + `calculate_relationship_score` are used, enricher.py:565, 209).

13. **`_build_entity_index` is dead code** — enricher.py:506-527: no caller anywhere (grep confirms); also it calls `self.episodic.search("", top_k=1000)` which is likely an expensive full scan if it were used.

14. **Feedback loop instantiated per call** — enricher.py:259 and async_enricher.py:368 create a fresh `FeedbackCollector()` on every `enrich()`. If the collector persists state to disk this may be fine but is wasteful; if not, "learning" is ephemeral. Either way the object should live on the enricher instance.

15. **DocIntent boost triggered more often than documented** — enricher docstring (lines 73-77) says filters "Also trigger DocIntent-based boost"; the code applies the boost whenever `queries` is non-empty, filter-independent (enricher.py:278). Doc/code drift changes semantics for filterless callers.

16. **Budget loop discards smaller items after one oversized item** — enricher.py:310-314: `break` on first overflow instead of `continue`, so a single large high-ranked item prevents several smaller relevant items from being packed. Combined with "always keep the first item even if over budget" (`and budget_items` guard), `within_budget` can be reported `True` while `total_chars > max_chars`... actually line 324 recomputes correctly, but the first-item exemption means `within_budget=False` is reachable while the docstring implies budget is enforced.

### Low impact / polish

17. `except (ValueError, Exception)` redundancy — enricher.py:290 (see #6).
18. Deprecated `asyncio.get_event_loop()` inside coroutine — async_enricher.py:160; use `get_running_loop()`.
19. New `ThreadPoolExecutor` created and torn down per `enrich_async` call — async_enricher.py:164-166; pool churn under load. Also `max_workers=min(4, len(tasks))` caps parallelism at instance default regardless of machine.
20. Entity search hacks imports as `"function"` entities and keywords as `"class"` entities (enricher.py:127-128, async_enricher.py:240-242) — semantic misuse of the entity index; will pollute results for stores that validate entity types.
21. `_extract_keywords` operates on raw diff text including diff headers (`+++`, `index <hash>..<hash>`) — observer.py:87, 266-295; hash fragments become candidate keywords (≥4 hex chars match `\w{3,}`), polluting query strings.
22. `DomainDetector` hard-codes `min_confidence=0.5` in `ContextObserver` (observer.py:69) — `ContextEnricherConfig.domain_confidence` (config.py:22-23) exists but is **never consulted** by the detector; config knob is dead.
23. `DomainDetector.__init__` eagerly loads an ONNX sentence-transformers model on every instantiation (domain_detector.py:186-218) — i.e., every `ContextObserver()` (core.py:845) pays model-load cost even when rules suffice. No lazy loading, no singleton.
24. Telemetry `iter_events()` loads the whole JSONL into memory (telemetry.py:171-188) and the file grows unboundedly — no rotation/compaction. `events_for_run` and `aggregate` are O(file).
25. `detect_citations` / `record_citation` (telemetry.py:152-165, 304-345) have **no production callers** (grep: only tests) — the citation→feedback half of Mecanismo 1 is unwired; combined with finding "no production code passes `observer=` to `ContextEnricher`" (checked core.py:855, mcp/server.py:1788, cli/main.py:1624), the entire write side of telemetry is dormant in production; only the read/aggregate side is wired in the enterprise report (cli/main.py:2105).
26. `to_compact` docstring claims "single-line per item" but emits multi-line markdown blocks (presenter.py:82-114).
27. `EnrichmentFilters` referenced in `enrich()` annotation without runtime import (enricher.py:65; only `apply_filters` imported lazily at line 270). Safe under `from __future__ import annotations`, but breaks any future `typing.get_type_hints(ContextEnricher.enrich)`.
28. `_run_entity_search` dedup guard is convoluted: `hit.entry if hasattr(hit, "entry") else None` (async_enricher.py:263) — works but obscure vs parent's plain check (enricher.py:150-151).
29. `strict=True` + `doc_types=None` interplay: `strict` only matters when `doc_types` is set (filters.py:96-101); the field docs don't make that dependency obvious.
30. Duplicated noise-word lists and extraction patterns between `_extract_keywords` and `_extract_text_keywords` (observer.py:277-307) — drift risk.

## 5. Duplication (the biggest structural debt)

**Phases 2–6 exist twice, nearly verbatim**: enricher.py:163-338 vs async_enricher.py:293-402. ~140 lines copy-pasted with already-drifting behavior (async misses filters, DocIntent, telemetry — findings #2-#4 above). This is the single most dangerous piece of debt: every scoring change must now be made twice, and tests must cover both paths. The docstring of `_process_results` even *admits* the confusion (async_enricher.py:280-288: mentions monkey-patching `search_queries` "instead we call the parent's internal conversion..." — but there is no such parent method; it re-implements everything).

Other duplication:
- Strategy-task construction duplicated between enricher.py:93-129 and async_enricher.py:204-226 (incl. the entity-source table twice).
- Decay setup duplicated (enricher.py:220-225 vs async_enricher.py:343-347), both hard-coding `decay_rate=0.995` which appears in neither `DecayConfig` defaults nor `ContextEnricherConfig`.
- Budget loop duplicated verbatim (enricher.py:306-315 vs async_enricher.py:383-392).
- Presenter grouping logic duplicated between `to_markdown_grouped` and `to_compact_grouped` (presenter.py:117-194).

## 6. Refactor debts and opportunities

1. **Unify the pipeline (highest priority).** Extract Phases 2–6 into a protected method on `ContextEnricher` (e.g. `_fuse_and_rank(strategy_results, work, max_items, filters=None)`) and have both classes call it. Fixes findings #2/#3/#4 structurally and halves the maintenance surface.
2. **Make caches instance-level or move them into the store/graph provider.** Class attributes keyed by `id()` are a footgun (#5). A small `GraphCache` object owned by the enricher instance (or memoized on the store itself) removes id-reuse and cross-instance hazards.
3. **Lazy/embedding fallback.** Load the ONNX embedder lazily on first embedding-fallback use, and honor `config.domain_confidence` (#22/#23).
4. **Harden the budget resolver boundary.** Either teach `enrich()` to short-circuit on `top_k == 0` explicitly (`top_k is not None and top_k <= 0 → empty context`) or have the MCP server skip enrichment for zero profiles (#1).
5. **Fix or remove the typed graph.** Today it adds cost with fabricated relationship types (#10/#11). Options: (a) actually wire `build_from_ast` for changed files, (b) reduce to honest untyped co-occurrence with real counts, or (c) drop Phase 4b until relationships are grounded.
6. **Wire the telemetry write path** or delete it: pass `make_observer(...)` where `ContextEnricher` is constructed in core/MCP/CLI, implement `record_citation` call sites, add rotation (#25/#24). Half-built feedback loops are worse than none.
7. **Extract the entity-source table** to a module constant shared by both enrichers (#20).
8. **Replace substring matching with word-boundary matching** in domain rules and function-name filtering (#8), fix `credentiv2` typo (#9).
9. **Presenter:** share group/sort logic between the two grouped formatters.

## 7. "Preparación para un cambio grande" — what to touch first, what is fragile

If a large change lands here (new strategies, budget-aware rendering "Phase 09", pluggable middle-out), do this order:

1. **First: unify Phase 2–6** (refactor §6.1). Any big change made on top of the current duplication will double the diff and guarantee drift. Add characterization tests asserting sync and async produce identical rankings on a fixture store before touching anything else.
2. **Second: pin down scoring with golden tests.** The score is the product of 6 chained multipliers/additives (multi-match ×, +co-occ, +typed×0.5, ×decay, ×feedback, ×intent-boost). There is no test that freezes end-to-end ordering. Any change to boost constants silently reshuffles user-facing context.
3. **Fragile spots to treat with care:**
   - `search_queries` positional indexing (`queries[0]`=topic, `[1]`=files, `[2]`=keywords, `[3]`=pr_title) — observer.py:347-383 and enricher.py:94-115/async_enricher.py:204-218 are coupled by *position*, not names. Adding/reordering a query in the observer silently remaps strategies.
   - `EnrichedItem` field additions ripple into `_unified_hit_to_enriched` / `_semantic_hit_to_enriched` / `_episodic_hit_to_enriched` (three near-identical converters, enricher.py:393-468) and presenter/telemetry dict literals.
   - `HybridSearch` is constructed **per query, per call** (enricher.py:355-360) — if HybridSearch gains warm state (indexes, embeddings cache), this becomes a hot spot.
   - `id(self.episodic)` cache keys (#5).
   - Silent-git-failure observer (#7): a refactor that relies on `observe_from_git` will look "broken" without any error signal.
   - The `top_k or config.max_items` idiom appears twice; any budget work must handle `0` explicitly (#1).
4. **Safe to change freely:** `doc_intent.py` (pure, deterministic, well-isolated), `budget_resolver.py` (pure data), `filters.py` (pure predicates, good tests), `presenter.py` (pure formatting).

## 8. Health assessment

- **Test coverage posture is strong** (15 unit test files + integration e2e for telemetry), which lowers risk for the refactors above.
- **Core sync pipeline (`enricher.py`) is functional and coherent**, though long (662 lines) with lazy imports scattered mid-function (readable but hides dependency edges).
- **The async subclass is the weak point**: currently unused in production, API-incompatible with the parent, and behaviorally divergent. It should either be fixed via the unification refactor or demoted/removed before it gets adopted.
- **Several advertised features are inert in production**: typed-graph semantics (fabricated), telemetry writes (never wired), citation detection (no callers), `domain_confidence` config (dead knob), `build_from_ast` (dead), `_build_entity_index` (dead).
- **Overall: medium health.** Good bones (pure helpers, pydantic models, layered phases, defensive telemetry), but significant copy-paste divergence, dead/half-wired features masquerading as capabilities, and a handful of real bugs (`top_k=0`, silent git failures, substring false positives) that should be fixed before any large change.
