# CHANGELOG

## [Unreleased] — 2026-04-12

This release contains **17 critical fixes and improvements** that address fundamental architectural issues in Cortex. Below is a detailed explanation of every change, why it was necessary, and what it means for you.

---

### 🔴 CRITICAL FIXES

#### 1. Semantic Memory Now Uses True Vector Embeddings

**What changed:** `VaultReader` no longer performs naive keyword counting. It now embeds every vault document using the same `Embedder` as the episodic layer, enabling genuine cosine-similarity semantic search.

**Why it matters:** Previously, querying "authentication failure" would never find a document about "login errors" because the search was purely lexical (`str.count()` per term). Now both memory types live in the same vector space — a query for "login errors" will correctly surface docs about "authentication failures" due to semantic vector similarity.

**Files changed:**
- `cortex/semantic/vault_reader.py` — complete rewrite
- `cortex/core.py` — passes `embedding_model` and `embedding_backend` to `VaultReader`

**Technical details:**
- Documents are batch-embedded at sync time via `embedder.embed_batch()`
- Query-time: embed the query, compute cosine similarity against every document vector
- BM25 keyword search is kept as a fallback when embeddings are unavailable
- BM25 IDF statistics are pre-computed during sync and persisted to `.cortex_index.json`

**Migration:** None required. Existing vaults will be re-embedded on next `sync_vault()`. The first sync after upgrading will take longer as all documents are embedded.

---

#### 2. True Cross-Source Reciprocal Rank Fusion (RRF)

**What changed:** RRF now fuses episodic and semantic results into a **single unified ranked list** where results from both sources compete on equal footing.

**Why it matters:** Previously, RRF was applied *separately* to each source's results. An episodic hit at rank 1 and a semantic hit at rank 1 each got an RRF score, but they never competed against each other. The `episodic_weight` and `semantic_weight` parameters had no real effect because they only scaled within-source scores.

Now, a highly relevant semantic document can correctly outrank a weakly relevant episodic memory (and vice versa) in a single interleaved list. This is how RRF is meant to work per the original paper.

**Files changed:**
- `cortex/retrieval/hybrid_search.py` — complete rewrite of `_rrf_fuse()`
- `cortex/models.py` — new `UnifiedHit` model, `RetrievalResult` gains `unified_hits` field

**Before (wrong):**
```
Episodic:  [mem_001 score=0.0164, mem_002 score=0.0161]
Semantic:  [auth.md  score=0.0164]
# Two separate lists — no cross-source competition
```

**After (correct):**
```
Unified:   [EPISODIC mem_001 score=0.0164, SEMANTIC auth.md score=0.0164, EPISODIC mem_002 score=0.0161]
# Single list — best results from both sources interleaved
```

**Migration:** `result.to_prompt()` automatically uses the unified list. Existing code using `result.episodic_hits` and `result.semantic_hits` still works (backward compatible), but those lists now contain original similarity scores rather than RRF scores.

---

#### 3. Timestamp Restored on Episodic Memory Retrieval

**What changed:** `_deserialize_metadata()` in `EpisodicMemoryStore` now reads the stored `timestamp` field and reconstructs the `datetime` object.

**Why it matters:** Every retrieved memory was getting `datetime.now()` as its timestamp because the field was serialized to ChromaDB but never restored. This means you couldn't tell when a memory was created — a memory from 3 months ago appeared to have been created just now.

**Files changed:**
- `cortex/episodic/memory_store.py` — `_deserialize_metadata()` now parses `timestamp` via `datetime.fromisoformat()`

---

### 🟡 IMPORTANT FIXES

#### 4. `AgentMemory.create_note()` Added to Public API

**What changed:** `AgentMemory` now has a `create_note(title, content, tags=..., subfolder=...)` method that delegates to `self.semantic.create_note()`.

**Why it matters:** Previously, creating a semantic note required `memory.semantic.create_note()` — an implementation detail that leaked through the public API. The `remember()` method was on `AgentMemory`, but `create_note()` was not, making the API inconsistent.

**Before:**
```python
memory.semantic.create_note("My Note", "content...")  # leaked internal structure
```

