"""
Feature store for TalentRank AI.

Manages computed features as a pandas DataFrame and persists them in
Parquet format for fast serialization.  Designed for 100k candidates ×
~60 features.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from src.config.settings import get_settings
from src.utils.logging import get_logger

logger = get_logger("features.store")


class FeatureStore:
    """
    In-memory feature store backed by Parquet files.

    Features are stored as a pandas DataFrame where each row is a
    candidate (indexed by candidate_id) and each column is a feature.

    Typical usage::

        store = FeatureStore()
        store.add_features("CAND_0000001", {"ai_keyword_count": 12, ...})
        store.save()                       # writes to default Parquet path
        loaded = FeatureStore.load()       # reads back
    """

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}
        self._metadata: dict[str, Any] = {
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0",
            "feature_names": [],
            "feature_types": {},
            "feature_descriptions": {},
        }
        self._df_cache: Optional[pd.DataFrame] = None
        self._dirty: bool = False

    # ── public API ────────────────────────────────────────────────────────

    def add_features(self, candidate_id: str, features: dict[str, Any]) -> None:
        """
        Add or update features for a single candidate.

        Args:
            candidate_id: Unique candidate identifier (e.g. ``CAND_0000001``).
            features: Dictionary mapping feature names to their values.
        """
        if candidate_id in self._records:
            self._records[candidate_id].update(features)
        else:
            self._records[candidate_id] = dict(features)
        self._dirty = True
        self._df_cache = None  # Invalidate cache

    def get_features(self, candidate_id: str) -> Optional[dict[str, Any]]:
        """
        Retrieve features for a single candidate.

        Args:
            candidate_id: Unique candidate identifier.

        Returns:
            Feature dict or ``None`` if the candidate is not in the store.
        """
        return self._records.get(candidate_id)

    def get_all(self) -> pd.DataFrame:
        """
        Return all features as a pandas DataFrame.

        The DataFrame is cached until new features are added.
        """
        if self._df_cache is None or self._dirty:
            if not self._records:
                self._df_cache = pd.DataFrame()
            else:
                self._df_cache = pd.DataFrame.from_dict(
                    self._records, orient="index"
                )
                self._df_cache.index.name = "candidate_id"
            self._dirty = False
        return self._df_cache

    @property
    def candidate_count(self) -> int:
        """Number of candidates in the store."""
        return len(self._records)

    @property
    def feature_count(self) -> int:
        """Number of feature columns across all candidates."""
        if not self._records:
            return 0
        # Use the first record to determine column count
        return len(next(iter(self._records.values())))

    @property
    def metadata(self) -> dict[str, Any]:
        """Return current metadata."""
        self._metadata["feature_names"] = self._get_feature_names()
        self._metadata["candidate_count"] = self.candidate_count
        return dict(self._metadata)

    def set_feature_descriptions(
        self, descriptions: dict[str, str]
    ) -> None:
        """Set human-readable descriptions for feature columns."""
        self._metadata["feature_descriptions"].update(descriptions)

    # ── persistence ───────────────────────────────────────────────────────

    def save(self, path: Optional[Path] = None, version: Optional[str] = None) -> Path:
        """
        Save the feature store to a Parquet file.

        Args:
            path: Target file path.  Defaults to the path from settings.
            version: Optional version suffix (e.g. ``'v2'``).  The file will
                     be saved as ``feature_store_v2.parquet``.

        Returns:
            The path the file was saved to.
        """
        if path is None:
            settings = get_settings()
            path = settings.paths.feature_store_path

        if version:
            path = path.parent / f"{path.stem}_{version}{path.suffix}"

        path.parent.mkdir(parents=True, exist_ok=True)

        df = self.get_all()
        if df.empty:
            logger.warning("Saving empty feature store to %s", path)

        # Update metadata before save
        self._metadata["saved_at"] = datetime.utcnow().isoformat()
        self._metadata["feature_names"] = self._get_feature_names()
        self._metadata["candidate_count"] = self.candidate_count

        # Store metadata as Parquet file-level metadata
        import json

        meta_bytes = json.dumps(self._metadata).encode("utf-8")
        import pyarrow as pa
        import pyarrow.parquet as pq

        table = pa.Table.from_pandas(df)
        existing_meta = table.schema.metadata or {}
        existing_meta[b"talentrank_metadata"] = meta_bytes
        table = table.replace_schema_metadata(existing_meta)
        pq.write_table(table, str(path), compression="snappy")

        logger.info(
            "Feature store saved: %d candidates × %d features → %s",
            self.candidate_count,
            self.feature_count,
            path,
        )
        return path

    @classmethod
    def load(cls, path: Optional[Path] = None) -> FeatureStore:
        """
        Load a feature store from a Parquet file.

        Args:
            path: Source file path.  Defaults to the path from settings.

        Returns:
            A populated FeatureStore instance.
        """
        if path is None:
            settings = get_settings()
            path = settings.paths.feature_store_path

        if not path.exists():
            raise FileNotFoundError(f"Feature store not found: {path}")

        import json
        import pyarrow.parquet as pq

        table = pq.read_table(str(path))
        df = table.to_pandas()

        store = cls()

        # Restore metadata
        raw_meta = table.schema.metadata or {}
        if b"talentrank_metadata" in raw_meta:
            store._metadata = json.loads(raw_meta[b"talentrank_metadata"])

        # Restore records
        if not df.empty:
            df.index.name = "candidate_id"
            store._records = df.to_dict(orient="index")
            store._df_cache = df
            store._dirty = False

        logger.info(
            "Feature store loaded: %d candidates * %d features <- %s",
            store.candidate_count,
            store.feature_count,
            path,
        )
        return store

    # -- private helpers ---------------------------------------------------

    def _get_feature_names(self) -> list[str]:
        """Get the ordered list of feature names from the first record."""
        if not self._records:
            return []
        return list(next(iter(self._records.values())).keys())
