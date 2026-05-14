---
schema_version: 1
doc_type: session
title: Memory Engine Optimization & CI Visualization Fix
created_at: '2026-04-15T23:05:16.109617+00:00'
updated_at: '2026-04-15T23:05:16.109617+00:00'
tags:
- memory
- rrf
- bug-fix
- ci-cd
- windows
status: completed
links: []
vault_scope: local
fingerprint: 0438c582f43d28d10228a40528ace556a614784a8f88ad8f2cef34d3964c3db1
session_id: 2026-04-15-m
pr: null
branch: null
commit: null
cortex_telemetry: null
---

# Session: Memory Engine Optimization & CI Visualization Fix

## Summary
Optimized the retrieval engine to support additive cross-source fusion (RRF) and fixed a critical visualization bug in the CI/CD pipeline where memories were being displayed with blank titles. Also stabilized the test suite for Windows cross-platform compatibility.

## Changes Made
- `cortex/retrieval/hybrid_search.py`: Refactored RRF logic to use additive scoring instead of simple assignment.
- `cortex/models.py`: Added `display_title` property to `UnifiedHit` for consistent metadata presentation.
- `cortex/setup/templates.py`: Updated GitHub Actions bot script to use `display_title`, fixing the "empty title" bug in PR comments.
- `tests/setup/test_orchestrator.py`: Relaxed permission checks on Windows to avoid false-positive test failures.
- `vault/decisions/ADR-001-hybrid-search-fusion.md`: Documented the architectural shift in retrieval logic.

## Decisions Taken
- **Decision**: Logic fusion -> Accumulative scores -> Necessary to allow episodic and semantic memory to complement each other.
- **Decision**: `display_title` property -> Added to model -> Simplifies consumption for downstream UI components without breaking Pydantic schemas.

## Next Steps
- [ ] Observe PR #9 pipeline behavior with new documentation files.
- [ ] Verify if RRF scores increase when multi-source matches occur in larger datasets.
