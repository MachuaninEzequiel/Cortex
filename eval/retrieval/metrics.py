"""
eval.retrieval.metrics
----------------------
Pure retrieval-quality metrics for the Fase D evaluation suite.

All functions are **list-in / list-out** (or float-out): they take a
pre-ranked list of document identifiers and a set of relevant identifiers,
and never touch the filesystem, the network or the Cortex pipeline. This
keeps them trivially unit-testable and reusable by any runner.

Conventions:
- ``ranked`` is ordered best-first; ties must already be broken by the caller.
- An empty ``relevant`` set yields 0.0 (not a mathematical recall), so that
  aggregations stay simple and a malformed query cannot inflate the mean.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence


def hit_at_k(ranked: Sequence[str], relevant: Iterable[str], k: int) -> bool:
    """True if at least one relevant doc appears in the top-k positions."""
    if k <= 0:
        return False
    rel = set(relevant)
    if not rel:
        return False
    return any(doc in rel for doc in ranked[:k])


def recall_at_k(ranked: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """Fraction of relevant docs retrieved within the top-k.

    Duplicates in ``ranked`` count once (set semantics).
    """
    rel = set(relevant)
    if not rel or k <= 0:
        return 0.0
    top = set(ranked[:k])
    return len(top & rel) / len(rel)


def reciprocal_rank(
    ranked: Sequence[str], relevant: Iterable[str], k: int | None = None
) -> float:
    """Reciprocal rank of the first relevant doc (optionally within top-k).

    Returns 0.0 when no relevant doc is found.
    """
    rel = set(relevant)
    if not rel:
        return 0.0
    cutoff = len(ranked) if k is None else min(k, len(ranked))
    for i in range(cutoff):
        if ranked[i] in rel:
            return 1.0 / (i + 1)
    return 0.0


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def mean_reciprocal_rank(
    queries: Sequence[tuple[Sequence[str], Iterable[str]]],
    k: int | None = 10,
) -> float:
    """MRR@k over ``(ranked, relevant)`` pairs.

    This is the primary decision metric of Fase D.
    """
    return _mean([reciprocal_rank(ranked, relevant, k=k) for ranked, relevant in queries])


def macro_recall_at_k(
    queries: Sequence[tuple[Sequence[str], Iterable[str]]],
    k: int,
) -> float:
    """Fraction of queries with at least one relevant doc in top-k.

    This matches the spec's operational definition of "recall@k" for the
    decision table (hit-rate over queries); use :func:`recall_at_k` for the
    per-query set-based fraction.
    """
    if not queries:
        return 0.0
    hits = sum(1 for ranked, relevant in queries if hit_at_k(ranked, relevant, k))
    return hits / len(queries)


__all__ = [
    "hit_at_k",
    "macro_recall_at_k",
    "mean_reciprocal_rank",
    "recall_at_k",
    "reciprocal_rank",
]
