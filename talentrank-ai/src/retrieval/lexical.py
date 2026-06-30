"""
Lexical (BM25) retrieval for TalentRank AI.

Provides term-frequency-based retrieval that complements dense vector
search.  BM25 is particularly effective at surfacing candidates who
mention exact skill names, tools, or frameworks that the JD calls out
but whose semantic embedding distance may not fully capture.

The tokeniser is intentionally simple (lowercase + split on non-alpha)
to keep offline indexing fast and avoid heavy NLP dependencies.
"""

from __future__ import annotations

import pickle
import re
from pathlib import Path
from typing import Any, Optional

import numpy as np
from rank_bm25 import BM25Okapi

from src.config.settings import get_settings
from src.utils.logging import get_logger
from src.utils.text import build_candidate_text

logger = get_logger("retrieval.lexical")


# ── tokenisation ─────────────────────────────────────────────────────

_SPLIT_RE = re.compile(r"[^a-z0-9+#]+")


def _tokenize(text: str) -> list[str]:
    """
    Simple whitespace + lowercase tokeniser.

    Keeps ``+`` and ``#`` so that tokens like ``c++`` and ``c#`` survive.
    Drops tokens shorter than 2 characters.
    """
    tokens = _SPLIT_RE.split(text.lower())
    return [t for t in tokens if len(t) >= 2]


# ── retriever ────────────────────────────────────────────────────────


class LexicalRetriever:
    """
    BM25-backed lexical retriever.

    Typical usage::

        lr = LexicalRetriever()
        lr.build_index(candidates, candidate_ids)
        results = lr.query("machine learning engineer Python", top_k=500)
    """

    def __init__(self) -> None:
        """Initialise the retriever (the index is built lazily)."""
        settings = get_settings()
        self._default_top_k = settings.retrieval.bm25_top_k
        self._bm25: Optional[BM25Okapi] = None
        self._candidate_ids: list[str] = []

    # ── index construction ───────────────────────────────────────────

    def build_index(
        self,
        candidates: list[dict[str, Any]],
        candidate_ids: list[str],
    ) -> None:
        """
        Build the BM25 index from candidate dicts.

        Args:
            candidates: Raw candidate dicts (as loaded from JSONL).
            candidate_ids: Ordered candidate identifiers matching the
                candidate list.

        Raises:
            ValueError: If candidates and candidate_ids lengths differ.
        """
        if len(candidates) != len(candidate_ids):
            raise ValueError(
                f"candidates ({len(candidates)}) ≠ "
                f"candidate_ids ({len(candidate_ids)})"
            )

        logger.info("Building BM25 index for %d candidates…", len(candidates))

        tokenized_corpus: list[list[str]] = []
        for cand in candidates:
            text = build_candidate_text(cand)
            tokenized_corpus.append(_tokenize(text))

        self._bm25 = BM25Okapi(tokenized_corpus)
        self._candidate_ids = list(candidate_ids)

        logger.info(
            "BM25 index built  n=%d  avg_doc_len=%.1f",
            len(candidate_ids),
            float(np.mean([len(d) for d in tokenized_corpus])),
        )

    # ── querying ─────────────────────────────────────────────────────

    def query(
        self,
        query_text: str,
        top_k: Optional[int] = None,
    ) -> list[tuple[str, float]]:
        """
        Retrieve the *top_k* candidates most relevant to *query_text*.

        Args:
            query_text: Free-text query (will be tokenised internally).
            top_k: Number of results (defaults to ``RetrievalConfig.bm25_top_k``).

        Returns:
            Sorted list of ``(candidate_id, bm25_score)`` tuples,
            highest score first.

        Raises:
            RuntimeError: If the index has not been built or loaded.
        """
        if self._bm25 is None:
            raise RuntimeError(
                "BM25 index not available — call build_index() or load() first"
            )

        top_k = top_k or self._default_top_k
        query_tokens = _tokenize(query_text)

        scores: np.ndarray = self._bm25.get_scores(query_tokens)

        # Partial argsort for top-k (faster than full sort for large n)
        if top_k < len(scores):
            top_indices = np.argpartition(scores, -top_k)[-top_k:]
            top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]
        else:
            top_indices = np.argsort(scores)[::-1][:top_k]

        results: list[tuple[str, float]] = [
            (self._candidate_ids[i], float(scores[i]))
            for i in top_indices
            if scores[i] > 0.0
        ]

        logger.debug(
            "BM25 query returned %d results  (top_k=%d, best=%.4f)",
            len(results),
            top_k,
            results[0][1] if results else 0.0,
        )
        return results

    # ── persistence ──────────────────────────────────────────────────

    def save(self, path: Path) -> None:
        """
        Serialise the BM25 index and candidate IDs to disk.

        Args:
            path: Destination pickle file.

        Raises:
            RuntimeError: If the index has not been built.
        """
        if self._bm25 is None:
            raise RuntimeError("BM25 index not built — call build_index() first")

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "bm25": self._bm25,
            "candidate_ids": self._candidate_ids,
        }
        with open(path, "wb") as fh:
            pickle.dump(payload, fh, protocol=pickle.HIGHEST_PROTOCOL)

        logger.info("BM25 index saved  → %s", path)

    def load(self, path: Path) -> None:
        """
        Load a previously serialised BM25 index.

        Args:
            path: Path to the pickle file.

        Raises:
            FileNotFoundError: If the path does not exist.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"BM25 index file not found: {path}")

        with open(path, "rb") as fh:
            payload = pickle.load(fh)  # noqa: S301

        self._bm25 = payload["bm25"]
        self._candidate_ids = payload["candidate_ids"]

        logger.info(
            "BM25 index loaded  n=%d  from %s",
            len(self._candidate_ids),
            path,
        )
