"""
Dense (vector) retrieval for TalentRank AI.

Wraps a FAISS ``IndexFlatIP`` index over pre-computed sentence-transformer
embeddings.  Since embeddings are L2-normalised at generation time, inner
product equals cosine similarity — no additional normalisation needed at
query time.

Design rationale:
    • IndexFlatIP is brute-force but exact.  For 100k × 384 on CPU the
      query latency is < 50 ms, well within the 5-minute window.
    • The index is serialised with ``faiss.write_index`` so it can be
      pre-built offline and loaded instantly during the ranking run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import faiss
import numpy as np

from src.config.settings import get_settings
from src.utils.logging import get_logger

logger = get_logger("retrieval.dense")


class DenseRetriever:
    """
    FAISS-backed dense retriever.

    Typical usage::

        dr = DenseRetriever(embedding_matrix, candidate_ids)
        dr.build_index()
        results = dr.query(jd_embedding, top_k=500)
    """

    def __init__(
        self,
        embedding_matrix: np.ndarray,
        candidate_ids: list[str],
    ) -> None:
        """
        Initialise the dense retriever.

        Args:
            embedding_matrix: Pre-computed embeddings of shape ``(n, dim)``.
                Must be **row-normalised** (unit L2 norm) for cosine similarity.
            candidate_ids: Ordered list of candidate identifiers matching
                the rows of *embedding_matrix*.

        Raises:
            ValueError: If the matrix rows and candidate_ids length differ.
        """
        if embedding_matrix.shape[0] != len(candidate_ids):
            raise ValueError(
                f"Matrix rows ({embedding_matrix.shape[0]}) ≠ "
                f"candidate_ids length ({len(candidate_ids)})"
            )

        self._embeddings = np.ascontiguousarray(
            embedding_matrix.astype(np.float32)
        )
        self._candidate_ids = candidate_ids
        self._dim = embedding_matrix.shape[1]
        self._index: Optional[faiss.IndexFlatIP] = None

        settings = get_settings()
        self._default_top_k = settings.retrieval.dense_top_k
        logger.info(
            "DenseRetriever created  n=%d  dim=%d",
            len(candidate_ids),
            self._dim,
        )

    # ── index management ─────────────────────────────────────────────

    def build_index(self) -> None:
        """
        Build the FAISS inner-product index from the embedding matrix.

        After this call, :meth:`query` is ready to use.
        """
        self._index = faiss.IndexFlatIP(self._dim)
        self._index.add(self._embeddings)  # type: ignore[arg-type]
        logger.info(
            "FAISS IndexFlatIP built  ntotal=%d  dim=%d",
            self._index.ntotal,
            self._dim,
        )

    def save_index(self, path: Path) -> None:
        """
        Serialise the FAISS index to disk.

        Args:
            path: Destination file path.

        Raises:
            RuntimeError: If the index has not been built yet.
        """
        if self._index is None:
            raise RuntimeError("Index not built — call build_index() first")

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(path))
        logger.info("FAISS index saved  → %s", path)

    def load_index(self, path: Path) -> None:
        """
        Load a previously serialised FAISS index.

        Args:
            path: Path to the ``.faiss`` file.

        Raises:
            FileNotFoundError: If the path does not exist.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"FAISS index not found: {path}")

        self._index = faiss.read_index(str(path))
        logger.info(
            "FAISS index loaded  ntotal=%d  from %s",
            self._index.ntotal,
            path,
        )

    # ── querying ─────────────────────────────────────────────────────

    def query(
        self,
        query_embedding: np.ndarray,
        top_k: Optional[int] = None,
    ) -> list[tuple[str, float]]:
        """
        Retrieve the *top_k* most similar candidates.

        Args:
            query_embedding: Query vector of shape ``(dim,)`` or ``(1, dim)``.
            top_k: Number of results (defaults to ``RetrievalConfig.dense_top_k``).

        Returns:
            Sorted list of ``(candidate_id, similarity_score)`` tuples,
            highest score first.

        Raises:
            RuntimeError: If the index has not been built or loaded.
        """
        if self._index is None:
            raise RuntimeError(
                "Index not available — call build_index() or load_index() first"
            )

        top_k = top_k or self._default_top_k

        # Ensure correct shape for FAISS
        qvec = np.ascontiguousarray(
            query_embedding.astype(np.float32).reshape(1, -1)
        )

        scores, indices = self._index.search(qvec, top_k)  # type: ignore[union-attr]
        scores = scores[0]
        indices = indices[0]

        results: list[tuple[str, float]] = []
        for idx, score in zip(indices, scores):
            if idx == -1:
                # FAISS returns -1 when fewer than top_k vectors exist
                break
            results.append((self._candidate_ids[idx], float(score)))

        logger.debug(
            "Dense query returned %d results  (top_k=%d, best=%.4f)",
            len(results),
            top_k,
            results[0][1] if results else 0.0,
        )
        return results
