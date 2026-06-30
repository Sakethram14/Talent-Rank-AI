"""
Feature engineering pipeline for TalentRank AI.

Orchestrates all feature extractors and the behavioral analyzer to
produce a complete FeatureStore from raw CandidateRecords.  Designed
for 100k records within a 5-minute compute budget.
"""

from __future__ import annotations

import time
from typing import Optional

from src.behavior.analyzer import BehavioralAnalyzer
from src.config.settings import get_settings
from src.data.models import CandidateRecord
from src.features.extractors import (
    BehavioralFeatureExtractor,
    CareerFeatureExtractor,
    EducationFeatureExtractor,
    FeatureExtractor,
    HoneypotFeatureExtractor,
    RiskFeatureExtractor,
    SemanticFeatureExtractor,
)
from src.features.store import FeatureStore
from src.utils.logging import get_logger

logger = get_logger("features.pipeline")


class FeaturePipeline:
    """
    End-to-end feature engineering pipeline.

    Runs all extractors on every candidate, augments with behavioral
    multiplier / engagement score, and stores results.

    Typical usage::

        pipeline = FeaturePipeline()
        store = pipeline.run(candidates)
        store.save()
    """

    PROGRESS_INTERVAL: int = 10_000  # Log every N records

    def __init__(self) -> None:
        self._settings = get_settings()

        # Instantiate all extractors
        self._extractors: list[FeatureExtractor] = [
            SemanticFeatureExtractor(),
            CareerFeatureExtractor(),
            BehavioralFeatureExtractor(),
            EducationFeatureExtractor(),
            RiskFeatureExtractor(),
            HoneypotFeatureExtractor(),
        ]

        # Behavioral analyzer (produces multiplier + engagement)
        self._behavior_analyzer = BehavioralAnalyzer()

    @property
    def all_feature_names(self) -> list[str]:
        """Return the combined ordered list of all feature names."""
        names: list[str] = []
        for ext in self._extractors:
            names.extend(ext.feature_names)
        # Plus behavioral analyzer features
        names.extend([
            "behavioral_multiplier",
            "response_factor",
            "activity_factor",
            "availability_factor",
            "engagement_score",
        ])
        return names

    def run(
        self,
        candidates: list[CandidateRecord],
        store: Optional[FeatureStore] = None,
    ) -> FeatureStore:
        """
        Process all candidates and produce a populated FeatureStore.

        Args:
            candidates: List of parsed CandidateRecords.
            store: Optional pre-existing store to append to.  A new store
                   is created if not provided.

        Returns:
            FeatureStore containing all computed features.
        """
        if store is None:
            store = FeatureStore()

        total = len(candidates)
        logger.info("Starting feature pipeline for %d candidates", total)
        start_time = time.perf_counter()

        errors = 0
        for idx, record in enumerate(candidates):
            try:
                features = self._extract_all(record)
                store.add_features(record.candidate_id, features)
            except Exception:
                errors += 1
                logger.exception(
                    "Error extracting features for %s", record.candidate_id
                )

            # Progress logging
            processed = idx + 1
            if processed % self.PROGRESS_INTERVAL == 0 or processed == total:
                elapsed = time.perf_counter() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                logger.info(
                    "Progress: %d/%d (%.1f%%) | %.0f candidates/sec | errors: %d",
                    processed,
                    total,
                    100.0 * processed / total,
                    rate,
                    errors,
                )

        elapsed = time.perf_counter() - start_time
        logger.info(
            "Feature pipeline complete: %d candidates, %d features, "
            "%.2fs elapsed, %d errors",
            store.candidate_count,
            store.feature_count,
            elapsed,
            errors,
        )

        return store

    def _extract_all(self, record: CandidateRecord) -> dict:
        """Run all extractors + behavioral analysis on a single record."""
        features: dict = {}

        # Run each extractor
        for extractor in self._extractors:
            features.update(extractor.extract(record))

        # Run behavioral analyzer
        result = self._behavior_analyzer.analyze(record)
        features["behavioral_multiplier"] = result.behavioral_multiplier
        features["response_factor"] = result.response_factor
        features["activity_factor"] = result.activity_factor
        features["availability_factor"] = result.availability_factor
        features["engagement_score"] = result.engagement_score

        return features
