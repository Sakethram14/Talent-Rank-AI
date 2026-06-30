"""
Tests for the IR metrics module.

Validates NDCG@k, MAP, Precision@k, and MRR against known results
and edge cases.
"""

from __future__ import annotations

import math
import pytest

from src.evaluation.metrics import (
    mean_average_precision,
    mrr,
    ndcg_at_k,
    precision_at_k,
)


# ── NDCG@k ──────────────────────────────────────────────────────────────────


class TestNDCG:
    """Tests for Normalised Discounted Cumulative Gain."""

    def test_perfect_ranking(self) -> None:
        """A perfect ranking (descending relevance) should yield NDCG = 1.0."""
        scores = [3.0, 2.0, 1.0, 0.0]
        assert ndcg_at_k(scores, k=4) == pytest.approx(1.0)

    def test_perfect_ranking_partial_k(self) -> None:
        """NDCG@2 on a perfect ranking is still 1.0."""
        scores = [3.0, 2.0, 1.0, 0.0]
        assert ndcg_at_k(scores, k=2) == pytest.approx(1.0)

    def test_worst_ranking(self) -> None:
        """Reversed ranking should give NDCG < 1.0."""
        scores = [0.0, 1.0, 2.0, 3.0]
        result = ndcg_at_k(scores, k=4)
        assert 0.0 < result < 1.0

    def test_partial_ranking(self) -> None:
        """Known partial ranking with hand-calculated NDCG."""
        # relevance: [3, 1, 2]  at positions 1, 2, 3
        # DCG  = 3/log2(2) + 1/log2(3) + 2/log2(4)
        #      = 3 + 0.6309 + 1.0  = 4.6309
        # IDCG (ideal [3, 2, 1]):
        #      = 3/log2(2) + 2/log2(3) + 1/log2(4)
        #      = 3 + 1.2619 + 0.5 = 4.7619
        # NDCG = 4.6309 / 4.7619 ≈ 0.9725
        scores = [3.0, 1.0, 2.0]
        result = ndcg_at_k(scores, k=3)
        expected_dcg = 3.0 / math.log2(2) + 1.0 / math.log2(3) + 2.0 / math.log2(4)
        expected_idcg = 3.0 / math.log2(2) + 2.0 / math.log2(3) + 1.0 / math.log2(4)
        assert result == pytest.approx(expected_dcg / expected_idcg, rel=1e-4)

    def test_single_element(self) -> None:
        """Single-element list → NDCG = 1.0 when relevance > 0."""
        assert ndcg_at_k([5.0], k=1) == pytest.approx(1.0)

    def test_all_zeros(self) -> None:
        """All-zero relevance → NDCG = 0.0 (IDCG is 0)."""
        assert ndcg_at_k([0.0, 0.0, 0.0], k=3) == 0.0

    def test_empty_list(self) -> None:
        """Empty list → 0.0."""
        assert ndcg_at_k([], k=5) == 0.0

    def test_k_zero(self) -> None:
        """k=0 → 0.0."""
        assert ndcg_at_k([3.0, 2.0], k=0) == 0.0

    def test_k_negative(self) -> None:
        """Negative k → 0.0."""
        assert ndcg_at_k([3.0, 2.0], k=-1) == 0.0

    def test_k_larger_than_list(self) -> None:
        """k exceeding list length uses len(list) as effective k."""
        scores = [3.0, 2.0]
        assert ndcg_at_k(scores, k=100) == pytest.approx(1.0)

    def test_identical_scores(self) -> None:
        """All identical non-zero scores → NDCG = 1.0 (any order is ideal)."""
        assert ndcg_at_k([2.0, 2.0, 2.0], k=3) == pytest.approx(1.0)


# ── Precision@k ──────────────────────────────────────────────────────────────


class TestPrecisionAtK:
    """Tests for Precision@k."""

    def test_all_relevant(self) -> None:
        """All items relevant → precision = 1.0."""
        scores = [1.0, 1.0, 1.0]
        assert precision_at_k(scores, k=3) == pytest.approx(1.0)

    def test_none_relevant(self) -> None:
        """No items relevant → precision = 0.0."""
        scores = [0.0, 0.0, 0.0]
        assert precision_at_k(scores, k=3) == pytest.approx(0.0)

    def test_half_relevant(self) -> None:
        """Two of four relevant → precision = 0.5."""
        scores = [1.0, 0.0, 1.0, 0.0]
        assert precision_at_k(scores, k=4) == pytest.approx(0.5)

    def test_k_smaller_than_list(self) -> None:
        """Only look at first k items."""
        scores = [1.0, 0.0, 0.0, 1.0, 1.0]
        assert precision_at_k(scores, k=2) == pytest.approx(0.5)

    def test_custom_threshold(self) -> None:
        """Use a custom relevance threshold."""
        scores = [0.5, 0.8, 0.3]
        assert precision_at_k(scores, k=3, threshold=0.5) == pytest.approx(2.0 / 3)

    def test_empty_list(self) -> None:
        assert precision_at_k([], k=5) == 0.0

    def test_k_zero(self) -> None:
        assert precision_at_k([1.0, 1.0], k=0) == 0.0

    def test_k_negative(self) -> None:
        assert precision_at_k([1.0], k=-1) == 0.0

    def test_k_exceeds_list(self) -> None:
        """k > len → uses len as effective k."""
        scores = [1.0, 0.0]
        assert precision_at_k(scores, k=10) == pytest.approx(0.5)


