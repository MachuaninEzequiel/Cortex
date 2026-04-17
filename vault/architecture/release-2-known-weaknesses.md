---
title: "Release 2 Known Weaknesses and Hardening Backlog"
date: 2026-04-16
tags: [architecture, technical-debt, release-2, hardening, backlog]
status: active
---

# Release 2 Known Weaknesses and Hardening Backlog

> [!info]
> This note captures implementation weaknesses confirmed during the initial
> architecture review for Release 2. The goal is not to interrupt the current
> feature stream, but to preserve a precise hardening backlog for later work.

## Scope

This document records weaknesses that are already present in the codebase and
should be revisited after the current Release 2 implementation work is complete.

## Confirmed Weaknesses

### 1. Entity search is conceptually implemented but not actually persisted

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

### 2. Co-occurrence and typed-graph boosts may silently disable themselves

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

### 3. MCP context tool calls a method that does not exist

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

### 4. Setup defaults drift from the ONNX-first architecture

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

### 5. Generated CI templates invoke unsupported CLI flags

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

### 6. `cortex context --output` always writes markdown, even when JSON is requested

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

### 7. Doc verification has a classification inconsistency for vault files

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
