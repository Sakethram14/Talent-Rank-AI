"""
Feature extractors for TalentRank AI.

Each extractor is responsible for computing a specific group of features
from a CandidateRecord.  Extractors are lightweight, stateless, and
designed for fast batch processing of 100k records within the 5-minute
compute budget.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import Any

from src.config.settings import get_settings
from src.data.models import CandidateRecord
from src.utils.logging import get_logger

logger = get_logger("features.extractors")

# ── constants derived from settings ──────────────────────────────────────────

_SETTINGS = get_settings()

# Curated AI/ML keyword list for the Senior AI Engineer JD
AI_KEYWORDS: frozenset[str] = frozenset(
    {
        "python",
        "machine learning",
        "deep learning",
        "nlp",
        "transformers",
        "embeddings",
        "vector database",
        "faiss",
        "pinecone",
        "qdrant",
        "milvus",
        "tensorflow",
        "pytorch",
        "scikit-learn",
        "huggingface",
        "langchain",
        "rag",
        "llm",
        "fine-tuning",
        "lora",
        "qlora",
        "bert",
        "gpt",
        "recommendation systems",
        "ranking systems",
        "search",
        "elasticsearch",
        "information retrieval",
        "a/b testing",
        "ndcg",
        "mlops",
    }
)

PROFICIENCY_SCORES: dict[str, int] = {
    "beginner": 1,
    "intermediate": 2,
    "advanced": 3,
    "expert": 4,
}

HEADLINE_RELEVANCE_KEYWORDS: frozenset[str] = frozenset(
    {"ai", "ml", "machine learning", "deep learning", "data science",
     "engineer", "nlp", "artificial intelligence"}
)

NON_RELEVANT_TITLES: frozenset[str] = frozenset(
    {"marketing manager", "sales manager", "hr manager", "content writer",
     "graphic designer", "marketing executive", "sales executive",
     "business development", "account manager", "marketing specialist",
     "social media manager", "copywriter", "recruiter", "financial analyst"}
)

AI_TITLE_KEYWORDS: frozenset[str] = frozenset(
    {"ai", "ml", "machine learning", "deep learning", "data scientist",
     "data science", "nlp", "artificial intelligence", "research scientist",
     "ai engineer", "ml engineer", "computer vision"}
)

TITLE_PROGRESSION_RANKS: dict[str, int] = {
    "intern": 0,
    "trainee": 0,
    "junior": 1,
    "associate": 1,
    "mid": 2,
    "senior": 3,
    "lead": 4,
    "staff": 4,
    "principal": 5,
    "director": 6,
    "vp": 7,
    "head": 7,
    "chief": 8,
    "cto": 8,
}

# Company sizes considered "large / product company" proxy
_LARGE_COMPANY_SIZES: frozenset[str] = frozenset(
    {"201-500", "501-1000", "1001-5000", "5001-10000", "10001+"}
)

DEGREE_LEVELS: dict[str, int] = {
    "phd": 4, "doctorate": 4, "ph.d": 4,
    "master": 3, "mtech": 3, "m.tech": 3, "ms": 3, "m.s": 3, "msc": 3,
    "m.sc": 3, "mba": 3, "m.e": 3, "me": 3,
    "bachelor": 2, "btech": 2, "b.tech": 2, "bs": 2, "b.s": 2, "bsc": 2,
    "b.sc": 2, "be": 2, "b.e": 2, "bca": 2, "b.c.a": 2,
    "diploma": 1, "associate": 1, "polytechnic": 1,
}

CS_RELATED_FIELDS: frozenset[str] = frozenset(
    {"computer science", "computer engineering", "information technology",
     "software engineering", "data science", "artificial intelligence",
     "machine learning", "electrical engineering", "electronics",
     "ece", "cse", "it", "cs", "mathematics", "statistics",
     "computational science", "information systems"}
)

# Reference date for "days since active" computation
REFERENCE_DATE: date = date(2026, 6, 15)


# ── base class ───────────────────────────────────────────────────────────────


class FeatureExtractor(ABC):
    """Base class for all feature extractors."""

    @abstractmethod
    def extract(self, record: CandidateRecord) -> dict[str, Any]:
        """
        Extract features from a single candidate record.

        Args:
            record: A fully-parsed CandidateRecord.

        Returns:
            Dictionary mapping feature names to their values.
        """

    @property
    @abstractmethod
    def feature_names(self) -> list[str]:
        """Return the ordered list of feature names this extractor produces."""


# ── Semantic (Skills / NLP) Features ─────────────────────────────────────────


class SemanticFeatureExtractor(FeatureExtractor):
    """Extracts features related to AI/ML skill match and profile text."""

    @property
    def feature_names(self) -> list[str]:
        return [
            "ai_keyword_count",
            "ai_skill_depth",
            "ai_skill_duration_total",
            "headline_relevance",
            "summary_length",
        ]

    def extract(self, record: CandidateRecord) -> dict[str, Any]:
        """Compute semantic / skill-based features."""
        skill_names_lower = [s.name.lower().strip() for s in record.skills]

        # ai_keyword_count: how many of the candidate's skills are in our AI keyword list
        ai_matches = [s for s in skill_names_lower if s in AI_KEYWORDS]
        ai_keyword_count = len(ai_matches)

        # ai_skill_depth: average proficiency score across AI-related skills
        ai_skill_proficiencies: list[int] = []
        ai_skill_duration: int = 0
        for skill in record.skills:
            if skill.name.lower().strip() in AI_KEYWORDS:
                prof = PROFICIENCY_SCORES.get(skill.proficiency.lower().strip(), 0)
                if prof > 0:
                    ai_skill_proficiencies.append(prof)
                ai_skill_duration += skill.duration_months

        ai_skill_depth = (
            sum(ai_skill_proficiencies) / len(ai_skill_proficiencies)
            if ai_skill_proficiencies
            else 0.0
        )

        # headline_relevance: binary — headline mentions relevant terms?
        headline_lower = record.profile.headline.lower()
        headline_relevance = int(
            any(kw in headline_lower for kw in HEADLINE_RELEVANCE_KEYWORDS)
        )

        # summary_length: raw character count (proxy for effort)
        summary_length = len(record.profile.summary)

        return {
            "ai_keyword_count": ai_keyword_count,
            "ai_skill_depth": round(ai_skill_depth, 4),
            "ai_skill_duration_total": ai_skill_duration,
            "headline_relevance": headline_relevance,
            "summary_length": summary_length,
        }


# ── Career Features ──────────────────────────────────────────────────────────


class CareerFeatureExtractor(FeatureExtractor):
    """Extracts career history and title-matching features."""

    def __init__(self) -> None:
        settings = get_settings()
        self._exp_min = settings.ranking.ideal_experience_min
        self._exp_max = settings.ranking.ideal_experience_max

    @property
    def feature_names(self) -> list[str]:
        return [
            "years_experience",
            "experience_in_range",
            "career_entry_count",
            "avg_tenure_months",
            "max_tenure_months",
            "has_current_role",
            "title_match_score",
            "title_is_ai_ml",
            "title_is_non_relevant",
            "career_in_product_companies",
            "career_progression_score",
            "total_career_months",
            "experience_consistency",
        ]

    def extract(self, record: CandidateRecord) -> dict[str, Any]:
        """Compute career features."""
        profile = record.profile
        career = record.career_history

        years_exp = profile.years_of_experience
        experience_in_range = int(self._exp_min <= years_exp <= self._exp_max)

        career_entry_count = len(career)
        durations = [c.duration_months for c in career]
        avg_tenure = sum(durations) / len(durations) if durations else 0.0
        max_tenure = max(durations) if durations else 0
        has_current = int(any(c.is_current for c in career))

        # Title match score for "Senior AI Engineer"
        title_match_score = self._compute_title_match(profile.current_title)
        title_is_ai_ml = int(self._is_ai_ml_title(profile.current_title))
        title_is_non_relevant = int(self._is_non_relevant_title(profile.current_title))

        # Product company proxy: large companies
        product_count = sum(
            1 for c in career if c.company_size in _LARGE_COMPANY_SIZES
        )

        # Career progression: are titles showing upward movement?
        progression_score = self._compute_progression(career)

        total_career_months = sum(durations)
        total_career_years = total_career_months / 12.0 if total_career_months > 0 else 0.0
        experience_consistency = (
            years_exp / total_career_years if total_career_years > 0 else 0.0
        )

        return {
            "years_experience": years_exp,
            "experience_in_range": experience_in_range,
            "career_entry_count": career_entry_count,
            "avg_tenure_months": round(avg_tenure, 2),
            "max_tenure_months": max_tenure,
            "has_current_role": has_current,
            "title_match_score": round(title_match_score, 4),
            "title_is_ai_ml": title_is_ai_ml,
            "title_is_non_relevant": title_is_non_relevant,
            "career_in_product_companies": product_count,
            "career_progression_score": round(progression_score, 4),
            "total_career_months": total_career_months,
            "experience_consistency": round(experience_consistency, 4),
        }

    # ── helper methods ────────────────────────────────────────────────────

    @staticmethod
    def _compute_title_match(title: str) -> float:
        """
        Score how well *title* matches 'Senior AI Engineer' (0‑1).

        Keyword-based: 'senior'=0.2, 'ai'=0.3, 'engineer'=0.2,
        'machine learning'=0.2, 'ml'=0.1.  Capped at 1.0.
        """
        t = title.lower()
        score = 0.0
        if "senior" in t:
            score += 0.2
        if "ai" in t or "artificial intelligence" in t:
            score += 0.3
        if "engineer" in t:
            score += 0.2
        if "machine learning" in t:
            score += 0.2
        if "ml" in t:
            score += 0.1
        return min(score, 1.0)

    @staticmethod
    def _is_ai_ml_title(title: str) -> bool:
        """Check whether the title indicates an AI/ML role."""
        t = title.lower()
        return any(kw in t for kw in AI_TITLE_KEYWORDS)

    @staticmethod
    def _is_non_relevant_title(title: str) -> bool:
        """Check whether the title is clearly non-relevant."""
        t = title.lower().strip()
        return any(kw in t for kw in NON_RELEVANT_TITLES)

    @staticmethod
    def _compute_progression(career: list) -> float:
        """
        Compute a career progression score (0‑1).

        Looks at title seniority across career entries (chronological).
        A monotonically increasing sequence scores 1.0.
        """
        if len(career) < 2:
            return 0.5  # Neutral — not enough data

        ranks: list[int] = []
        for entry in career:
            title_lower = entry.title.lower()
            best_rank = -1
            for keyword, rank in TITLE_PROGRESSION_RANKS.items():
                if keyword in title_lower and rank > best_rank:
                    best_rank = rank
            if best_rank >= 0:
                ranks.append(best_rank)

        if len(ranks) < 2:
            return 0.5

        # Count progressive steps vs. total steps
        progressive_steps = sum(
            1 for i in range(1, len(ranks)) if ranks[i] >= ranks[i - 1]
        )
        return progressive_steps / (len(ranks) - 1)


# ── Behavioral Features ──────────────────────────────────────────────────────


class BehavioralFeatureExtractor(FeatureExtractor):
    """Extracts behavioral signals from Redrob platform data."""

    @property
    def feature_names(self) -> list[str]:
        return [
            "recruiter_response_rate",
            "avg_response_time_hours",
            "interview_completion_rate",
            "offer_acceptance_rate",
            "profile_completeness",
            "days_since_active",
            "is_active_recently",
            "open_to_work",
            "github_activity_score",
            "has_github",
            "profile_views_30d",
            "saved_by_recruiters_30d",
            "search_appearance_30d",
            "applications_submitted_30d",
            "connection_count",
            "endorsements_received",
            "verified_email",
            "verified_phone",
            "linkedin_connected",
            "notice_period_days",
            "notice_period_ok",
            "willing_to_relocate",
            "preferred_work_mode",
        ]

    def extract(self, record: CandidateRecord) -> dict[str, Any]:
        """Compute behavioral features."""
        sig = record.redrob_signals

        # Days since last active
        days_since = self._days_since_active(sig.last_active_date)

        # Active within 90 days
        is_active_recently = int(days_since <= 90) if days_since >= 0 else 0

        # GitHub presence
        has_github = int(sig.github_activity_score >= 0)

        # Notice period OK (<=30 days is preferred)
        notice_ok = int(sig.notice_period_days <= 30)

        # Preferred work mode as categorical int
        work_mode_map = {"remote": 0, "hybrid": 1, "onsite": 2, "flexible": 3}
        pref_work = work_mode_map.get(sig.preferred_work_mode.lower().strip(), -1)

        return {
            "recruiter_response_rate": sig.recruiter_response_rate,
            "avg_response_time_hours": sig.avg_response_time_hours,
            "interview_completion_rate": sig.interview_completion_rate,
            "offer_acceptance_rate": sig.offer_acceptance_rate,
            "profile_completeness": sig.profile_completeness_score,
            "days_since_active": days_since,
            "is_active_recently": is_active_recently,
            "open_to_work": int(sig.open_to_work_flag),
            "github_activity_score": sig.github_activity_score,
            "has_github": has_github,
            "profile_views_30d": sig.profile_views_received_30d,
            "saved_by_recruiters_30d": sig.saved_by_recruiters_30d,
            "search_appearance_30d": sig.search_appearance_30d,
            "applications_submitted_30d": sig.applications_submitted_30d,
            "connection_count": sig.connection_count,
            "endorsements_received": sig.endorsements_received,
            "verified_email": int(sig.verified_email),
            "verified_phone": int(sig.verified_phone),
            "linkedin_connected": int(sig.linkedin_connected),
            "notice_period_days": sig.notice_period_days,
            "notice_period_ok": notice_ok,
            "willing_to_relocate": int(sig.willing_to_relocate),
            "preferred_work_mode": pref_work,
        }

    @staticmethod
    def _days_since_active(last_active_str: str) -> int:
        """
        Compute days between last_active_date and the reference date.

        Returns -1 if the date cannot be parsed.
        """
        if not last_active_str:
            return -1
        try:
            last_active = datetime.strptime(last_active_str, "%Y-%m-%d").date()
            delta = REFERENCE_DATE - last_active
            return max(delta.days, 0)
        except (ValueError, TypeError):
            return -1


# ── Education Features ────────────────────────────────────────────────────────


class EducationFeatureExtractor(FeatureExtractor):
    """Extracts education-related features."""

    @property
    def feature_names(self) -> list[str]:
        return [
            "highest_degree_level",
            "cs_related_field",
            "tier_1_education",
            "best_education_tier",
        ]

    def extract(self, record: CandidateRecord) -> dict[str, Any]:
        """Compute education features."""
        edu = record.education

        # Highest degree level
        highest = 0
        for entry in edu:
            deg_lower = entry.degree.lower().strip()
            for keyword, level in DEGREE_LEVELS.items():
                if keyword in deg_lower and level > highest:
                    highest = level

        # CS-related field
        cs_related = int(
            any(
                any(kw in e.field_of_study.lower() for kw in CS_RELATED_FIELDS)
                for e in edu
            )
        ) if edu else 0

        # Tier assessment
        tier_map = {"tier_1": 4, "tier_2": 3, "tier_3": 2, "tier_4": 1, "unknown": 0}
        best_tier = max(
            (tier_map.get(e.tier.lower().strip(), 0) for e in edu),
            default=0,
        )
        tier_1_education = int(best_tier == 4)

        return {
            "highest_degree_level": highest,
            "cs_related_field": cs_related,
            "tier_1_education": tier_1_education,
            "best_education_tier": best_tier,
        }


# ── Risk Features ─────────────────────────────────────────────────────────────


class RiskFeatureExtractor(FeatureExtractor):
    """Extracts salary, certification, and assessment features."""

    @property
    def feature_names(self) -> list[str]:
        return [
            "salary_expectation_min",
            "salary_expectation_max",
            "certification_count",
            "language_count",
            "has_skill_assessments",
            "avg_assessment_score",
        ]

    def extract(self, record: CandidateRecord) -> dict[str, Any]:
        """Compute risk / supplementary features."""
        sig = record.redrob_signals
        scores = sig.skill_assessment_scores

        has_assessments = int(len(scores) > 0)
        avg_score = (
            sum(scores.values()) / len(scores) if scores else 0.0
        )

        return {
            "salary_expectation_min": sig.expected_salary_range.min_lpa,
            "salary_expectation_max": sig.expected_salary_range.max_lpa,
            "certification_count": len(record.certifications),
            "language_count": len(record.languages),
            "has_skill_assessments": has_assessments,
            "avg_assessment_score": round(avg_score, 4),
        }


# ── Honeypot Detection Features ──────────────────────────────────────────────


class HoneypotFeatureExtractor(FeatureExtractor):
    """
    Extracts features designed to detect honeypot / fabricated profiles.

    These features catch impossible combinations:
    - Expert skills with zero duration
    - Skill durations exceeding claimed experience
    - Experience inflation (claimed vs. career-history mismatch)
    - Impossible career dates
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._max_inflation = settings.honeypot.max_experience_inflation_ratio
        self._max_expert_zero = settings.honeypot.max_expert_zero_duration_skills

    @property
    def feature_names(self) -> list[str]:
        return [
            "expert_skills_with_zero_duration",
            "skill_duration_exceeds_experience",
            "experience_inflation_ratio",
            "impossible_career_dates",
            "too_many_expert_skills",
            "honeypot_score",
        ]

    def extract(self, record: CandidateRecord) -> dict[str, Any]:
        """Compute honeypot detection features."""
        skills = record.skills
        career = record.career_history
        years_exp = record.profile.years_of_experience

        # Expert skills with zero duration
        expert_zero = sum(
            1
            for s in skills
            if s.proficiency.lower().strip() == "expert" and s.duration_months == 0
        )

        # Skill duration exceeds claimed experience (with 12-month grace)
        max_allowed_months = years_exp * 12 + 12
        skill_exceeds = int(
            any(s.duration_months > max_allowed_months for s in skills)
        )

        # Experience inflation: claimed years vs. career-history total
        total_career_months = sum(c.duration_months for c in career)
        total_career_years = total_career_months / 12.0 if total_career_months > 0 else 0.001
        inflation_ratio = years_exp / total_career_years if total_career_years > 0 else 0.0

        # Impossible career dates: start_date > end_date
        impossible_dates = int(self._has_impossible_dates(career))

        # Too many expert skills
        expert_count = sum(
            1 for s in skills if s.proficiency.lower().strip() == "expert"
        )

        # Composite honeypot score (0-1)
        honeypot_score = self._compute_honeypot_score(
            expert_zero=expert_zero,
            skill_exceeds=skill_exceeds,
            inflation_ratio=inflation_ratio,
            impossible_dates=impossible_dates,
            expert_count=expert_count,
        )

        return {
            "expert_skills_with_zero_duration": expert_zero,
            "skill_duration_exceeds_experience": skill_exceeds,
            "experience_inflation_ratio": round(inflation_ratio, 4),
            "impossible_career_dates": impossible_dates,
            "too_many_expert_skills": expert_count,
            "honeypot_score": round(honeypot_score, 4),
        }

    @staticmethod
    def _has_impossible_dates(career: list) -> bool:
        """Check if any career entry has start_date > end_date."""
        for entry in career:
            if entry.start_date and entry.end_date:
                try:
                    start = datetime.strptime(entry.start_date, "%Y-%m-%d").date()
                    end = datetime.strptime(entry.end_date, "%Y-%m-%d").date()
                    if start > end:
                        return True
                except (ValueError, TypeError):
                    continue
        return False

    def _compute_honeypot_score(
        self,
        *,
        expert_zero: int,
        skill_exceeds: int,
        inflation_ratio: float,
        impossible_dates: int,
        expert_count: int,
    ) -> float:
        """
        Composite honeypot score combining all indicators (0-1).

        Each indicator contributes a fraction; they are averaged.
        Higher score = more suspicious.
        """
        signals: list[float] = []

        # Expert skills with zero duration (>2 is very suspicious)
        signals.append(min(expert_zero / max(self._max_expert_zero, 1), 1.0))

        # Skill duration exceeds experience
        signals.append(float(skill_exceeds))

        # Inflation ratio (>1.5 is suspicious)
        if inflation_ratio > self._max_inflation:
            signals.append(min((inflation_ratio - 1.0) / 2.0, 1.0))
        else:
            signals.append(0.0)

        # Impossible dates
        signals.append(float(impossible_dates))

        # Too many expert skills (>8 is suspicious)
        if expert_count > 8:
            signals.append(min((expert_count - 8) / 8.0, 1.0))
        else:
            signals.append(0.0)

        return sum(signals) / len(signals) if signals else 0.0