**After:**
```python
memory.create_note("My Note", "content...")  # consistent public API
```

**Files changed:** `cortex/core.py`

---

#### 5. `CortexHook` Decorator Uses `functools.wraps` and Handles Keyword Arguments

**What changed:**
- The decorator now uses `@functools.wraps(fn)` to preserve `__name__`, `__doc__`, and other function metadata.
- Input capture now uses `inspect.signature().bind_partial()` to map arguments to their parameter names, producing readable memory entries even when functions are called with keyword arguments.

**Why it matters:**
- Without `functools.wraps`, debuggers, profilers, and documentation tools saw `wrapper` instead of the actual function name.
- Previously, `run_agent(prompt="hello")` stored `Input: {'prompt': 'hello'}` — a raw dict representation. Now it stores `Input: prompt=hello` — readable and consistent.

**Files changed:** `cortex/hooks/agent_hooks.py`

---

#### 6. Config Validated with Pydantic

**What changed:** A full Pydantic config model hierarchy (`CortexConfig`, `EpisodicConfig`, `SemanticConfig`, `RetrievalConfig`, `LLMConfig`) validates all values on startup.

**Why it matters:** Previously, setting `top_k: -1` or `episodic_weight: -5` would silently produce garbage results. Now Pydantic rejects invalid values with clear error messages:

```
pydantic_core.ValidationError: 1 validation error for RetrievalConfig
top_k
  Input should be greater than or equal to 1 [type=greater_than_equal, ...]
```

**Validation rules:**
- `top_k`: 1–100
- `episodic_weight` / `semantic_weight`: must be > 0
- `provider`: must be one of `none`, `openai`, `anthropic`, `ollama`
- `embedding_backend`: must be `local` or `openai`

**Files changed:** `cortex/core.py`

---

#### 7. VaultReader Embedding Backend Parameter

**What changed:** `VaultReader` now accepts `embedding_model` and `embedding_backend` parameters, using the same `Embedder` as the episodic layer.

**Why it matters:** Both memory layers must use the same embedding model to live in the same vector space. If the episodic layer used `all-MiniLM-L6-v2` and the semantic layer used a different model, cosine similarity scores would be meaningless across sources, breaking hybrid retrieval.

**Files changed:** `cortex/semantic/vault_reader.py`, `cortex/core.py`

---

#### 8. Safe YAML Frontmatter Generation

**What changed:** `create_note()` now uses `yaml.dump()` instead of f-string interpolation for frontmatter.

**Before (unsafe):**
```python
frontmatter = f"---\ntitle: {title}\ntags: {tags or []}\n---\n\n"
# title = "C++ & Rust" → tags: ['auth', 'it's great']  ← broken YAML
```

**After (safe):**
```python
frontmatter_dict = {"title": title, "tags": tags or []}
frontmatter = "---\n" + yaml.dump(frontmatter_dict) + "---\n\n"
# Properly escapes special characters
```

**Files changed:** `cortex/semantic/vault_reader.py`

---

#### 9. CLI `--summarize` Warns When No LLM Configured

**What changed:** `cortex remember "text" --summarize` now prints a warning if `llm.provider` is `none`, explaining that it falls back to truncation.

**Why it matters:** The flag implied LLM-based compression but silently fell back to string slicing. Users would think their memories were being intelligently summarized when they were just being cut off at 300 characters.

**Files changed:** `cortex/cli/main.py`

---

#### 10. `cortex forget` Suggests Next Steps on Failure

**What changed:** When a memory ID is not found, the error message now suggests running `cortex stats` or `cortex search` to find the correct ID.

**Files changed:** `cortex/cli/main.py`

---

#### 11. Shared Test Fixtures in `conftest.py`

**What changed:** `conftest.py` now provides reusable fixtures: `episodic_store`, `vault_reader`, `markdown_parser`, `hybrid_search_mocks`, `mock_embedder`, `vault_mock_embedder`.

**Why it matters:** Previously, each test file duplicated fixture definitions. The `conftest.py` was empty. Now fixtures are DRY, consistent, and any change to mock behavior propagates everywhere.