# ── MAP (Average Precision) ────────────────────────────────────────────────


class TestMAP:
    """Tests for Mean Average Precision (single-query = AP)."""

    def test_all_relevant(self) -> None:
        """All relevant → MAP = 1.0."""
        assert mean_average_precision([1.0, 1.0, 1.0]) == pytest.approx(1.0)

    def test_none_relevant(self) -> None:
        """No relevant → MAP = 0.0."""
        assert mean_average_precision([0.0, 0.0, 0.0]) == pytest.approx(0.0)

    def test_known_computation(self) -> None:
        """Hand-verified MAP calculation.

        Relevant at positions 1, 3, 4 → precisions 1/1, 2/3, 3/4
        AP = (1 + 2/3 + 3/4) / 3 ≈ 0.8056
        """
        scores = [1.0, 0.0, 1.0, 1.0, 0.0]
        expected = (1.0 + 2.0 / 3 + 3.0 / 4) / 3
        assert mean_average_precision(scores) == pytest.approx(expected, rel=1e-4)

    def test_single_relevant_at_start(self) -> None:
        """Single relevant at position 1 → MAP = 1.0."""
        assert mean_average_precision([1.0, 0.0, 0.0]) == pytest.approx(1.0)

    def test_single_relevant_at_end(self) -> None:
        """Single relevant at last position."""
        scores = [0.0, 0.0, 1.0]
        # precision at rank 3 = 1/3;  AP = (1/3)/1 = 1/3
        assert mean_average_precision(scores) == pytest.approx(1.0 / 3, rel=1e-4)

    def test_empty_list(self) -> None:
        assert mean_average_precision([]) == 0.0

    def test_custom_threshold(self) -> None:
        """Scores below threshold are ignored."""
        scores = [0.5, 0.3, 0.8]
        # threshold=0.5 → relevant at pos 1 (0.5) and pos 3 (0.8)
        # precisions: 1/1, 2/3 → AP = (1 + 2/3)/2 = 5/6
        expected = (1.0 + 2.0 / 3) / 2
        assert mean_average_precision(scores, threshold=0.5) == pytest.approx(
            expected, rel=1e-4
        )


# ── MRR ──────────────────────────────────────────────────────────────────────


class TestMRR:
    """Tests for Mean Reciprocal Rank."""

    def test_first_relevant(self) -> None:
        """First item relevant → MRR = 1.0."""
        assert mrr([1.0, 0.0, 0.0]) == pytest.approx(1.0)

    def test_second_relevant(self) -> None:
        """Second item relevant → MRR = 0.5."""
        assert mrr([0.0, 1.0, 0.0]) == pytest.approx(0.5)

    def test_third_relevant(self) -> None:
        """Third item relevant → MRR = 1/3."""
        assert mrr([0.0, 0.0, 1.0]) == pytest.approx(1.0 / 3)

    def test_no_relevant(self) -> None:
        """No relevant items → MRR = 0.0."""
        assert mrr([0.0, 0.0, 0.0]) == 0.0

    def test_empty_list(self) -> None:
        assert mrr([]) == 0.0

    def test_all_relevant(self) -> None:
        """All relevant → MRR = 1.0 (first is at position 1)."""
        assert mrr([1.0, 1.0, 1.0]) == pytest.approx(1.0)

    def test_custom_threshold(self) -> None:
        """Only values >= threshold count as relevant."""
        scores = [0.3, 0.7, 0.9]
        assert mrr(scores, threshold=0.5) == pytest.approx(0.5)


# ── Composite edge cases ────────────────────────────────────────────────────


class TestEdgeCases:
    """Cross-cutting edge-case tests."""

    def test_single_element_relevant(self) -> None:
        """Single relevant element works across all metrics."""
        scores = [1.0]
        assert ndcg_at_k(scores, k=1) == pytest.approx(1.0)
        assert precision_at_k(scores, k=1) == pytest.approx(1.0)
        assert mean_average_precision(scores) == pytest.approx(1.0)
        assert mrr(scores) == pytest.approx(1.0)

    def test_single_element_irrelevant(self) -> None:
        """Single irrelevant element returns 0 across all metrics."""
        scores = [0.0]
        assert ndcg_at_k(scores, k=1) == 0.0
        assert precision_at_k(scores, k=1) == 0.0
        assert mean_average_precision(scores) == 0.0
        assert mrr(scores) == 0.0

    def test_large_k_all_metrics(self) -> None:
        """Very large k doesn't crash any metric."""
        scores = [1.0, 0.0]
        k = 10_000
        assert ndcg_at_k(scores, k=k) >= 0.0
        assert precision_at_k(scores, k=k) >= 0.0

    def test_float_relevance_scores(self) -> None:
        """Non-integer relevance scores are handled correctly."""
        scores = [2.5, 1.5, 0.5]
        result = ndcg_at_k(scores, k=3)
        assert 0.0 <= result <= 1.0
