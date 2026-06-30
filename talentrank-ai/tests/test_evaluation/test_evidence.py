"""
Tests for the evidence collection module.

Validates that EvidenceCollector produces correct positive/negative
signals, risk flags, and summaries for clearly good, clearly bad,
and honeypot candidates.
"""

from __future__ import annotations

import pytest

from src.data.models import (
    CandidateRecord,
    CareerEntry,
    EducationEntry,
    Profile,
    RedrobSignals,
    SalaryRange,
    SkillEntry,
)
from src.explanations.evidence import (
    CandidateEvidence,
    EvidenceCollector,
    EvidenceItem,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_good_candidate() -> CandidateRecord:
    """AI Engineer, 7 years, high signals — should score well."""
    return CandidateRecord(
        candidate_id="CAND_0000001",
        profile=Profile(
            anonymized_name="Candidate A",
            headline="Senior ML Engineer | NLP | Deep Learning",
            summary="7 years building production ML systems.",
            location="Pune, Maharashtra",
            country="India",
            years_of_experience=7.0,
            current_title="Senior Machine Learning Engineer",
            current_company="TechProduct Inc.",
            current_company_size="201-500",
            current_industry="Technology / Product",
        ),
        career_history=[
            CareerEntry(
                company="TechProduct Inc.",
                title="Senior Machine Learning Engineer",
                start_date="2021-01-01",
                end_date=None,
                duration_months=42,
                is_current=True,
                industry="Technology / Product",
                company_size="201-500",
            ),
            CareerEntry(
                company="DataStartup",
                title="ML Engineer",
                start_date="2018-01-01",
                end_date="2020-12-31",
                duration_months=36,
                is_current=False,
                industry="SaaS / Startup",
                company_size="11-50",
            ),
        ],
        skills=[
            SkillEntry(name="Python", proficiency="expert", endorsements=15, duration_months=84),
            SkillEntry(name="PyTorch", proficiency="advanced", endorsements=10, duration_months=48),
            SkillEntry(name="Transformers", proficiency="advanced", endorsements=8, duration_months=36),
            SkillEntry(name="FAISS", proficiency="intermediate", endorsements=5, duration_months=24),
            SkillEntry(name="Docker", proficiency="advanced", endorsements=7, duration_months=36),
            SkillEntry(name="SQL", proficiency="advanced", endorsements=6, duration_months=60),
        ],
        redrob_signals=RedrobSignals(
            profile_completeness_score=85.0,
            signup_date="2023-01-15",
            last_active_date="2026-06-25",
            open_to_work_flag=True,
            recruiter_response_rate=0.76,
            avg_response_time_hours=4.0,
            notice_period_days=15,
            expected_salary_range=SalaryRange(min_lpa=25.0, max_lpa=35.0),
            preferred_work_mode="hybrid",
            willing_to_relocate=True,
            github_activity_score=0.72,
            interview_completion_rate=0.90,
            offer_acceptance_rate=0.80,
            verified_email=True,
            verified_phone=True,
            linkedin_connected=True,
        ),
    )


def _make_bad_candidate() -> CandidateRecord:
    """Marketing Manager, low signals — should score poorly for ML role."""
    return CandidateRecord(
        candidate_id="CAND_0000002",
        profile=Profile(
            anonymized_name="Candidate B",
            headline="Marketing Manager | Growth",
            summary="3 years in digital marketing.",
            location="Mumbai, Maharashtra",
            country="India",
            years_of_experience=3.0,
            current_title="Marketing Manager",
            current_company="AdAgency Ltd.",
            current_company_size="51-200",
            current_industry="Advertising / Consulting",
        ),
        career_history=[
            CareerEntry(
                company="AdAgency Ltd.",
                title="Marketing Manager",
                start_date="2023-06-01",
                end_date=None,
                duration_months=12,
                is_current=True,
                industry="Advertising / Consulting",
                company_size="51-200",
            ),
            CareerEntry(
                company="Accenture",
                title="Marketing Associate",
                start_date="2022-01-01",
                end_date="2023-05-31",
                duration_months=17,
                is_current=False,
                industry="Consulting",
                company_size="10001+",
            ),
        ],
        skills=[
            SkillEntry(name="Excel", proficiency="advanced", endorsements=5, duration_months=36),
            SkillEntry(name="SEO", proficiency="intermediate", endorsements=3, duration_months=24),
        ],
        redrob_signals=RedrobSignals(
            profile_completeness_score=40.0,
            signup_date="2024-06-01",
            last_active_date="2025-01-01",
            open_to_work_flag=False,
            recruiter_response_rate=0.02,
            avg_response_time_hours=72.0,
            notice_period_days=90,
            expected_salary_range=SalaryRange(min_lpa=8.0, max_lpa=12.0),
            preferred_work_mode="onsite",
            willing_to_relocate=False,
            github_activity_score=-1.0,
            interview_completion_rate=0.30,
            offer_acceptance_rate=-1.0,
        ),
    )


def _make_honeypot_candidate() -> CandidateRecord:
    """Known honeypot — should surface honeypot evidence."""
    record = CandidateRecord(
        candidate_id="CAND_0000003",
        profile=Profile(
            anonymized_name="Candidate C",
            headline="AI Researcher / ML Architect",
            summary="Expert in everything AI with 6 years of experience.",
            location="Noida, UP",
            country="India",
            years_of_experience=6.0,
            current_title="AI Research Lead",
            current_company="FakeAI Corp",
            current_company_size="11-50",
            current_industry="Technology / Product",
        ),
        career_history=[
            CareerEntry(
                company="FakeAI Corp",
                title="AI Research Lead",
                start_date="2024-01-01",
                end_date=None,
                duration_months=6,
                is_current=True,
                industry="Technology / Product",
                company_size="11-50",
            ),
            CareerEntry(
                company="TempJob Inc",
                title="Data Analyst",
                start_date="2023-01-01",
                end_date="2023-12-31",
                duration_months=8,
                is_current=False,
                industry="Consulting",
                company_size="51-200",
            ),
        ],
        skills=[
            SkillEntry(name="Python", proficiency="expert", endorsements=0, duration_months=0),
            SkillEntry(name="PyTorch", proficiency="expert", endorsements=0, duration_months=0),
        ],
        redrob_signals=RedrobSignals(
            profile_completeness_score=95.0,
            signup_date="2024-06-01",
            last_active_date="2026-06-20",
            open_to_work_flag=True,
            recruiter_response_rate=0.90,
            avg_response_time_hours=1.0,
            notice_period_days=0,
            expected_salary_range=SalaryRange(min_lpa=10.0, max_lpa=15.0),
            preferred_work_mode="remote",
            willing_to_relocate=True,
            github_activity_score=0.95,
            interview_completion_rate=1.0,
            offer_acceptance_rate=1.0,
            verified_email=True,
            verified_phone=True,
            linkedin_connected=True,
        ),
    )
    record.is_honeypot = True
    record.honeypot_reasons = [
        "Expert skills with zero duration",
        "Experience inflation detected",
    ]
    return record


@pytest.fixture
def collector() -> EvidenceCollector:
    """Shared EvidenceCollector instance."""
    return EvidenceCollector()


@pytest.fixture
def good_candidate() -> CandidateRecord:
    return _make_good_candidate()


@pytest.fixture
def bad_candidate() -> CandidateRecord:
    return _make_bad_candidate()


@pytest.fixture
def honeypot_candidate() -> CandidateRecord:
    return _make_honeypot_candidate()


# Dummy feature scores (keys match a plausible feature store)
_GOOD_FEATURES: dict[str, float] = {
    "experience_score": 0.85,
    "skill_match_score": 0.90,
    "behavior_score": 0.80,
    "semantic_similarity": 0.75,
}

_BAD_FEATURES: dict[str, float] = {
    "experience_score": 0.20,
    "skill_match_score": 0.05,
    "behavior_score": 0.10,
    "semantic_similarity": 0.15,
}

_HONEYPOT_FEATURES: dict[str, float] = {
    "experience_score": 0.95,
    "skill_match_score": 0.98,
    "behavior_score": 0.99,
    "semantic_similarity": 0.92,
}


# ---------------------------------------------------------------------------
# Good candidate tests
# ---------------------------------------------------------------------------


class TestGoodCandidate:
    """Evidence for a strong AI/ML candidate."""

    def test_has_positive_signals(
        self, collector: EvidenceCollector, good_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(good_candidate, _GOOD_FEATURES)
        assert len(evidence.positive_signals) >= 5

    def test_experience_in_range(
        self, collector: EvidenceCollector, good_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(good_candidate, _GOOD_FEATURES)
        signal_names = [s.signal_name for s in evidence.positive_signals]
        assert "experience_in_range" in signal_names

    def test_relevant_title(
        self, collector: EvidenceCollector, good_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(good_candidate, _GOOD_FEATURES)
        signal_names = [s.signal_name for s in evidence.positive_signals]
        assert "relevant_title" in signal_names

    def test_strong_skill_match(
        self, collector: EvidenceCollector, good_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(good_candidate, _GOOD_FEATURES)
        signal_names = [s.signal_name for s in evidence.positive_signals]
        assert "strong_skill_match" in signal_names

    def test_high_response_rate(
        self, collector: EvidenceCollector, good_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(good_candidate, _GOOD_FEATURES)
        signal_names = [s.signal_name for s in evidence.positive_signals]
        assert "high_response_rate" in signal_names

    def test_short_notice(
        self, collector: EvidenceCollector, good_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(good_candidate, _GOOD_FEATURES)
        signal_names = [s.signal_name for s in evidence.positive_signals]
        assert "short_notice" in signal_names

    def test_preferred_location(
        self, collector: EvidenceCollector, good_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(good_candidate, _GOOD_FEATURES)
        signal_names = [s.signal_name for s in evidence.positive_signals]
        assert "preferred_location" in signal_names

    def test_not_honeypot(
        self, collector: EvidenceCollector, good_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(good_candidate, _GOOD_FEATURES)
        assert evidence.is_honeypot is False
        assert evidence.honeypot_reasons == []

    def test_behavioral_summary(
        self, collector: EvidenceCollector, good_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(good_candidate, _GOOD_FEATURES)
        assert evidence.behavioral_summary["response_rate"] == 0.76
        assert evidence.behavioral_summary["open_to_work"] is True
        assert evidence.behavioral_summary["availability"] == "immediate"

    def test_career_summary(
        self, collector: EvidenceCollector, good_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(good_candidate, _GOOD_FEATURES)
        assert evidence.career_summary["years_of_experience"] == 7.0
        assert evidence.career_summary["company_count"] == 2

    def test_feature_contributions_passed_through(
        self, collector: EvidenceCollector, good_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(good_candidate, _GOOD_FEATURES)
        assert evidence.feature_contributions == _GOOD_FEATURES

    def test_no_risk_flags(
        self, collector: EvidenceCollector, good_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(good_candidate, _GOOD_FEATURES)
        assert len(evidence.risk_flags) == 0

    def test_overall_assessment_mentions_title(
        self, collector: EvidenceCollector, good_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(good_candidate, _GOOD_FEATURES)
        assert "Machine Learning" in evidence.overall_assessment

    def test_overall_assessment_not_empty(
        self, collector: EvidenceCollector, good_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(good_candidate, _GOOD_FEATURES)
        assert len(evidence.overall_assessment) > 20


# ---------------------------------------------------------------------------
# Bad candidate tests
# ---------------------------------------------------------------------------


class TestBadCandidate:
    """Evidence for a clearly mismatched candidate."""

    def test_has_negative_signals(
        self, collector: EvidenceCollector, bad_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(bad_candidate, _BAD_FEATURES)
        assert len(evidence.negative_signals) >= 4

    def test_experience_below_range(
        self, collector: EvidenceCollector, bad_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(bad_candidate, _BAD_FEATURES)
        signal_names = [s.signal_name for s in evidence.negative_signals]
        assert "experience_below_range" in signal_names

    def test_non_relevant_title(
        self, collector: EvidenceCollector, bad_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(bad_candidate, _BAD_FEATURES)
        signal_names = [s.signal_name for s in evidence.negative_signals]
        assert "non_relevant_title" in signal_names

    def test_no_skill_match(
        self, collector: EvidenceCollector, bad_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(bad_candidate, _BAD_FEATURES)
        signal_names = [s.signal_name for s in evidence.negative_signals]
        assert "no_skill_match" in signal_names

    def test_low_response_rate(
        self, collector: EvidenceCollector, bad_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(bad_candidate, _BAD_FEATURES)
        signal_names = [s.signal_name for s in evidence.negative_signals]
        assert "low_response_rate" in signal_names

    def test_no_github(
        self, collector: EvidenceCollector, bad_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(bad_candidate, _BAD_FEATURES)
        signal_names = [s.signal_name for s in evidence.negative_signals]
        assert "no_github" in signal_names

    def test_long_notice(
        self, collector: EvidenceCollector, bad_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(bad_candidate, _BAD_FEATURES)
        signal_names = [s.signal_name for s in evidence.negative_signals]
        assert "long_notice" in signal_names

    def test_consulting_only_background(
        self, collector: EvidenceCollector, bad_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(bad_candidate, _BAD_FEATURES)
        signal_names = [s.signal_name for s in evidence.negative_signals]
        assert "consulting_only_background" in signal_names

    def test_fewer_positive_signals(
        self, collector: EvidenceCollector, bad_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(bad_candidate, _BAD_FEATURES)
        assert len(evidence.positive_signals) < len(evidence.negative_signals)

    def test_career_summary_low_experience(
        self, collector: EvidenceCollector, bad_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(bad_candidate, _BAD_FEATURES)
        assert evidence.career_summary["years_of_experience"] == 3.0


# ---------------------------------------------------------------------------
# Honeypot candidate tests
# ---------------------------------------------------------------------------


class TestHoneypotCandidate:
    """Evidence for a candidate flagged as a honeypot."""

    def test_is_honeypot(
        self, collector: EvidenceCollector, honeypot_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(honeypot_candidate, _HONEYPOT_FEATURES)
        assert evidence.is_honeypot is True

    def test_honeypot_reasons_preserved(
        self, collector: EvidenceCollector, honeypot_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(honeypot_candidate, _HONEYPOT_FEATURES)
        assert len(evidence.honeypot_reasons) == 2
        assert "Experience inflation detected" in evidence.honeypot_reasons

    def test_risk_flags_include_honeypot(
        self, collector: EvidenceCollector, honeypot_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(honeypot_candidate, _HONEYPOT_FEATURES)
        honeypot_flags = [f for f in evidence.risk_flags if "Honeypot" in f]
        assert len(honeypot_flags) >= 1

    def test_job_hopping_risk(
        self, collector: EvidenceCollector, honeypot_candidate: CandidateRecord
    ) -> None:
        """Honeypot candidate also has short average tenure → job-hopping flag."""
        evidence = collector.collect(honeypot_candidate, _HONEYPOT_FEATURES)
        hopping_flags = [f for f in evidence.risk_flags if "job hopping" in f.lower()]
        assert len(hopping_flags) >= 1

    def test_overall_assessment_mentions_honeypot(
        self, collector: EvidenceCollector, honeypot_candidate: CandidateRecord
    ) -> None:
        evidence = collector.collect(honeypot_candidate, _HONEYPOT_FEATURES)
        assert "honeypot" in evidence.overall_assessment.lower()

    def test_still_has_positive_signals(
        self, collector: EvidenceCollector, honeypot_candidate: CandidateRecord
    ) -> None:
        """Even honeypots can have legitimate-looking positive signals."""
        evidence = collector.collect(honeypot_candidate, _HONEYPOT_FEATURES)
        assert len(evidence.positive_signals) > 0


# ---------------------------------------------------------------------------
# EvidenceItem dataclass tests
# ---------------------------------------------------------------------------


class TestEvidenceItem:
    """Basic sanity checks for the EvidenceItem dataclass."""

    def test_creation(self) -> None:
        item = EvidenceItem(
            signal_name="test_signal",
            value=42,
            impact="positive",
            weight=0.5,
            description="Test description",
        )
        assert item.signal_name == "test_signal"
        assert item.value == 42
        assert item.impact == "positive"
        assert item.weight == 0.5
        assert item.description == "Test description"


class TestCandidateEvidence:
    """Basic sanity checks for the CandidateEvidence dataclass."""

    def test_defaults(self) -> None:
        ev = CandidateEvidence(candidate_id="CAND_TEST")
        assert ev.positive_signals == []
        assert ev.negative_signals == []
        assert ev.neutral_signals == []
        assert ev.risk_flags == []
        assert ev.feature_contributions == {}
        assert ev.overall_assessment == ""
        assert ev.is_honeypot is False
        assert ev.honeypot_reasons == []