**Files changed:** `tests/conftest.py`, all test files updated to use shared fixtures.

---

### 🟢 MINOR FIXES

#### 12. Setuptools Build Backend

**What changed:** `build-backend = "setuptools.backends.legacy:build"` → `build-backend = "setuptools.build_meta"`

**Why it matters:** The `legacy` backend is deprecated and can cause build warnings or compatibility issues with modern pip.

**Files changed:** `pyproject.toml`

---

#### 13. EpisodicMemoryStore Log Message

**What changed:** `"EpisodicMemoryStore ready — %d memories loaded"` → `"EpisodicMemoryStore initialized — collection '%s' has %d entries"`

**Why it matters:** "loaded" implied memories were loaded into RAM. The number is actually the ChromaDB collection count on disk. The new message is accurate.

**Files changed:** `cortex/episodic/memory_store.py`

---

#### 14. Duplicate Wiki-Link Regex Removed

**What changed:** `VaultReader` had its own `_WIKI_LINK_RE` that was different from `MarkdownParser._WIKI_LINK_RE`. The duplicate has been removed.

**Why it matters:** Inconsistent regex patterns meant wiki-links could be parsed differently depending on code path, causing subtle bugs with aliases like `[[note|alias]]`.

**Files changed:** `cortex/semantic/vault_reader.py`

---

#### 15. `cortex init` Warns About Embedding Model Download

**What changed:** The init message now includes: "Note: The first search will download an embedding model (~80 MB)."

**Why it matters:** Users would run `cortex init` (instant), then `cortex remember` and experience an unexplained 30-second hang while the model downloads.

**Files changed:** `cortex/cli/main.py`

---

### NEW FILES

| File | Purpose |
|------|---------|
| `CHANGELOG.md` | This file — comprehensive change documentation |

### MODIFIED FILES

| File | Summary |
|------|---------|
| `cortex/models.py` | Added `UnifiedHit` model, `unified_hits` field on `RetrievalResult` |
| `cortex/core.py` | Pydantic config validation, `create_note()` delegation, VaultReader embedder params |
| `cortex/episodic/memory_store.py` | Timestamp restore, embedding_backend param, better log message |
| `cortex/episodic/embedder.py` | No changes (unchanged) |
| `cortex/episodic/summarizer.py` | No changes (unchanged) |
| `cortex/semantic/vault_reader.py` | Vector embeddings, BM25 fallback, safe YAML, embedder params |
| `cortex/semantic/markdown_parser.py` | No changes (unchanged) |
| `cortex/retrieval/hybrid_search.py` | True cross-source RRF fusion, `UnifiedHit` output |
| `cortex/hooks/agent_hooks.py` | `functools.wraps`, `inspect.signature` arg handling |
| `cortex/cli/main.py` | Summarize warning, forget suggestions, init note, unified output |
| `pyproject.toml` | Fixed setuptools build backend |
| `tests/conftest.py` | Full shared fixture suite |
| `tests/episodic/test_memory_store.py` | Timestamp test, uses shared fixtures |
| `tests/semantic/test_vault_reader.py` | Updated for vector search, uses shared fixtures |
| `tests/semantic/test_markdown_parser.py` | Uses shared fixture |
| `tests/retrieval/test_hybrid_search.py` | Unified hit tests, RRF monotonicity test |

---

### BREAKING CHANGES

- **`RetrievalResult.to_prompt()` now uses unified RRF ranking** — the order of results may differ from before. The output format is backward compatible.
- **`VaultReader` now requires `Embedder`** — if you instantiate `VaultReader` directly (not via `AgentMemory`), you must ensure the embedding backend is available.
- **`AgentMemory.config` is now a Pydantic `CortexConfig` object** instead of a raw dict. If you access `memory.config["episodic"]`, change to `memory.config.episodic`.

### NON-BREAKING ADDITIONS

- `RetrievalResult.unified_hits` — new field, existing code using `episodic_hits` / `semantic_hits` still works
- `AgentMemory.create_note()` — new convenience method
- `UnifiedHit` model — new type for unified retrieval results
