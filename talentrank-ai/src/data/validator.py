"""
Candidate data validator for TalentRank AI.

Validates candidate records against the official candidate_schema.json
rules and business logic constraints derived from the challenge resources.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

from src.config.settings import get_settings, DataConfig
from src.data.models import CandidateRecord
from src.utils.logging import get_logger

logger = get_logger("data.validator")

_CANDIDATE_ID_RE = re.compile(r"^CAND_\d{7}$")


class CandidateValidator:
    """
    Validates candidate records against schema and business rules.

    Validation is non-destructive: it annotates records with
    validation_errors and is_valid flags rather than discarding them.
    """

    def __init__(self) -> None:
        self.config: DataConfig = get_settings().data
        self._total_validated = 0
        self._total_invalid = 0

    def validate(self, record: CandidateRecord) -> CandidateRecord:
        """
        Validate a single candidate record.

        Populates record.validation_errors and record.is_valid.
        """
        errors: list[str] = []

        # ── candidate_id ──
        if not _CANDIDATE_ID_RE.match(record.candidate_id):
            errors.append(f"Invalid candidate_id format: '{record.candidate_id}'")

        # ── profile ──
        p = record.profile
        if not p.headline:
            errors.append("Missing profile.headline")
        if not p.summary:
            errors.append("Missing profile.summary")
        if p.years_of_experience < 0 or p.years_of_experience > 50:
            errors.append(f"years_of_experience out of range: {p.years_of_experience}")
        if p.current_company_size and p.current_company_size not in self.config.valid_company_sizes:
            errors.append(f"Invalid company_size: '{p.current_company_size}'")

        # ── career_history ──
        if not record.career_history:
            errors.append("Empty career_history (schema requires minItems: 1)")
        if len(record.career_history) > self.config.max_career_entries:
            errors.append(f"career_history exceeds max {self.config.max_career_entries}")

        for i, entry in enumerate(record.career_history):
            if entry.duration_months < 0:
                errors.append(f"career_history[{i}].duration_months < 0")
            if not entry.company:
                errors.append(f"career_history[{i}].company is empty")
            if not entry.title:
                errors.append(f"career_history[{i}].title is empty")
            # Validate date formats
            if entry.start_date:
                if not self._is_valid_date(entry.start_date):
                    errors.append(f"career_history[{i}].start_date invalid: '{entry.start_date}'")

        # ── education ──
        if len(record.education) > self.config.max_education_entries:
            errors.append(f"education exceeds max {self.config.max_education_entries}")

        for i, edu in enumerate(record.education):
            if edu.start_year and edu.end_year and edu.end_year < edu.start_year:
                errors.append(f"education[{i}].end_year < start_year")
            if edu.tier and edu.tier not in self.config.valid_education_tiers:
                errors.append(f"education[{i}].tier invalid: '{edu.tier}'")

        # ── skills ──
        for i, skill in enumerate(record.skills):
            if not skill.name:
                errors.append(f"skills[{i}].name is empty")
            if skill.proficiency and skill.proficiency not in self.config.valid_proficiency_levels:
                errors.append(f"skills[{i}].proficiency invalid: '{skill.proficiency}'")
            if skill.endorsements < 0:
                errors.append(f"skills[{i}].endorsements < 0")
            if skill.duration_months < 0:
                errors.append(f"skills[{i}].duration_months < 0")

        # ── redrob_signals ──
        sig = record.redrob_signals
        if sig.profile_completeness_score < 0 or sig.profile_completeness_score > 100:
            errors.append(f"profile_completeness_score out of range: {sig.profile_completeness_score}")
        if sig.recruiter_response_rate < 0 or sig.recruiter_response_rate > 1:
            errors.append(f"recruiter_response_rate out of range: {sig.recruiter_response_rate}")
        if sig.interview_completion_rate < 0 or sig.interview_completion_rate > 1:
            errors.append(f"interview_completion_rate out of range: {sig.interview_completion_rate}")
        if sig.preferred_work_mode and sig.preferred_work_mode not in self.config.valid_work_modes:
            errors.append(f"preferred_work_mode invalid: '{sig.preferred_work_mode}'")

        # Store results
        record.validation_errors = errors
        record.is_valid = len(errors) == 0

        self._total_validated += 1
        if not record.is_valid:
            self._total_invalid += 1

        return record

    def validate_batch(self, records: list[CandidateRecord]) -> list[CandidateRecord]:
        """Validate a batch of records."""
        return [self.validate(r) for r in records]

    @staticmethod
    def _is_valid_date(date_str: str) -> bool:
        """Check if a string is a valid ISO date."""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except (ValueError, TypeError):
            return False

    def check_duplicates(self, records: list[CandidateRecord]) -> list[str]:
        """
        Check for duplicate candidate_ids.

        Returns list of duplicate IDs found.
        """
        seen: dict[str, int] = {}
        duplicates: list[str] = []
        for r in records:
            if r.candidate_id in seen:
                duplicates.append(r.candidate_id)
            seen[r.candidate_id] = seen.get(r.candidate_id, 0) + 1

        if duplicates:
            logger.warning("Found %d duplicate candidate_ids", len(duplicates))
        else:
            logger.info("No duplicate candidate_ids found")
        return duplicates

    @property
    def stats(self) -> dict:
        return {
            "total_validated": self._total_validated,
            "total_invalid": self._total_invalid,
            "valid_rate": (
                (self._total_validated - self._total_invalid) / self._total_validated
                if self._total_validated > 0 else 0
            ),
        }
