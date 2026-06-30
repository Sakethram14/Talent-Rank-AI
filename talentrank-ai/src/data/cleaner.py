"""
Candidate data cleaner for TalentRank AI.

Handles missing values, normalizes data, and applies transformations
that make records suitable for feature engineering.
"""

from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from src.data.models import CandidateRecord
from src.utils.text import clean_text, normalize_title
from src.utils.logging import get_logger

logger = get_logger("data.cleaner")

# Reference date for computing recency/activity metrics
REFERENCE_DATE = date(2026, 6, 15)


class CandidateCleaner:
    """
    Cleans and normalizes candidate records for downstream processing.

    Cleaning is in-place on the CandidateRecord objects.
    """

    def __init__(self, reference_date: Optional[date] = None) -> None:
        self.reference_date = reference_date or REFERENCE_DATE
        self._cleaned_count = 0

    def clean(self, record: CandidateRecord) -> CandidateRecord:
        """
        Clean a single candidate record.

        - Normalizes text fields
        - Fills missing values with sensible defaults
        - Computes derived date fields
        """
        self._clean_profile(record)
        self._clean_career(record)
        self._clean_skills(record)
        self._clean_education(record)
        self._clean_signals(record)

        self._cleaned_count += 1
        return record

    def clean_batch(self, records: list[CandidateRecord]) -> list[CandidateRecord]:
        """Clean a batch of records."""
        return [self.clean(r) for r in records]

    def _clean_profile(self, record: CandidateRecord) -> None:
        """Normalize profile text fields."""
        p = record.profile
        p.headline = clean_text(p.headline)
        p.summary = clean_text(p.summary)
        p.location = clean_text(p.location)
        p.country = clean_text(p.country)
        p.current_title = clean_text(p.current_title)
        p.current_company = clean_text(p.current_company)
        p.current_industry = clean_text(p.current_industry)

        # Clamp experience to valid range
        if p.years_of_experience < 0:
            p.years_of_experience = 0.0
        if p.years_of_experience > 50:
            p.years_of_experience = 50.0

    def _clean_career(self, record: CandidateRecord) -> None:
        """Normalize career history entries."""
        for entry in record.career_history:
            entry.title = clean_text(entry.title)
            entry.company = clean_text(entry.company)
            entry.description = clean_text(entry.description)
            entry.industry = clean_text(entry.industry)

            # Ensure non-negative duration
            if entry.duration_months < 0:
                entry.duration_months = 0

    def _clean_skills(self, record: CandidateRecord) -> None:
        """Normalize skill entries."""
        for skill in record.skills:
            skill.name = clean_text(skill.name)
            if skill.endorsements < 0:
                skill.endorsements = 0
            if skill.duration_months < 0:
                skill.duration_months = 0

    def _clean_education(self, record: CandidateRecord) -> None:
        """Normalize education entries."""
        for edu in record.education:
            edu.institution = clean_text(edu.institution)
            edu.degree = clean_text(edu.degree)
            edu.field_of_study = clean_text(edu.field_of_study)
            if not edu.tier:
                edu.tier = "unknown"

    def _clean_signals(self, record: CandidateRecord) -> None:
        """Normalize and fill behavioral signals."""
        sig = record.redrob_signals

        # Clamp rates to [0, 1]
        sig.recruiter_response_rate = max(0.0, min(1.0, sig.recruiter_response_rate))
        sig.interview_completion_rate = max(0.0, min(1.0, sig.interview_completion_rate))

        # Clamp profile completeness to [0, 100]
        sig.profile_completeness_score = max(0.0, min(100.0, sig.profile_completeness_score))

        # Clamp notice period
        sig.notice_period_days = max(0, min(180, sig.notice_period_days))

    @property
    def cleaned_count(self) -> int:
        return self._cleaned_count

    @staticmethod
    def days_since(date_str: str, reference: date) -> int:
        """Compute days between a date string and a reference date."""
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            return max(0, (reference - d).days)
        except (ValueError, TypeError):
            return -1  # Signal invalid/missing date
