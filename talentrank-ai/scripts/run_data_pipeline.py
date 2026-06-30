"""
Main data processing pipeline for TalentRank AI.

Orchestrates parsing, validation, and cleaning of the full
100k candidate dataset. Run this script first before any
downstream processing.

Usage:
    python -m scripts.run_data_pipeline
    python -m scripts.run_data_pipeline --max-records 1000
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config.settings import get_settings, reset_settings
from src.data.parser import CandidateParser
from src.data.validator import CandidateValidator
from src.data.cleaner import CandidateCleaner
from src.utils.logging import get_logger
from src.utils.io import save_json

logger = get_logger("pipeline.data")


def run_data_pipeline(
    max_records: int | None = None,
    validate: bool = True,
    clean: bool = True,
) -> dict:
    """
    Run the complete data processing pipeline.

    Steps:
        1. Parse JSONL → CandidateRecord objects
        2. Validate each record against schema rules
        3. Clean and normalize each record
        4. Check for duplicates
        5. Generate data quality report

    Args:
        max_records: Process only the first N records (for development).
        validate: Whether to run validation.
        clean: Whether to run cleaning.

    Returns:
        Data quality statistics dict.
    """
    reset_settings()
    settings = get_settings(project_root=PROJECT_ROOT)
    start_time = time.time()

    # ── Step 1: Parse ──
    logger.info("=" * 60)
    logger.info("STEP 1: Parsing candidates from %s", settings.paths.candidates_jsonl)
    parser = CandidateParser(filepath=settings.paths.candidates_jsonl)
    candidates = parser.load_all(max_records=max_records)
    logger.info("Parsed %d candidates in %.1fs", len(candidates), time.time() - start_time)

    # ── Step 2: Validate ──
    if validate:
        logger.info("=" * 60)
        logger.info("STEP 2: Validating candidates")
        validator = CandidateValidator()
        candidates = validator.validate_batch(candidates)
        invalid_count = sum(1 for c in candidates if not c.is_valid)
        logger.info(
            "Validation complete: %d valid, %d invalid (%.1f%% valid rate)",
            len(candidates) - invalid_count,
            invalid_count,
            (len(candidates) - invalid_count) / len(candidates) * 100
            if candidates else 0,
        )

        # Check duplicates
        duplicates = validator.check_duplicates(candidates)
        if duplicates:
            logger.warning("Duplicate candidate_ids found: %s", duplicates[:10])

    # ── Step 3: Clean ──
    if clean:
        logger.info("=" * 60)
        logger.info("STEP 3: Cleaning and normalizing candidates")
        cleaner = CandidateCleaner()
        candidates = cleaner.clean_batch(candidates)
        logger.info("Cleaned %d candidates", cleaner.cleaned_count)

    # ── Step 4: Data Quality Report ──
    elapsed = time.time() - start_time
    logger.info("=" * 60)
    logger.info("STEP 4: Generating data quality report")

    report = _generate_quality_report(candidates, elapsed)

    # Save report
    report_path = settings.paths.data_processed / "data_quality_report.json"
    save_json(report, report_path)
    logger.info("Data quality report saved to %s", report_path)

    # Print summary
    logger.info("=" * 60)
    logger.info("DATA PIPELINE COMPLETE")
    logger.info("  Total candidates: %d", report["total_candidates"])
    logger.info("  Valid candidates: %d", report["valid_candidates"])
    logger.info("  Invalid candidates: %d", report["invalid_candidates"])
    logger.info("  Total time: %.1fs", elapsed)
    logger.info("  Processing rate: %.0f records/sec", report["processing_rate"])
    logger.info("=" * 60)

    return report


def _generate_quality_report(candidates: list, elapsed: float) -> dict:
    """Generate a comprehensive data quality report."""
    total = len(candidates)
    valid = sum(1 for c in candidates if c.is_valid)
    invalid = total - valid

    # Collect validation error types
    error_types: dict[str, int] = {}
    for c in candidates:
        for err in c.validation_errors:
            key = err.split(":")[0].strip() if ":" in err else err[:50]
            error_types[key] = error_types.get(key, 0) + 1

    # Experience distribution
    exp_values = [c.profile.years_of_experience for c in candidates]
    exp_in_range = sum(1 for e in exp_values if 5 <= e <= 9)

    # Title distribution (top 20)
    title_counts: dict[str, int] = {}
    for c in candidates:
        title = c.profile.current_title or "UNKNOWN"
        title_counts[title] = title_counts.get(title, 0) + 1
    top_titles = sorted(title_counts.items(), key=lambda x: -x[1])[:20]

    # Country distribution
    country_counts: dict[str, int] = {}
    for c in candidates:
        country = c.profile.country or "UNKNOWN"
        country_counts[country] = country_counts.get(country, 0) + 1

    # Skill stats
    skill_counts = [len(c.skills) for c in candidates]
    avg_skills = sum(skill_counts) / total if total else 0

    # Behavioral signal averages
    avg_response_rate = (
        sum(c.redrob_signals.recruiter_response_rate for c in candidates) / total
        if total else 0
    )
    open_to_work_count = sum(1 for c in candidates if c.redrob_signals.open_to_work_flag)

    return {
        "total_candidates": total,
        "valid_candidates": valid,
        "invalid_candidates": invalid,
        "valid_rate": valid / total if total else 0,
        "processing_time_seconds": round(elapsed, 2),
        "processing_rate": round(total / elapsed, 0) if elapsed > 0 else 0,
        "error_types": dict(sorted(error_types.items(), key=lambda x: -x[1])[:20]),
        "experience": {
            "min": min(exp_values) if exp_values else 0,
            "max": max(exp_values) if exp_values else 0,
            "mean": sum(exp_values) / total if total else 0,
            "in_jd_range_5_9": exp_in_range,
            "in_jd_range_pct": exp_in_range / total * 100 if total else 0,
        },
        "top_titles": dict(top_titles),
        "country_distribution": dict(sorted(country_counts.items(), key=lambda x: -x[1])[:15]),
        "skills": {
            "avg_per_candidate": round(avg_skills, 1),
            "min": min(skill_counts) if skill_counts else 0,
            "max": max(skill_counts) if skill_counts else 0,
        },
        "behavioral": {
            "avg_recruiter_response_rate": round(avg_response_rate, 3),
            "open_to_work_count": open_to_work_count,
            "open_to_work_pct": round(open_to_work_count / total * 100, 1) if total else 0,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Run the TalentRank AI data pipeline")
    parser.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="Process only the first N records (for development)",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip validation step",
    )
    parser.add_argument(
        "--skip-cleaning",
        action="store_true",
        help="Skip cleaning step",
    )
    args = parser.parse_args()

    run_data_pipeline(
        max_records=args.max_records,
        validate=not args.skip_validation,
        clean=not args.skip_cleaning,
    )


if __name__ == "__main__":
    main()
