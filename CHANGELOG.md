# CHANGELOG

## [Unreleased]

### 🔵 Current Focus
- **Enterprise Memory Actualization**: Refining the integration between local Python codebase and Obsidian-based documentation pipeline.
- **MCP Server Optimization**: Streamlining context synchronization for high-latency environments.
- **Improved Context Injection**: Fine-tuning co-occurrence boost and domain detection.

---

## [2.5.0] — 2026-04-28

### 🔴 Enterprise Foundation
**What changed:** 
- Introduced `.cortex/org.yaml` for multi-project governance.
- **Multi-level Retrieval**: Capabilities to search across local and corporate memory spaces simultaneously.
- **Enterprise Doctor**: Advanced diagnostic tool for memory topology and governance health.

**Why it matters:** Enables Cortex to scale from a single-repo tool to an organization-wide knowledge system where agents can leverage cross-project context.

### 🟡 Cortex-Pi CLI
**What changed:**
- **Premium Branding**: Implementation of TrueColor ASCII branding and a high-fidelity visual identity.
- **Release 2.5 Protocol**: Mandatory integration of Security and Test subagents into the default development flow.
- **Pi Extensions**: Plugin system for customizing agent behavior in the Pi environment.

**Why it matters:** Provides a professional-grade interface that enforces project governance standards while offering a premium developer experience.

### 🟢 Infrastructure & Documentation
- **CI Stabilization**: Massive refactor of GitHub Actions pipelines to ensure 100% reliability in hardening gates.
- **Strategic Docs**: Reorganized enterprise-grade documentation into `docs/enterprise/`.

---

## [2.4.0] — 2026-04-25

### 🔴 Architectural Overhaul
**What changed:**
- **Core Refactor**: `cortex/core.py` transitioned to a clean Facade pattern with dependency injection for `cortex/services/`.
- **Pipeline Module**: Introduced `cortex/pipeline/` to replace legacy bash scripts for CI/CD gates.
- **MCP Delegation**: Parallel execution of subagent tasks (`_delegate_task`, `_delegate_batch`).

**Why it matters:** Improves maintainability and allows for more complex orchestration patterns without bloating the core logic.

### 🟡 Intelligence & Speed
**What changed:**
- **Adaptive RRF**: Fusion weights now adjust dynamically based on query intent.
- **Async Context Enricher**: Implemented `asyncio.gather` for concurrent context resolution.
- **Lazy Embedders**: `EmbeddersFactory` now loads backends on-demand, reducing CLI startup time.

**Why it matters:** Faster responses and more relevant results, especially in large-scale repositories.

### 🟢 Quality & Security
- **Property-Based Testing**: Added Hypothesis tests for RRF mathematical boundaries.
- **WebGraph Security**: CSRF protection via `X-Cortex-WebGraph` tokens.
- **Contract Testing**: Standardized tests for any new embedding backend.

---

## [2.0.0] — 2026-04-17

### 🔴 CRITICAL FIXES

#### 1. Semantic Memory Now Uses True Vector Embeddings
**What changed:** `VaultReader` no longer performs naive keyword counting. It now embeds every vault document using the same `Embedder` as the episodic layer.
**Why it matters:** Enables genuine cosine-similarity semantic search, allowing the agent to find documents by meaning rather than just exact words.

#### 2. True Cross-Source Reciprocal Rank Fusion (RRF)
**What changed:** RRF now fuses episodic and semantic results into a **single unified ranked list**.
**Why it matters:** Previously, sources didn't compete. Now, a highly relevant semantic doc can correctly outrank a weakly relevant episodic memory.

#### 3. Timestamp Restored on Episodic Memory Retrieval
**What changed:** Fixed a bug where retrieved memories always showed `datetime.now()`.
**Why it matters:** Restores chronological context to retrieved events.

### 🟡 IMPORTANT IMPROVEMENTS

#### 4. `AgentMemory.create_note()` Added to Public API
Added convenience method for creating semantic notes without accessing internal modules.

#### 5. `CortexHook` Decorator Enhancements
Uses `functools.wraps` and `inspect.signature` for better metadata preservation and readable input capture.

#### 6. Config Validated with Pydantic
A full Pydantic hierarchy now validates all `config.yaml` values on startup, rejecting invalid configurations early.

### 🟢 MINOR FIXES & CHORES
- **Modern Build Backend**: Switched to `setuptools.build_meta`.
- **Centralized Fixtures**: Moved all test fixtures to `tests/conftest.py`.
- **CLI Warnings**: Improved feedback when LLMs are not configured or when memory IDs are missing.

---

### BREAKING CHANGES (v2.0.0)
- `RetrievalResult.to_prompt()` uses unified RRF ranking.
- `AgentMemory.config` is now a Pydantic object (access via dot notation instead of keys).
- `VaultReader` now requires an `Embedder` instance.
