"""Unit tests for eval.retrieval.metrics — pure list-in/list-out metrics.

Edge cases covered: empty inputs, k larger than n, ties, no relevant hits,
perfect ranking, hit at position 3 (MRR = 1/3).
"""

from __future__ import annotations

import pytest

from eval.retrieval.metrics import (
    hit_at_k,
    mean_reciprocal_rank,
    recall_at_k,
    reciprocal_rank,
)


class TestHitAtK:
    def test_hit_in_top_k(self):
        assert hit_at_k(["a", "b", "c"], {"b"}, k=3) is True

    def test_relevant_outside_top_k(self):
        assert hit_at_k(["a", "b", "c"], {"d"}, k=2) is False
        assert hit_at_k(["a", "b", "c", "d"], {"d"}, k=2) is False

    def test_empty_ranked(self):
        assert hit_at_k([], {"a"}, k=5) is False

    def test_empty_relevant_is_not_a_hit(self):
        # No relevant docs defined -> the query cannot produce a hit.
        assert hit_at_k(["a"], set(), k=1) is False

    def test_k_larger_than_n(self):
        assert hit_at_k(["a"], {"a"}, k=10) is True

    def test_k_zero_never_hits(self):
        assert hit_at_k(["a"], {"a"}, k=0) is False


class TestRecallAtK:
    def test_all_relevant_in_top_k(self):
        assert recall_at_k(["a", "b"], {"a", "b"}, k=2) == pytest.approx(1.0)

    def test_partial_recall(self):
        # 1 of 2 relevant docs in top-3.
        assert recall_at_k(["x", "a", "y"], {"a", "b"}, k=3) == pytest.approx(0.5)

    def test_no_relevant_retrieved(self):
        assert recall_at_k(["x", "y"], {"a"}, k=2) == pytest.approx(0.0)

    def test_empty_ranked(self):
        assert recall_at_k([], {"a"}, k=5) == 0.0

    def test_empty_relevant_returns_zero_by_convention(self):
        # Undefined mathematically; we fix it at 0.0 to keep aggregation simple.
        assert recall_at_k(["a"], set(), k=3) == 0.0

    def test_k_larger_than_n(self):
        assert recall_at_k(["b", "a"], {"a", "b", "c"}, k=10) == pytest.approx(2 / 3)

    def test_duplicates_counted_once(self):
        assert recall_at_k(["a", "a", "b"], {"a", "b"}, k=3) == pytest.approx(1.0)


class TestReciprocalRank:
    def test_perfect_ranking(self):
        assert reciprocal_rank(["a", "b"], {"a"}) == pytest.approx(1.0)

    def test_hit_at_position_3(self):
        assert reciprocal_rank(["x", "y", "a"], {"a"}) == pytest.approx(1 / 3)

    def test_no_hit(self):
        assert reciprocal_rank(["x", "y"], {"z"}) == 0.0

    def test_empty_ranked(self):
        assert reciprocal_rank([], {"a"}) == 0.0

    def test_empty_relevant(self):
        assert reciprocal_rank(["a"], set()) == 0.0

    def test_first_of_several_relevant_wins(self):
        # RR uses the FIRST relevant position, not the best-scoring tie group.
        assert reciprocal_rank(["x", "b", "a"], {"a", "b"}) == pytest.approx(0.5)


class TestMeanReciprocalRank:
    def test_perfect_queries_average_to_one(self):
        queries = [(["a"], {"a"}), (["a", "b"], {"a"})]
        assert mean_reciprocal_rank(queries) == pytest.approx(1.0)

    def test_known_mix(self):
        # RR: 1.0 and 1/3 -> mean 2/3.
        queries = [(["a"], {"a"}), (["x", "y", "a"], {"a"})]
        assert mean_reciprocal_rank(queries) == pytest.approx((1.0 + 1 / 3) / 2)

    def test_all_misses(self):
        queries = [(["x"], {"a"}), ([], {"b"})]
        assert mean_reciprocal_rank(queries) == 0.0

    def test_empty_query_set_returns_zero(self):
        assert mean_reciprocal_rank([]) == 0.0


class TestTies:
    """Rankings arrive pre-sorted as lists; equal scores must respect input order."""

    def test_tied_order_preserved_for_hit(self):
        ranked = ["noise", "target"]  # same score implied; caller order decides.
        assert hit_at_k(ranked, {"target"}, k=2) is True
        assert reciprocal_rank(ranked, {"target"}) == pytest.approx(0.5)
