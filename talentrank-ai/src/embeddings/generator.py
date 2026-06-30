"""
Embedding generator for TalentRank AI.

Handles offline batch embedding of candidate text and JD query text
using sentence-transformers.  Supports checkpointing so that interrupted
runs can be resumed without re-computing finished batches.

This module is used during OFFLINE pre-computation only – the generated
.npy artefacts are loaded at retrieval time for fast candidate ranking.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Optional

import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from src.config.settings import get_settings
from src.utils.logging import get_logger
from src.utils.text import build_candidate_text, build_jd_query_text

logger = get_logger("embeddings.generator")


class EmbeddingGenerator:
    """
    Generate and persist dense embeddings for candidates and job descriptions.

    Typical usage::

        gen = EmbeddingGenerator()
        matrix = gen.generate_candidate_embeddings(candidates, output_path)
        jd_vec = gen.generate_jd_embedding(jd_output_path)
    """

    def __init__(self, model_name: Optional[str] = None) -> None:
        """
        Initialise the generator.

        Args:
            model_name: HuggingFace model identifier.  Falls back to
                ``EmbeddingConfig.model_name`` when *None*.
        """
        settings = get_settings()
        self._cfg = settings.embedding

        self._model_name = model_name or self._cfg.model_name
        self._batch_size = self._cfg.batch_size
        self._normalize = self._cfg.normalize
        self._device = self._cfg.device

        logger.info(
            "Loading sentence-transformer model '%s' on device '%s'",
            self._model_name,
            self._device,
        )
        self._model = SentenceTransformer(self._model_name, device=self._device)
        self._model.max_seq_length = self._cfg.max_seq_length
        logger.info(
            "Model loaded  (dim=%d, max_seq=%d)",
            self._cfg.embedding_dim,
            self._cfg.max_seq_length,
        )

    # ── public API ────────────────────────────────────────────────────

    def generate_candidate_embeddings(
        self,
        candidates: list[dict[str, Any]],
        output_path: Path,
        checkpoint_every: int = 50,
    ) -> np.ndarray:
        """
        Embed all candidates and save the matrix as a ``.npy`` file.

        Args:
            candidates: Raw candidate dicts (as loaded from JSONL).
            output_path: Destination for the ``(n, dim)`` numpy matrix.
            checkpoint_every: Persist intermediate results every *N* batches.

        Returns:
            The full embedding matrix ``(n_candidates × embedding_dim)``.
        """
        n = len(candidates)
        dim = self._cfg.embedding_dim
        logger.info(
            "Generating embeddings for %d candidates (batch_size=%d)",
            n,
            self._batch_size,
        )

        # Build text representations ─────────────────────────────────
        logger.info("Constructing candidate text representations…")
        texts: list[str] = [
            build_candidate_text(c) for c in tqdm(candidates, desc="Building text")
        ]

        # Checkpoint setup ────────────────────────────────────────────
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path = output_path.with_suffix(".checkpoint.npy")

        embeddings = np.zeros((n, dim), dtype=np.float32)
        start_batch = 0

        # Resume from checkpoint if available
        if checkpoint_path.exists():
            checkpoint_data = np.load(checkpoint_path)
            completed_rows = checkpoint_data.shape[0]
            if completed_rows < n:
                embeddings[:completed_rows] = checkpoint_data
                start_batch = completed_rows // self._batch_size
                logger.info(
                    "Resumed from checkpoint — %d/%d candidates already embedded",
                    completed_rows,
                    n,
                )
            else:
                logger.info("Checkpoint contains all rows — skipping encoding")
                embeddings = checkpoint_data[:n]
                np.save(output_path, embeddings)
                _remove_checkpoint(checkpoint_path)
                return embeddings

        # Batch encode ────────────────────────────────────────────────
        total_batches = math.ceil(n / self._batch_size)
        for batch_idx in tqdm(
            range(start_batch, total_batches),
            initial=start_batch,
            total=total_batches,
            desc="Encoding batches",
        ):
            lo = batch_idx * self._batch_size
            hi = min(lo + self._batch_size, n)
            batch_texts = texts[lo:hi]

            batch_embeddings = self._model.encode(
                batch_texts,
                batch_size=self._batch_size,
                show_progress_bar=False,
                normalize_embeddings=self._normalize,
                convert_to_numpy=True,
            )
            embeddings[lo:hi] = batch_embeddings

            # Periodic checkpoint
            if (batch_idx + 1) % checkpoint_every == 0:
                np.save(checkpoint_path, embeddings[: hi])
                logger.info(
                    "Checkpoint saved at batch %d/%d  (%d candidates)",
                    batch_idx + 1,
                    total_batches,
                    hi,
                )

        # Final save ──────────────────────────────────────────────────
        np.save(output_path, embeddings)
        _remove_checkpoint(checkpoint_path)
        logger.info("Saved embedding matrix  shape=%s  → %s", embeddings.shape, output_path)
        return embeddings

    def generate_jd_embedding(self, output_path: Path) -> np.ndarray:
        """
        Embed the job description query text and save as ``.npy``.

        Args:
            output_path: Destination path (will contain a ``(1, dim)`` array).

        Returns:
            The JD embedding vector ``(1, dim)``.
        """
        jd_text = build_jd_query_text()
        logger.info("Generating JD embedding  (len=%d chars)", len(jd_text))

        jd_embedding: np.ndarray = self._model.encode(
            [jd_text],
            normalize_embeddings=self._normalize,
            convert_to_numpy=True,
        )
        # Ensure shape is (1, dim)
        if jd_embedding.ndim == 1:
            jd_embedding = jd_embedding.reshape(1, -1)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(output_path, jd_embedding)
        logger.info("Saved JD embedding  shape=%s  → %s", jd_embedding.shape, output_path)
        return jd_embedding

    @staticmethod
    def load_embeddings(path: Path) -> np.ndarray:
        """
        Load a pre-computed embedding matrix from a ``.npy`` file.

        Args:
            path: Path to the ``.npy`` file.

        Returns:
            The loaded numpy array.

        Raises:
            FileNotFoundError: If the path does not exist.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Embedding file not found: {path}")

        matrix = np.load(path)
        logger.info("Loaded embeddings  shape=%s  from %s", matrix.shape, path)
        return matrix


# ── helpers ──────────────────────────────────────────────────────────


def _remove_checkpoint(checkpoint_path: Path) -> None:
    """Silently remove a checkpoint file if it exists."""
    try:
        if checkpoint_path.exists():
            checkpoint_path.unlink()
            logger.info("Removed checkpoint file: %s", checkpoint_path)
    except OSError as exc:
        logger.warning("Could not remove checkpoint file %s: %s", checkpoint_path, exc)
