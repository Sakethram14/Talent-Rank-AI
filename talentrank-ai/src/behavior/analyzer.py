"""
Behavioral signal analyzer for TalentRank AI.

Computes a behavioral multiplier (0.0-1.0) that modulates a candidate's
ranking score based on real-world engagement signals.  Even a perfect
resume is worthless if the candidate never responds to recruiters.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional

from src.config.settings import get_settings
from src.data.models import CandidateRecord
from src.utils.logging import get_logger

logger = get_logger("behavior.analyzer")

# Reference date for activity calculations
REFERENCE_DATE: date = date(2026, 6, 15)


@dataclass
class BehavioralResult:
    """Result of behavioral analysis for a single candidate."""

    behavioral_multiplier: float
    response_factor: float
    activity_factor: float
    availability_factor: float
    engagement_score: float  # 0-100


class BehavioralAnalyzer:
    """
    Analyzes Redrob platform behavioral signals.

    The core output is ``behavioral_multiplier``, a float in [0.0, 1.0]
    that is multiplied into the candidate's final ranking score.

    **Penalty logic:**

    * ``response_factor`` — Heavy penalty if recruiter_response_rate < 0.1.
      A candidate who never replies is unhireable regardless of resume.
    * ``activity_factor`` — Penalty for inactive candidates.  Active within
      90 days = 1.0, within 180 days = 0.7, otherwise = 0.3.
    * ``availability_factor`` — Candidates *not* open to work get 0.6.

    ``behavioral_multiplier = response_factor × activity_factor × availability_factor``
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._min_response_rate = settings.behavior.min_response_rate
        self._max_inactive_days = settings.behavior.max_inactive_days
        self._github_not_linked = settings.behavior.github_not_linked_value

    def analyze(self, record: CandidateRecord) -> BehavioralResult:
        """
        Run behavioral analysis on a single candidate.

        Args:
            record: A fully-parsed CandidateRecord.

        Returns:
            BehavioralResult with the multiplier and sub-factors.
        """
        sig = record.redrob_signals

        # ── response factor ───────────────────────────────────────────────
        response_rate = sig.recruiter_response_rate
        if response_rate > 0:
            response_factor = max(0.1, response_rate)
        else:
            # Zero response rate — could be new user or truly unresponsive.
            # Give a small benefit of the doubt.
            response_factor = 0.2

        # ── activity factor ───────────────────────────────────────────────
        days_since = self._days_since_active(sig.last_active_date)
        if days_since < 0:
            # Cannot determine — neutral
            activity_factor = 0.5
        elif days_since <= 90:
            activity_factor = 1.0
        elif days_since <= 180:
            activity_factor = 0.7
        else:
            activity_factor = 0.3

        # ── availability factor ───────────────────────────────────────────
        availability_factor = 1.0 if sig.open_to_work_flag else 0.6

        # ── composite multiplier ──────────────────────────────────────────
        multiplier = response_factor * activity_factor * availability_factor
        multiplier = max(0.0, min(1.0, multiplier))

        # ── engagement score (0-100) ──────────────────────────────────────
        engagement = self._compute_engagement(sig)

        return BehavioralResult(
            behavioral_multiplier=round(multiplier, 4),
            response_factor=round(response_factor, 4),
            activity_factor=round(activity_factor, 4),
            availability_factor=round(availability_factor, 4),
            engagement_score=round(engagement, 2),
        )

    def compute_multiplier(self, record: CandidateRecord) -> float:
        """
        Convenience method returning just the scalar multiplier.

        Args:
            record: A CandidateRecord.

        Returns:
            Float in [0.0, 1.0].
        """
        return self.analyze(record).behavioral_multiplier

    # ── private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _days_since_active(last_active_str: str) -> int:
        """Compute days since last activity.  Returns -1 on parse failure."""
        if not last_active_str:
            return -1
        try:
            last_active = datetime.strptime(last_active_str, "%Y-%m-%d").date()
            delta = REFERENCE_DATE - last_active
            return max(delta.days, 0)
        except (ValueError, TypeError):
            return -1

    @staticmethod
    def _compute_engagement(sig) -> float:
        """
        Compute an engagement score (0-100) from platform activity.

        Combines profile views, saved-by-recruiters, and search appearances
        with diminishing-returns scaling.
        """
        import math

        # Logarithmic scaling so outliers don't dominate
        views_score = min(math.log1p(sig.profile_views_received_30d) * 10, 30)
        saved_score = min(math.log1p(sig.saved_by_recruiters_30d) * 15, 35)
        search_score = min(math.log1p(sig.search_appearance_30d) * 8, 20)

        # Verification bonus
        verification_bonus = 0.0
        if sig.verified_email:
            verification_bonus += 5.0
        if sig.verified_phone:
            verification_bonus += 5.0
        if sig.linkedin_connected:
            verification_bonus += 5.0

        total = views_score + saved_score + search_score + verification_bonus
        return min(total, 100.0)
