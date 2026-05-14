---
schema_version: 1
doc_type: architecture
title: Release 2 Known Weaknesses and Hardening Backlog
created_at: '2026-05-13T22:29:18.577758+00:00'
updated_at: '2026-05-13T22:29:18.577758+00:00'
tags:
- architecture
- technical-debt
- release-2
- hardening
- backlog
status: current
links:
- ADR-001-hybrid-search-fusion
- architecture
vault_scope: local
fingerprint: fc6c871492d93a4c9becaaf5b93616fa17b324a7d7b1c970cf903c467ef94760
related_adrs: []
legacy_last_review: 2026-05-13
---

> [!success] **2026-05-13 final review (Olas 0–4 closed)**
> All seven items audited and addressed:
> - **#1, #3, #4, #5, #6** — fully resolved (see status notes inline).
> - **#7** — resolved in Ola 4 via mutually-exclusive classification
>   in `verify_from_diff` plus 6 regression tests in
>   `tests/unit/test_doc_verifier.py::TestClassificationContract`.
> - **#2** — scoped out: the empty-query transport pattern is intentional
>   for now and gracefully degrades to no graph boost. A proper
>   "list all memories" episodic API is tracked in
>   `docs/roadmap/post-adopters.md` for the next release cycle.
> This document is preserved for historical context but should be
> considered **fully reviewed** with respect to Release 2 hardening.

# Release 2 Known Weaknesses and Hardening Backlog

> [!info]
> This note captures implementation weaknesses confirmed during the initial
> architecture review for Release 2. The goal is not to interrupt the current
> feature stream, but to preserve a precise hardening backlog for later work.

## Scope

This document records weaknesses that are already present in the codebase and
should be revisited after the current Release 2 implementation work is complete.

## Confirmed Weaknesses

### 1. ~~Entity search is conceptually implemented but not actually persisted~~ — **RESOLVED 2026-05-13**

Verified: `_serialize_metadata` in `cortex/episodic/memory_store.py:292-311` flattens the full `entry.metadata` (entities included) into Chroma metadata via `metadata_json` (JSON-encoded). `_deserialize_metadata` (lines 313-350) restores it. Additionally, every individual entity is also persisted as a boolean flag key (`_entity_filter_key`) so Chroma's `where=` filter can locate memories by entity in O(1). Coverage added in `tests/unit/episodic/test_memory_store.py::test_entity_round_trip_by_type` (parametrised across 7 entity types) plus 3 supporting tests for multi-type, extra-metadata coexistence and strict filtering.

- **Area**: Episodic memory / entity retrieval
- **Files**:
  - `cortex/episodic/memory_store.py`
- **Problem**:
  - `EpisodicMemoryStore.add()` extracts entities and attaches them to
    `entry.metadata`.
  - `_serialize_metadata()` only persists `id`, `memory_type`, `tags`, `files`
    and `timestamp`.
  - `_deserialize_metadata()` rebuilds the `MemoryEntry` without restoring
    entity metadata.
  - As a consequence, `search_by_entity()` reads `entry.metadata.get("entities", {})`
    from retrieved memories, but that structure is usually absent after round-trip
    persistence.
- **Impact**:
  - The entity-search feature exists in the API surface, but its retrieval
    quality is much lower than the code suggests.
  - The context enricher may rely on a capability that is only partially real.
- **Recommended follow-up**:
  - Persist entities explicitly in Chroma metadata.
  - Restore metadata on deserialization.
  - Add round-trip tests that prove entity retrieval survives storage.

### 2. ~~Co-occurrence and typed-graph boosts may silently disable themselves~~ — **SCOPED OUT 2026-05-13**

Audited: behaviour degrades gracefully (other 4 enrichment strategies still work), so this is not a demo-blocker for early adopters. A proper fix requires adding an explicit ``EpisodicMemoryStore.list_all(branch=None, limit=None)`` API and refactoring `_build_co_occurrence` + `_build_typed_graph` to consume it — sized as a minor release. Tracked in `docs/roadmap/post-adopters.md`.

- **Area**: Context enricher / graph expansion
- **Files**:
  - `cortex/context_enricher/enricher.py`
  - `cortex/episodic/embedder.py`
- **Problem**:
  - `_build_co_occurrence()` and `_build_typed_graph()` call
    `self.episodic.search("", top_k=...)` to approximate “get all memories”.
  - The embedder rejects empty text (`Cannot embed empty text.`).
  - Those failures are swallowed by broad exception handling and converted into
    empty graph/co-occurrence structures.
- **Impact**:
  - Graph-based ranking signals can disappear without obvious runtime failure.
  - The system may look stable while ranking quality quietly degrades.
- **Recommended follow-up**:
  - Introduce an explicit “list all memories” path in the episodic store.
  - Stop using empty-query search as a transport mechanism.
  - Add tests that assert graph enrichment remains active with real stored data.

### 3. ~~MCP context tool calls a method that does not exist~~ — **RESOLVED 2026-05-13**

Verified: `cortex/mcp/server.py:651` uses `related.to_prompt()` on a `RetrievalResult` (which **does** define `to_prompt()` in `models.py:132`), and `:654` uses `enriched.to_prompt_format()` on an `EnrichedContext` (which defines `to_prompt_format()` in `models.py:320`). `cortex/autopilot/budget_profiles.py:51-63` adds defensive fallback. Original report conflated the two classes — both APIs now exist and are exercised by the test suite.

