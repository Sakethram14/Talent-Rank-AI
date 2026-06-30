"""
Evidence collection for candidate explainability.

Produces structured evidence explaining *why* each candidate received
their score.  The evidence is purely factual — derived from the
candidate record and computed feature scores — so that downstream
narrative generators can produce human-readable summaries without
hallucination.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from src.config.settings import get_settings
from src.data.models import CandidateRecord
from src.utils.logging import get_logger

logger = get_logger("explanations.evidence")

# ---------------------------------------------------------------------------
# JD-derived constants (centralised so nothing is hard-coded in logic)
# ---------------------------------------------------------------------------

_JD_MIN_EXPERIENCE_YEARS: float = 5.0
_JD_MAX_EXPERIENCE_YEARS: float = 9.0
_JD_MAX_NOTICE_DAYS: int = 30
_JD_PREFERRED_LOCATIONS: tuple[str, ...] = ("pune", "noida")
_JD_RELEVANT_TITLE_KEYWORDS: tuple[str, ...] = (
    "machine learning",
    "ml",
    "data scientist",
    "ai",
    "deep learning",
    "nlp",
    "computer vision",
    "software engineer",
    "backend",
    "platform",
    "research",
)
_JD_RELEVANT_SKILL_KEYWORDS: tuple[str, ...] = (
    "python",
    "pytorch",
    "tensorflow",
    "scikit-learn",
    "embeddings",
    "vector",
    "faiss",
    "qdrant",
    "pinecone",
    "milvus",
    "chromadb",
    "langchain",
    "transformers",
    "huggingface",
    "mlflow",
    "kubernetes",
    "docker",
    "aws",
    "gcp",
    "sql",
)
_JD_SALARY_MAX_LPA: float = 40.0  # Approximate budget ceiling

_CONSULTING_KEYWORDS: tuple[str, ...] = (
    "consulting",
    "consultancy",
    "infosys",
    "wipro",
    "tcs",
    "hcl",
    "cognizant",
    "accenture",
    "capgemini",
    "tech mahindra",
)
_PRODUCT_KEYWORDS: tuple[str, ...] = (
    "product",
    "startup",
    "saas",
    "platform",
)

# Thresholds sourced from settings where available
_settings = get_settings()
_HIGH_RESPONSE_RATE: float = 0.50
_LOW_RESPONSE_RATE: float = _settings.behavior.min_response_rate
_GITHUB_NOT_LINKED: float = _settings.behavior.github_not_linked_value
_JOB_HOPPING_THRESHOLD_MONTHS: int = 12


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class EvidenceItem:
    """A single explainability signal for a candidate.

    Attributes:
        signal_name: Machine-readable identifier, e.g. ``'recruiter_response_rate'``.
        value: The raw metric value.
        impact: One of ``'positive'``, ``'negative'``, or ``'neutral'``.
        weight: Contribution magnitude in ``[0, 1]``.
        description: Human-readable sentence, e.g. *'Strong recruiter response rate (76 %)'*.
    """

    signal_name: str
    value: Any
    impact: str  # 'positive' | 'negative' | 'neutral'
    weight: float
    description: str


@dataclass
class CandidateEvidence:
    """Aggregated evidence for a single candidate.

    This is the output of :class:`EvidenceCollector` and feeds into the
    narrative generator and the evaluation framework.
    """

    candidate_id: str
    positive_signals: list[EvidenceItem] = field(default_factory=list)
    negative_signals: list[EvidenceItem] = field(default_factory=list)
    neutral_signals: list[EvidenceItem] = field(default_factory=list)
    behavioral_summary: dict[str, Any] = field(default_factory=dict)
    career_summary: dict[str, Any] = field(default_factory=dict)
    risk_flags: list[str] = field(default_factory=list)
    feature_contributions: dict[str, float] = field(default_factory=dict)
    overall_assessment: str = ""
    is_honeypot: bool = False
    honeypot_reasons: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Collector
# ---------------------------------------------------------------------------


class EvidenceCollector:
    """Analyse a :class:`CandidateRecord` against the JD and produce
    structured :class:`CandidateEvidence`.

    Usage::

        collector = EvidenceCollector()
        evidence = collector.collect(record, feature_scores)
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def collect(
        self,
        record: CandidateRecord,
        feature_scores: dict[str, float],
    ) -> CandidateEvidence:
        """Build a complete :class:`CandidateEvidence` for *record*.

        Args:
            record: Fully-parsed candidate record.
            feature_scores: Dict mapping feature names to their computed
                numeric scores (e.g. from the feature store).

        Returns:
            Structured evidence object.
        """
        evidence = CandidateEvidence(candidate_id=record.candidate_id)

        # 1. Honeypot pass-through
        evidence.is_honeypot = record.is_honeypot
        evidence.honeypot_reasons = list(record.honeypot_reasons)

        # 2. Feature contributions
        evidence.feature_contributions = dict(feature_scores)

        # 3. Signal analysis (populates positive / negative / neutral)
        self._analyse_experience(record, evidence)
        self._analyse_title(record, evidence)
        self._analyse_skills(record, evidence)
        self._analyse_response_rate(record, evidence)
        self._analyse_activity(record, evidence)
        self._analyse_github(record, evidence)
        self._analyse_notice_period(record, evidence)
        self._analyse_location(record, evidence)
        self._analyse_company_background(record, evidence)
        self._analyse_open_to_work(record, evidence)
        self._analyse_profile_completeness(record, evidence)

        # 4. Summaries
        evidence.behavioral_summary = self._build_behavioral_summary(record)
        evidence.career_summary = self._build_career_summary(record)

        # 5. Risk flags
        evidence.risk_flags = self._build_risk_flags(record, evidence)

        # 6. Overall assessment (factual, no hallucination)
        evidence.overall_assessment = self._build_overall_assessment(
            record, evidence
        )

        logger.debug(
            "Evidence collected for %s: %d positive, %d negative, %d risk flags",
            record.candidate_id,
            len(evidence.positive_signals),
            len(evidence.negative_signals),
            len(evidence.risk_flags),
        )
        return evidence

    # ------------------------------------------------------------------
    # Signal analysers
    # ------------------------------------------------------------------

    def _analyse_experience(
        self,
        record: CandidateRecord,
        evidence: CandidateEvidence,
    ) -> None:
        """Check years of experience against the JD ideal range."""
        yoe = record.profile.years_of_experience
        if _JD_MIN_EXPERIENCE_YEARS <= yoe <= _JD_MAX_EXPERIENCE_YEARS:
            evidence.positive_signals.append(
                EvidenceItem(
                    signal_name="experience_in_range",
                    value=yoe,
                    impact="positive",
                    weight=0.8,
                    description=(
                        f"Experience ({yoe:.1f} yrs) is within the ideal "
                        f"{_JD_MIN_EXPERIENCE_YEARS:.0f}–{_JD_MAX_EXPERIENCE_YEARS:.0f} yr range"
                    ),
                )
            )
        elif yoe < _JD_MIN_EXPERIENCE_YEARS:
            evidence.negative_signals.append(
                EvidenceItem(
                    signal_name="experience_below_range",
                    value=yoe,
                    impact="negative",
                    weight=0.7,
                    description=(
                        f"Experience ({yoe:.1f} yrs) is below the minimum "
                        f"{_JD_MIN_EXPERIENCE_YEARS:.0f} yrs required"
                    ),
                )
            )
        else:
            evidence.neutral_signals.append(
                EvidenceItem(
                    signal_name="experience_above_range",
                    value=yoe,
                    impact="neutral",
                    weight=0.4,
                    description=(
                        f"Experience ({yoe:.1f} yrs) exceeds the ideal "
                        f"{_JD_MAX_EXPERIENCE_YEARS:.0f} yr maximum — may be overqualified"
                    ),
                )
            )

    def _analyse_title(
        self,
        record: CandidateRecord,
        evidence: CandidateEvidence,
    ) -> None:
        """Check whether the current title aligns with ML/AI roles."""
        title_lower = record.profile.current_title.lower()
        matched = any(kw in title_lower for kw in _JD_RELEVANT_TITLE_KEYWORDS)
        if matched:
            evidence.positive_signals.append(
                EvidenceItem(
                    signal_name="relevant_title",
                    value=record.profile.current_title,
                    impact="positive",
                    weight=0.7,
                    description=(
                        f"Current title '{record.profile.current_title}' "
                        f"aligns with AI/ML role requirements"
                    ),
                )
            )
        else:
            evidence.negative_signals.append(
                EvidenceItem(
                    signal_name="non_relevant_title",
                    value=record.profile.current_title,
                    impact="negative",
                    weight=0.6,
                    description=(
                        f"Current title '{record.profile.current_title}' "
                        f"does not indicate AI/ML experience"
                    ),
                )
            )

    def _analyse_skills(
        self,
        record: CandidateRecord,
        evidence: CandidateEvidence,
    ) -> None:
        """Count JD-relevant skills present on the candidate's profile."""
        candidate_skills = {s.name.lower() for s in record.skills}
        matched_skills = [
            kw for kw in _JD_RELEVANT_SKILL_KEYWORDS if kw in candidate_skills
        ]
        match_count = len(matched_skills)

        if match_count >= 4:
            evidence.positive_signals.append(
                EvidenceItem(
                    signal_name="strong_skill_match",
                    value=matched_skills,
                    impact="positive",
                    weight=0.8,
                    description=(
                        f"{match_count} JD-relevant skills matched: "
                        f"{', '.join(matched_skills[:6])}"
                    ),
                )
            )
        elif match_count >= 1:
            evidence.neutral_signals.append(
                EvidenceItem(
                    signal_name="partial_skill_match",
                    value=matched_skills,
                    impact="neutral",
                    weight=0.4,
                    description=(
                        f"{match_count} JD-relevant skill(s) matched: "
                        f"{', '.join(matched_skills)}"
                    ),
                )
            )
        else:
            evidence.negative_signals.append(
                EvidenceItem(
                    signal_name="no_skill_match",
                    value=[],
                    impact="negative",
                    weight=0.7,
                    description="No JD-relevant skills found on profile",
                )
            )

    def _analyse_response_rate(
        self,
        record: CandidateRecord,
        evidence: CandidateEvidence,
    ) -> None:
        """Evaluate recruiter response rate."""
        rate = record.redrob_signals.recruiter_response_rate
        if rate >= _HIGH_RESPONSE_RATE:
            evidence.positive_signals.append(
                EvidenceItem(
                    signal_name="high_response_rate",
                    value=rate,
                    impact="positive",
                    weight=0.5,
                    description=(
                        f"Strong recruiter response rate ({rate:.0%})"
                    ),
                )
            )
        elif rate < _LOW_RESPONSE_RATE:
            evidence.negative_signals.append(
                EvidenceItem(
                    signal_name="low_response_rate",
                    value=rate,
                    impact="negative",
                    weight=0.4,
                    description=(
                        f"Very low recruiter response rate ({rate:.0%})"
                    ),
                )
            )
        else:
            evidence.neutral_signals.append(
                EvidenceItem(
                    signal_name="moderate_response_rate",
                    value=rate,
                    impact="neutral",
                    weight=0.2,
                    description=(
                        f"Moderate recruiter response rate ({rate:.0%})"
                    ),
                )
            )

    def _analyse_activity(
        self,
        record: CandidateRecord,
        evidence: CandidateEvidence,
    ) -> None:
        """Check recency of platform activity."""
        last_active = record.redrob_signals.last_active_date
        if not last_active:
            evidence.negative_signals.append(
                EvidenceItem(
                    signal_name="no_activity_date",
                    value=None,
                    impact="negative",
                    weight=0.3,
                    description="No last-active date recorded",
                )
            )
            return

        try:
            last_dt = datetime.fromisoformat(last_active)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            days_since = (datetime.now(timezone.utc) - last_dt).days
        except (ValueError, TypeError):
            evidence.neutral_signals.append(
                EvidenceItem(
                    signal_name="unparseable_activity_date",
                    value=last_active,
                    impact="neutral",
                    weight=0.1,
                    description="Could not parse last-active date",
                )
            )
            return

        max_inactive = self._settings.behavior.max_inactive_days
        if days_since <= max_inactive:
            evidence.positive_signals.append(
                EvidenceItem(
                    signal_name="recently_active",
                    value=days_since,
                    impact="positive",
                    weight=0.4,
                    description=(
                        f"Active within the last {days_since} day(s)"
                    ),
                )
            )
        else:
            evidence.negative_signals.append(
                EvidenceItem(
                    signal_name="inactive",
                    value=days_since,
                    impact="negative",
                    weight=0.4,
                    description=(
                        f"Last active {days_since} days ago — may be inactive"
                    ),
                )
            )

    def _analyse_github(
        self,
        record: CandidateRecord,
        evidence: CandidateEvidence,
    ) -> None:
        """Check GitHub activity score."""
        score = record.redrob_signals.github_activity_score
        if score == _GITHUB_NOT_LINKED:
            evidence.negative_signals.append(
                EvidenceItem(
                    signal_name="no_github",
                    value=score,
                    impact="negative",
                    weight=0.3,
                    description="No GitHub profile linked",
                )
            )
        elif score >= 0.5:
            evidence.positive_signals.append(
                EvidenceItem(
                    signal_name="strong_github",
                    value=score,
                    impact="positive",
                    weight=0.4,
                    description=(
                        f"Good GitHub activity score ({score:.2f})"
                    ),
                )
            )
        else:
            evidence.neutral_signals.append(
                EvidenceItem(
                    signal_name="low_github",
                    value=score,
                    impact="neutral",
                    weight=0.2,
                    description=(
                        f"Low GitHub activity score ({score:.2f})"
                    ),
                )
            )

    def _analyse_notice_period(
        self,
        record: CandidateRecord,
        evidence: CandidateEvidence,
    ) -> None:
        """Evaluate notice period against JD preference."""
        days = record.redrob_signals.notice_period_days
        if days <= _JD_MAX_NOTICE_DAYS:
            evidence.positive_signals.append(
                EvidenceItem(
                    signal_name="short_notice",
                    value=days,
                    impact="positive",
                    weight=0.3,
                    description=(
                        f"Notice period ({days} days) meets the sub-"
                        f"{_JD_MAX_NOTICE_DAYS}-day preference"
                    ),
                )
            )
        else:
            evidence.negative_signals.append(
                EvidenceItem(
                    signal_name="long_notice",
                    value=days,
                    impact="negative",
                    weight=0.3,
                    description=(
                        f"Notice period ({days} days) exceeds the "
                        f"{_JD_MAX_NOTICE_DAYS}-day preference"
                    ),
                )
            )

    def _analyse_location(
        self,
        record: CandidateRecord,
        evidence: CandidateEvidence,
    ) -> None:
        """Check location against JD preferred cities."""
        loc_lower = record.profile.location.lower()
        matched = any(city in loc_lower for city in _JD_PREFERRED_LOCATIONS)
        if matched:
            evidence.positive_signals.append(
                EvidenceItem(
                    signal_name="preferred_location",
                    value=record.profile.location,
                    impact="positive",
                    weight=0.3,
                    description=(
                        f"Location '{record.profile.location}' is a "
                        f"preferred JD location"
                    ),
                )
            )
        elif record.redrob_signals.willing_to_relocate:
            evidence.neutral_signals.append(
                EvidenceItem(
                    signal_name="willing_to_relocate",
                    value=record.profile.location,
                    impact="neutral",
                    weight=0.2,
                    description=(
                        f"Not in a preferred city ({record.profile.location}) "
                        f"but willing to relocate"
                    ),
                )
            )
        else:
            evidence.negative_signals.append(
                EvidenceItem(
                    signal_name="non_preferred_location",
                    value=record.profile.location,
                    impact="negative",
                    weight=0.2,
                    description=(
                        f"Location '{record.profile.location}' is not a "
                        f"preferred JD location and not willing to relocate"
                    ),
                )
            )

    def _analyse_company_background(
        self,
        record: CandidateRecord,
        evidence: CandidateEvidence,
    ) -> None:
        """Determine product-company vs consulting-only background."""
        companies = [
            entry.company.lower() for entry in record.career_history
        ]
        industries = [
            entry.industry.lower() for entry in record.career_history
        ]
        all_text = " ".join(companies + industries)

        has_product = any(kw in all_text for kw in _PRODUCT_KEYWORDS)
        has_consulting = any(kw in all_text for kw in _CONSULTING_KEYWORDS)

        if has_product:
            evidence.positive_signals.append(
                EvidenceItem(
                    signal_name="product_company_experience",
                    value=True,
                    impact="positive",
                    weight=0.4,
                    description="Has product / startup company experience",
                )
            )
        if has_consulting and not has_product:
            evidence.negative_signals.append(
                EvidenceItem(
                    signal_name="consulting_only_background",
                    value=True,
                    impact="negative",
                    weight=0.3,
                    description=(
                        "Career history shows only consulting/services "
                        "companies — JD prefers product-company background"
                    ),
                )
            )

    def _analyse_open_to_work(
        self,
        record: CandidateRecord,
        evidence: CandidateEvidence,
    ) -> None:
        """Check open-to-work flag."""
        if record.redrob_signals.open_to_work_flag:
            evidence.positive_signals.append(
                EvidenceItem(
                    signal_name="open_to_work",
                    value=True,
                    impact="positive",
                    weight=0.2,
                    description="Candidate is actively open to work",
                )
            )

    def _analyse_profile_completeness(
        self,
        record: CandidateRecord,
        evidence: CandidateEvidence,
    ) -> None:
        """Evaluate profile completeness score."""
        score = record.redrob_signals.profile_completeness_score
        min_completeness = self._settings.behavior.min_profile_completeness
        if score >= 70.0:
            evidence.positive_signals.append(
                EvidenceItem(
                    signal_name="complete_profile",
                    value=score,
                    impact="positive",
                    weight=0.2,
                    description=(
                        f"Profile is well-completed ({score:.0f}%)"
                    ),
                )
            )
        elif score < min_completeness:
            evidence.negative_signals.append(
                EvidenceItem(
                    signal_name="incomplete_profile",
                    value=score,
                    impact="negative",
                    weight=0.3,
                    description=(
                        f"Profile completeness ({score:.0f}%) is below "
                        f"the {min_completeness:.0f}% minimum threshold"
                    ),
                )
            )

    # ------------------------------------------------------------------
    # Summaries
    # ------------------------------------------------------------------

    def _build_behavioral_summary(
        self, record: CandidateRecord
    ) -> dict[str, Any]:
        """Aggregate key behavioral signals into a flat dict."""
        signals = record.redrob_signals

        # Determine activity status
        activity_status = "unknown"
        if signals.last_active_date:
            try:
                last_dt = datetime.fromisoformat(signals.last_active_date)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                days = (datetime.now(timezone.utc) - last_dt).days
                max_inactive = self._settings.behavior.max_inactive_days
                activity_status = "active" if days <= max_inactive else "inactive"
            except (ValueError, TypeError):
                activity_status = "unknown"

        return {
            "response_rate": signals.recruiter_response_rate,
            "activity_status": activity_status,
            "interview_completion_rate": signals.interview_completion_rate,
            "availability": (
                "immediate"
                if signals.notice_period_days <= _JD_MAX_NOTICE_DAYS
                else f"{signals.notice_period_days}-day notice"
            ),
            "open_to_work": signals.open_to_work_flag,
            "profile_completeness": signals.profile_completeness_score,
        }

    def _build_career_summary(
        self, record: CandidateRecord
    ) -> dict[str, Any]:
        """Aggregate career trajectory metrics."""
        durations = [
            entry.duration_months
            for entry in record.career_history
            if entry.duration_months > 0
        ]
        avg_tenure = (
            sum(durations) / len(durations) if durations else 0.0
        )

        # Simple title-progression heuristic: count distinct titles
        titles = [
            entry.title for entry in record.career_history if entry.title
        ]
        unique_titles = list(dict.fromkeys(titles))  # preserve order

        return {
            "years_of_experience": record.profile.years_of_experience,
            "current_title": record.profile.current_title,
            "current_company": record.profile.current_company,
            "company_count": len(record.career_history),
            "avg_tenure_months": round(avg_tenure, 1),
            "title_progression": unique_titles,
        }

    # ------------------------------------------------------------------
    # Risk flags
    # ------------------------------------------------------------------

    def _build_risk_flags(
        self,
        record: CandidateRecord,
        evidence: CandidateEvidence,
    ) -> list[str]:
        """Compile risk flags from record and already-collected signals."""
        flags: list[str] = []

        # Honeypot
        if record.is_honeypot:
            flags.append(
                f"Honeypot candidate: {'; '.join(record.honeypot_reasons)}"
            )

        # Job-hopping
        durations = [
            e.duration_months
            for e in record.career_history
            if e.duration_months > 0
        ]
        if durations:
            avg = sum(durations) / len(durations)
            if avg < _JOB_HOPPING_THRESHOLD_MONTHS:
                flags.append(
                    f"Frequent job hopping — average tenure {avg:.0f} months"
                )

        # Salary expectation mismatch
        salary = record.redrob_signals.expected_salary_range
        if salary.min_lpa > _JD_SALARY_MAX_LPA:
            flags.append(
                f"Salary expectation ({salary.min_lpa:.0f}–"
                f"{salary.max_lpa:.0f} LPA) exceeds budget ceiling"
            )

        # Validation errors carried forward
        if record.validation_errors:
            flags.append(
                f"Validation issues: {'; '.join(record.validation_errors[:3])}"
            )

        return flags

    # ------------------------------------------------------------------
    # Overall assessment
    # ------------------------------------------------------------------

    def _build_overall_assessment(
        self,
        record: CandidateRecord,
        evidence: CandidateEvidence,
    ) -> str:
        """Produce a factual 1-2 sentence summary from collected signals.

        The text is composed entirely from the signals already gathered
        (no LLM, no hallucination).
        """
        parts: list[str] = []

        yoe = record.profile.years_of_experience
        title = record.profile.current_title or "Unknown role"
        parts.append(f"{title} with {yoe:.1f} years of experience.")

        pos_count = len(evidence.positive_signals)
        neg_count = len(evidence.negative_signals)
        risk_count = len(evidence.risk_flags)

        if evidence.is_honeypot:
            parts.append("Flagged as a honeypot candidate.")
        elif risk_count > 0:
            parts.append(
                f"{pos_count} positive signal(s) but "
                f"{risk_count} risk flag(s) identified."
            )
        elif neg_count == 0 and pos_count > 0:
            parts.append("Strong overall match with no negative signals.")
        else:
            parts.append(
                f"{pos_count} positive and {neg_count} negative signal(s)."
            )

        return " ".join(parts)
