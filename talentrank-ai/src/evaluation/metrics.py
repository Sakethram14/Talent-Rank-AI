"""
Information-retrieval metrics for ranking evaluation.

These metrics are used for *self-evaluation* — measuring how well the
pipeline's ranking aligns with an internally-constructed relevance
signal (e.g. honeypot detection, feature-score ordering).  They are
**not** compared against hidden ground truth.

All functions are pure, stateless, and handle edge cases gracefully.
"""

from __future__ import annotations

import math
from typing import Optional

from src.utils.logging import get_logger

logger = get_logger("evaluation.metrics")


# ---------------------------------------------------------------------------
# NDCG@k
# ---------------------------------------------------------------------------


def ndcg_at_k(relevance_scores: list[float], k: int) -> float:
    """Compute Normalised Discounted Cumulative Gain at rank *k*.

    Args:
        relevance_scores: Relevance values in *predicted* rank order
            (index 0 = top-ranked item).
        k: Cut-off position (1-indexed).

    Returns:
        NDCG value in ``[0.0, 1.0]``.  Returns ``0.0`` when the input
        is empty, *k* ≤ 0, or all relevance scores are zero.
    """
    if not relevance_scores or k <= 0:
        return 0.0

    k = min(k, len(relevance_scores))

    dcg = _dcg(relevance_scores[:k])
    ideal_scores = sorted(relevance_scores, reverse=True)[:k]
    idcg = _dcg(ideal_scores)

    if idcg == 0.0:
        return 0.0

    return dcg / idcg


def _dcg(scores: list[float]) -> float:
    """Discounted Cumulative Gain (helper).

    Uses the standard formula: ``sum(rel_i / log2(i + 2))`` for
    *i* in 0 … len-1 (position *i + 1* is 1-indexed).
    """
    return sum(
        rel / math.log2(i + 2) for i, rel in enumerate(scores)
    )


# ---------------------------------------------------------------------------
# Mean Average Precision (MAP)
# ---------------------------------------------------------------------------


def mean_average_precision(relevance_scores: list[float], threshold: float = 1.0) -> float:
    """Compute Mean Average Precision for a single ranked list.

    Since we have a single query, this is equivalent to Average Precision
    (AP).

    Args:
        relevance_scores: Relevance values in predicted rank order.
        threshold: Minimum relevance value to consider an item relevant.

    Returns:
        MAP (AP) in ``[0.0, 1.0]``.  Returns ``0.0`` when there are no
        relevant items or the list is empty.
    """
    if not relevance_scores:
        return 0.0

    num_relevant = 0
    precision_sum = 0.0

    for i, rel in enumerate(relevance_scores, start=1):
        if rel >= threshold:
            num_relevant += 1
            precision_sum += num_relevant / i

    if num_relevant == 0:
        return 0.0

    return precision_sum / num_relevant


# ---------------------------------------------------------------------------
# Precision@k
# ---------------------------------------------------------------------------


def precision_at_k(
    relevance_scores: list[float],
    k: int,
    threshold: float = 1.0,
) -> float:
    """Compute Precision at rank *k*.

    Args:
        relevance_scores: Relevance values in predicted rank order.
        k: Cut-off position.
        threshold: Minimum relevance value to consider an item relevant.

    Returns:
        Precision in ``[0.0, 1.0]``.  Returns ``0.0`` when the list is
        empty or *k* ≤ 0.
    """
    if not relevance_scores or k <= 0:
        return 0.0

    k = min(k, len(relevance_scores))
    relevant_count = sum(
        1 for rel in relevance_scores[:k] if rel >= threshold
    )
    return relevant_count / k


# ---------------------------------------------------------------------------
# Mean Reciprocal Rank (MRR)
# ---------------------------------------------------------------------------


def mrr(relevance_scores: list[float], threshold: float = 1.0) -> float:
    """Compute Mean Reciprocal Rank.

    For a single ranked list this equals ``1 / rank_of_first_relevant``.

    Args:
        relevance_scores: Relevance values in predicted rank order.
        threshold: Minimum relevance value to consider an item relevant.

    Returns:
        MRR in ``(0.0, 1.0]``.  Returns ``0.0`` when no relevant item
        is found or the list is empty.
    """
    if not relevance_scores:
        return 0.0

    for i, rel in enumerate(relevance_scores, start=1):
        if rel >= threshold:
            return 1.0 / i

    return 0.0
