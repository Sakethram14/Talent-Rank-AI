"""
Hybrid retrieval for TalentRank AI.

Fuses results from :class:`DenseRetriever` (cosine / inner-product) and
:class:`LexicalRetriever` (BM25) into a single ranked list.

Two fusion strategies are provided:

1. **Reciprocal Rank Fusion (RRF)** — rank-based, parameter-free (apart
   from the constant *k*).  Robust to wildly different score scales
   between dense and lexical retrievers.

2. **Weighted linear combination** — score-based, using the
   ``dense_weight`` / ``bm25_weight`` from :class:`RetrievalConfig`.
   Scores are min–max normalised within each result set before
   combining to account for different value ranges.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

import numpy as np

from src.config.settings import get_settings
from src.retrieval.dense import DenseRetriever
from src.retrieval.lexical import LexicalRetriever
from src.utils.logging import get_logger

logger = get_logger("retrieval.hybrid")


class HybridRetriever:
    """
    Hybrid retriever combining dense and lexical signals.

    Typical usage::

        hr = HybridRetriever(dense_retriever, lexical_retriever)
        results = hr.query(jd_embedding, jd_text, top_k=300)
    """

    def __init__(
        self,
        dense_retriever: DenseRetriever,
        lexical_retriever: LexicalRetriever,
    ) -> None:
        """
        Initialise the hybrid retriever.

        Args:
            dense_retriever: An initialised :class:`DenseRetriever` with a
                built or loaded FAISS index.
            lexical_retriever: An initialised :class:`LexicalRetriever` with
                a built or loaded BM25 index.
        """
        settings = get_settings()
        self._cfg = settings.retrieval

        self._dense = dense_retriever
        self._lexical = lexical_retriever

        logger.info(
            "HybridRetriever created  dense_w=%.2f  bm25_w=%.2f  hybrid_top_k=%d",
            self._cfg.dense_weight,
            self._cfg.bm25_weight,
            self._cfg.hybrid_top_k,
        )

    # ── public API ────────────────────────────────────────────────────

    def query(
        self,
        query_embedding: np.ndarray,
        query_text: str,
        top_k: Optional[int] = None,
        *,
        method: str = "rrf",
    ) -> list[tuple[str, float]]:
        """
        Retrieve candidates by fusing dense and lexical results.

        Args:
            query_embedding: Dense query vector (shape ``(dim,)`` or ``(1, dim)``).
            query_text: Free-text query for BM25.
            top_k: Number of final results.  Defaults to
                ``RetrievalConfig.hybrid_top_k``.
            method: Fusion strategy — ``"rrf"`` (default) or ``"weighted"``.

        Returns:
            Sorted list of ``(candidate_id, fused_score)`` tuples,
            highest score first.
        """
        top_k = top_k or self._cfg.hybrid_top_k

        dense_results = self._dense.query(
            query_embedding, top_k=self._cfg.dense_top_k
        )
        lexical_results = self._lexical.query(
            query_text, top_k=self._cfg.bm25_top_k
        )

        logger.info(
            "Fusing results  dense=%d  lexical=%d  method=%s",
            len(dense_results),
            len(lexical_results),
            method,
        )

        if method == "rrf":
            fused = _reciprocal_rank_fusion(
                [dense_results, lexical_results], k=60
            )
        elif method == "weighted":
            fused = _weighted_linear_combination(
                dense_results,
                lexical_results,
                dense_weight=self._cfg.dense_weight,
                bm25_weight=self._cfg.bm25_weight,
            )
        else:
            raise ValueError(f"Unknown fusion method: {method!r}")

        # Sort descending and trim to top_k
        fused.sort(key=lambda x: x[1], reverse=True)
        results = fused[:top_k]

        logger.info(
            "Hybrid query returned %d results  (best=%.4f)",
            len(results),
            results[0][1] if results else 0.0,
        )
        return results


# ── fusion strategies ────────────────────────────────────────────────


def _reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[str, float]]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """
    Fuse multiple ranked lists via Reciprocal Rank Fusion.

    For each candidate appearing in *any* list the RRF score is::

        rrf_score = Σ  1 / (k + rank)

    where ``rank`` is 1-based within each list.

    Args:
        ranked_lists: One or more ``(candidate_id, score)`` lists,
            each **pre-sorted** by score descending.
        k: Smoothing constant (default 60, per the original RRF paper).

    Returns:
        Unsorted list of ``(candidate_id, rrf_score)`` tuples.
    """
    rrf_scores: dict[str, float] = defaultdict(float)

    for result_list in ranked_lists:
        for rank, (cid, _score) in enumerate(result_list, start=1):
            rrf_scores[cid] += 1.0 / (k + rank)

    return [(cid, score) for cid, score in rrf_scores.items()]


def _weighted_linear_combination(
    dense_results: list[tuple[str, float]],
    lexical_results: list[tuple[str, float]],
    dense_weight: float,
    bm25_weight: float,
) -> list[tuple[str, float]]:
    """
    Fuse results with min-max normalised weighted linear combination.

    Scores from each retriever are independently rescaled to [0, 1]
    before weighting to prevent one score range from dominating.

    Args:
        dense_results: Sorted dense retriever output.
        lexical_results: Sorted BM25 retriever output.
        dense_weight: Weight for dense scores.
        bm25_weight: Weight for BM25 scores.

    Returns:
        Unsorted list of ``(candidate_id, combined_score)`` tuples.
    """
    dense_normed = _min_max_normalise(dense_results)
    lexical_normed = _min_max_normalise(lexical_results)

    combined: dict[str, float] = defaultdict(float)

    for cid, score in dense_normed:
        combined[cid] += dense_weight * score

    for cid, score in lexical_normed:
        combined[cid] += bm25_weight * score

    return [(cid, score) for cid, score in combined.items()]


def _min_max_normalise(
    results: list[tuple[str, float]],
) -> list[tuple[str, float]]:
    """
    Rescale scores to [0, 1] using min-max normalisation.

    If all scores are identical the function returns 1.0 for every entry.
    """
    if not results:
        return []

    scores = [s for _, s in results]
    lo = min(scores)
    hi = max(scores)
    span = hi - lo

    if span == 0.0:
        return [(cid, 1.0) for cid, _ in results]

    return [(cid, (s - lo) / span) for cid, s in results]
