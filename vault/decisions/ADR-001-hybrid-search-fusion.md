---
title: "ADR-001: Hybrid Search Cross-Source Fusion"
date: 2026-04-15
tags: [architecture, retrieval, rrf, memory]
status: accepted
---

# ADR-001: Hybrid Search Cross-Source Fusion

## Context
Cortex uses Reciprocal Rank Fusion (RRF) to combine episodic memories (PRs, sessions) and semantic documents (Vault notes). 

The initial implementation used source-specific prefixes (e.g., `episodic:ID`) in the RRF scoring dictionary. While this correctly interleaved results, it prevented "fusion" — the ability for a single logical concept present in both sources to have its scores summed and thus be boosted higher. 

Furthermore, RRF scores were not being normalized or presented with clear titles, leading to a "frozen" user experience where results always appeared with a score of 0.016 (Rank 1 score).

## Decision
We decided to refactor the `HybridSearch` engine to:
1.  **Enforce Additive Scoring**: Change the RRF dictionary assignment from `=` to `+=` to allow for potential cross-source boosting.
2.  **Canonical Data Model**: Introduce `display_title` in the shared models to ensure that even without manual titles, the engine can present a user-friendly summary of the memory.
3.  **CI/CD Transparency**: Update the GitHub Actions bot to use these unified fields, eliminating the "blank title" bug.

## Consequences
- **Positive**: Results identified in both Vault and Memories will now rank significantly higher.
- **Positive**: Documentation in PRs is now clearly labeled and readable.
- **Negative**: The RRF constant ($K=60$) remains conservative; scores for Rank-1 items still start at 0.016, but can now grow with reinforcements.
