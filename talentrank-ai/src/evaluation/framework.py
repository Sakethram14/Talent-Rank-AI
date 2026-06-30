"""
Evaluation framework for the TalentRank AI pipeline.

Provides tooling to measure runtime performance, memory usage,
honeypot rejection quality, score consistency, and feature-store
health.  All results are serialisable to a JSON report.
"""

from __future__ import annotations

import json
import time
import tracemalloc
from pathlib import Path
from typing import Any, Callable, Optional

from src.config.settings import get_settings
from src.utils.logging import get_logger

logger = get_logger("evaluation.framework")


class EvaluationFramework:
    """One-stop evaluation harness for TalentRank AI.

    Usage::

        framework = EvaluationFramework()
        perf = framework.evaluate_runtime(my_pipeline_fn, arg1, arg2)
        hp   = framework.evaluate_honeypot_rate(ranked_ids, honeypot_set)
        framework.generate_report(
            {"performance": perf, "honeypots": hp},
            output_path=Path("artifacts/eval_report.json"),
        )
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    # ------------------------------------------------------------------
    # Runtime & memory
    # ------------------------------------------------------------------

    def evaluate_runtime(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute *func* and measure wall-clock time and peak memory.

        Args:
            func: Callable to profile.
            *args: Positional arguments forwarded to *func*.
            **kwargs: Keyword arguments forwarded to *func*.

        Returns:
            Dict with ``elapsed_seconds``, ``peak_memory_mb``, and
            ``result`` (the return value of *func*).
        """
        tracemalloc.start()
        start = time.perf_counter()

        try:
            result = func(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            _, peak_bytes = tracemalloc.get_traced_memory()
            tracemalloc.stop()

        peak_mb = peak_bytes / (1024 * 1024)

        logger.info(
            "Runtime evaluation: %.3f s, peak memory %.2f MB",
            elapsed,
            peak_mb,
        )

        return {
            "elapsed_seconds": round(elapsed, 4),
            "peak_memory_mb": round(peak_mb, 2),
            "result": result,
        }

    # ------------------------------------------------------------------
    # Honeypot analysis
    # ------------------------------------------------------------------

    def evaluate_honeypot_rate(
        self,
        ranked_ids: list[str],
        honeypot_ids: set[str],
        top_k: Optional[int] = None,
    ) -> dict[str, Any]:
        """Measure how many honeypots leaked into the top-*k* ranking.

        Args:
            ranked_ids: Candidate IDs in rank order.
            honeypot_ids: Set of known honeypot candidate IDs.
            top_k: Evaluation cut-off.  Defaults to
                ``settings.ranking.top_k_output`` (100).

        Returns:
            Dict with ``top_k``, ``honeypot_count``, ``honeypot_rate``,
            ``honeypot_positions`` (1-indexed), and ``passed``
            (whether the rate is within the allowed threshold).
        """
        if top_k is None:
            top_k = self._settings.ranking.top_k_output

        top_k = min(top_k, len(ranked_ids))
        top_slice = ranked_ids[:top_k]

        positions: list[int] = []
        for i, cid in enumerate(top_slice, start=1):
            if cid in honeypot_ids:
                positions.append(i)

        count = len(positions)
        rate = count / top_k if top_k > 0 else 0.0
        max_rate = self._settings.honeypot.max_honeypot_rate

        logger.info(
            "Honeypot rate in top %d: %d / %d = %.2f%% (max allowed: %.2f%%)",
            top_k,
            count,
            top_k,
            rate * 100,
            max_rate * 100,
        )

        return {
            "top_k": top_k,
            "honeypot_count": count,
            "honeypot_rate": round(rate, 4),
            "honeypot_positions": positions,
            "passed": rate <= max_rate,
        }

    # ------------------------------------------------------------------
    # Score consistency
    # ------------------------------------------------------------------

    def evaluate_score_consistency(
        self, scores: list[float]
    ) -> dict[str, Any]:
        """Check whether scores are monotonically non-increasing.

        Args:
            scores: Final ranking scores in rank order (index 0 = best).

        Returns:
            Dict with ``is_monotonic``, ``violations_count``, and
            ``violation_positions`` (1-indexed pairs).
        """
        if len(scores) <= 1:
            return {
                "is_monotonic": True,
                "violations_count": 0,
                "violation_positions": [],
            }

        violations: list[tuple[int, int]] = []
        for i in range(len(scores) - 1):
            if scores[i] < scores[i + 1]:
                violations.append((i + 1, i + 2))  # 1-indexed

        is_mono = len(violations) == 0
        logger.info(
            "Score consistency: monotonic=%s, violations=%d",
            is_mono,
            len(violations),
        )

        return {
            "is_monotonic": is_mono,
            "violations_count": len(violations),
            "violation_positions": violations,
        }

    # ------------------------------------------------------------------
    # Feature statistics
    # ------------------------------------------------------------------

    def evaluate_feature_stats(
        self,
        feature_store_df: Any,  # pd.DataFrame at runtime
    ) -> dict[str, dict[str, float]]:
        """Compute per-feature descriptive statistics.

        Args:
            feature_store_df: A pandas ``DataFrame`` where each column
                (except ``candidate_id``) is a numeric feature.

        Returns:
            Nested dict: ``{feature_name: {mean, std, min, max, missing_rate}}``.
        """
        import pandas as pd  # local import to keep module lightweight

        if not isinstance(feature_store_df, pd.DataFrame):
            raise TypeError(
                f"Expected pandas DataFrame, got {type(feature_store_df).__name__}"
            )

        stats: dict[str, dict[str, float]] = {}
        numeric_cols = feature_store_df.select_dtypes(include="number").columns

        for col in numeric_cols:
            series = feature_store_df[col]
            total = len(series)
            missing = int(series.isna().sum())
            stats[col] = {
                "mean": round(float(series.mean()), 4) if total > missing else 0.0,
                "std": round(float(series.std()), 4) if total > missing else 0.0,
                "min": round(float(series.min()), 4) if total > missing else 0.0,
                "max": round(float(series.max()), 4) if total > missing else 0.0,
                "missing_rate": round(missing / total, 4) if total > 0 else 0.0,
            }

        logger.info(
            "Feature stats computed for %d features across %d rows",
            len(stats),
            len(feature_store_df),
        )
        return stats

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    def generate_report(
        self,
        results: dict[str, Any],
        output_path: Path,
    ) -> None:
        """Serialise evaluation results to a JSON file.

        Args:
            results: Arbitrary nested dict of evaluation outputs.
            output_path: Destination file path.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Make everything JSON-serialisable
        clean = _make_serialisable(results)

        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(clean, fh, indent=2, ensure_ascii=False)

        logger.info("Evaluation report written to %s", output_path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_serialisable(obj: Any) -> Any:
    """Recursively coerce objects into JSON-friendly types."""
    if isinstance(obj, dict):
        return {str(k): _make_serialisable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_serialisable(v) for v in obj]
    if isinstance(obj, set):
        return sorted(_make_serialisable(v) for v in obj)
    if isinstance(obj, float):
        if obj != obj:  # NaN
            return None
        return obj
    if isinstance(obj, (int, bool, str, type(None))):
        return obj
    # Fallback: stringify
    return str(obj)