- **Area**: MCP server integration
- **Files**:
  - `cortex/mcp_server.py`
  - `cortex/models.py`
- **Problem**:
  - `cortex_context()` returns `context.to_prompt()`.
  - `EnrichedContext` exposes `to_prompt_format()`, not `to_prompt()`.
- **Impact**:
  - The MCP tool for proactive context is at risk of failing at runtime.
  - This directly affects the IDE integration story, which is part of the
    product promise.
- **Recommended follow-up**:
  - Align the MCP server with `EnrichedContext.to_prompt_format()`.
  - Add focused tests for MCP tool behavior.

### 4. ~~Setup defaults drift from the ONNX-first architecture~~ — **RESOLVED 2026-05-13**

Verified: `cortex/setup/templates.py:60` emits `embedding_backend: onnx`. `cortex/cli/main.py:78` `_DEFAULT_CONFIG` also sets `onnx`. README and config narrative aligned.

- **Area**: Setup / generated configuration
- **Files**:
  - `cortex/setup/templates.py`
  - `config.yaml`
  - `README.md`
- **Problem**:
  - The current narrative of the project promotes ONNX as the lightweight
    default backend.
  - `render_config_yaml()` still generates `embedding_backend: local`.
- **Impact**:
  - Fresh setups may pull the project back toward the heavier local
    sentence-transformers path.
  - Product behavior and generated defaults are currently misaligned.
- **Recommended follow-up**:
  - Make generated config match the intended ONNX-first default.
  - Review setup docs and migration notes to keep them consistent.

### 5. ~~Generated CI templates invoke unsupported CLI flags~~ — **RESOLVED 2026-05-13**

Verified: `cortex remember` in `cortex/cli/main.py:1059-1066` accepts `--branch`, `--commit`, `--repo`. Generated `pr-context capture` workflow steps use these flags and they map to existing CLI options.

- **Area**: Setup / GitHub Actions templates
- **Files**:
  - `cortex/setup/templates.py`
  - `cortex/cli/main.py`
- **Problem**:
  - Some generated workflow steps call `cortex remember` with flags such as
    `--branch` and `--commit`.
  - The current CLI command definition for `remember` does not accept those
    options.
- **Impact**:
  - Newly generated workflows can contain commands that do not match the
    shipped CLI contract.
  - Setup may appear successful while generated automation is already drifting.
- **Recommended follow-up**:
  - Either add the missing CLI options or simplify the templates to only use
    supported arguments.
  - Cover generated workflow commands with contract-level tests.

### 6. ~~`cortex context --output` always writes markdown, even when JSON is requested~~ — **RESOLVED 2026-05-13**

Verified: `cortex/cli/main.py:708-714` branches by `--format` (json | compact | markdown) when writing the output file. Regression coverage added in `tests/unit/cli/test_main.py::test_context_output_json_writes_parseable_json`, `test_context_output_markdown_default_writes_markdown`, `test_context_output_compact_writes_compact_markdown`.

- **Area**: CLI output consistency
- **Files**:
  - `cortex/cli/main.py`
- **Problem**:
  - The command prints JSON to stdout when `--format json` is used.
  - The file written via `--output` always uses `enriched.to_prompt_format()`,
    which is markdown-oriented.
- **Impact**:
  - Automation consumers may believe they are saving JSON while actually
    receiving markdown in the output file.
  - This creates a subtle contract mismatch for scripts and CI steps.
- **Recommended follow-up**:
  - Make file output honor the selected format.
  - Add CLI tests for stdout/file parity.

### 7. ~~Doc verification has a classification inconsistency for vault files~~ — **RESOLVED 2026-05-13**

Verified: `cortex/doc_verifier.py::verify_from_diff` refactored to a single classification pass with mutually-exclusive partitions (`new_files`, `modified_files`, `deleted_files`) whose union equals `vault_files`. New helper `_vault_relative_md` centralises the vault-prefix + `.md` filter. Coverage added in `tests/unit/test_doc_verifier.py::TestClassificationContract` (6 tests).

- **Area**: Documentation verification
- **Files**:
  - `cortex/doc_verifier.py`
- **Problem**:
  - In `verify_from_diff()`, one condition skips paths that start with
    `vault_rel + "/"`, and the following condition tries to classify those same
    paths as vault documents.
  - This makes `vault_files` accounting less trustworthy than the later
    `new_files` and `modified_files` logic.
- **Impact**:
  - Summary counts can become misleading even if the yes/no decision still
    behaves correctly in some flows.
  - That weakens confidence in CI diagnostics.
- **Recommended follow-up**:
  - Simplify path classification into a single consistent branch.
  - Add tests for `vault_files`, `new_files`, `modified_files` and `deleted_files`
    together.

## Testing Gaps Observed During Review

- CLI coverage is still low relative to how central the CLI is to the product.
- `mcp_server.py`, `ide_installer.py` and `hooks/agent_hooks.py` currently have
  little or no meaningful test protection.
- `setup/cold_start.py` has very low coverage despite being important for
  first-run experience.
- Some context-enricher integration tests validate interfaces and shape, but not
  always the full behavioral path under real persistence conditions.

## Suggested Hardening Order

1. Fix MCP runtime compatibility and CLI/template contract drift.
2. Repair entity persistence and graph/co-occurrence retrieval foundations.
3. Align setup defaults with the intended ONNX-first product direction.
4. Expand test coverage around CLI, MCP, cold start and generated workflows.

## Related Notes

- [[architecture]]
- [[ADR-001-hybrid-search-fusion]]
