"""
Unit tests for the feature engineering layer.

Tests focus on:
- HoneypotFeatureExtractor: catching fabricated profiles
- BehavioralFeatureExtractor: edge cases with missing / zero signals
- CareerFeatureExtractor: title matching and progression scoring
- BehavioralAnalyzer: multiplier computation
- FeaturePipeline: end-to-end integration
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure project root is on sys.path so ``src.`` imports work
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.config.settings import reset_settings  # noqa: E402
from src.data.models import (  # noqa: E402
    CandidateRecord,
    CareerEntry,
    EducationEntry,
    LanguageEntry,
    Profile,
    RedrobSignals,
    SalaryRange,
    SkillEntry,
    CertificationEntry,
)
from src.features.extractors import (  # noqa: E402
    BehavioralFeatureExtractor,
    CareerFeatureExtractor,
    EducationFeatureExtractor,
    HoneypotFeatureExtractor,
    RiskFeatureExtractor,
    SemanticFeatureExtractor,
)
from src.behavior.analyzer import BehavioralAnalyzer  # noqa: E402
from src.features.pipeline import FeaturePipeline  # noqa: E402
from src.features.store import FeatureStore  # noqa: E402


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_settings():
    """Reset singleton settings before each test."""
    reset_settings()
    yield
    reset_settings()


def _make_candidate(**overrides) -> CandidateRecord:
    """Build a CandidateRecord with sensible defaults, overridable."""
    defaults = dict(
        candidate_id="CAND_0000001",
        profile=Profile(
            anonymized_name="Test Candidate",
            headline="Senior AI Engineer with ML expertise",
            summary="Experienced in production ML systems, embeddings, and RAG.",
            location="Bangalore",
            country="India",
            years_of_experience=7.0,
            current_title="Senior AI Engineer",
            current_company="TechCorp",
            current_company_size="501-1000",
            current_industry="Technology",
        ),
        career_history=[
            CareerEntry(
                company="TechCorp",
                title="Senior AI Engineer",
                start_date="2022-01-01",
                end_date=None,
                duration_months=42,
                is_current=True,
                industry="Technology",
                company_size="501-1000",
                description="Building ML platform",
            ),
            CareerEntry(
                company="DataInc",
                title="ML Engineer",
                start_date="2019-06-01",
                end_date="2021-12-31",
                duration_months=30,
                is_current=False,
                industry="Technology",
                company_size="201-500",
                description="NLP models for search",
            ),
        ],
        education=[
            EducationEntry(
                institution="IIT Bombay",
                degree="B.Tech",
                field_of_study="Computer Science",
                start_year=2014,
                end_year=2018,
                tier="tier_1",
            ),
        ],
        skills=[
            SkillEntry(name="Python", proficiency="expert", endorsements=50, duration_months=72),
            SkillEntry(name="PyTorch", proficiency="advanced", endorsements=30, duration_months=48),
            SkillEntry(name="Machine Learning", proficiency="expert", endorsements=40, duration_months=60),
            SkillEntry(name="NLP", proficiency="advanced", endorsements=25, duration_months=36),
            SkillEntry(name="Embeddings", proficiency="intermediate", endorsements=10, duration_months=24),
        ],
        certifications=[
            CertificationEntry(name="AWS ML Specialty", issuer="AWS", year=2023),
        ],
        languages=[
            LanguageEntry(language="English", proficiency="professional"),
            LanguageEntry(language="Hindi", proficiency="native"),
        ],
        redrob_signals=RedrobSignals(
            profile_completeness_score=85.0,
            signup_date="2023-01-15",
            last_active_date="2026-06-10",
            open_to_work_flag=True,
            profile_views_received_30d=45,
            applications_submitted_30d=12,
            recruiter_response_rate=0.75,
            avg_response_time_hours=4.5,
            skill_assessment_scores={"python": 92.0, "ml": 88.0},
            connection_count=500,
            endorsements_received=120,
            notice_period_days=30,
            expected_salary_range=SalaryRange(min_lpa=25.0, max_lpa=35.0),
            preferred_work_mode="hybrid",
            willing_to_relocate=True,
            github_activity_score=72.0,
            search_appearance_30d=150,
            saved_by_recruiters_30d=8,
            interview_completion_rate=0.9,
            offer_acceptance_rate=0.8,
            verified_email=True,
            verified_phone=True,
            linkedin_connected=True,
        ),
    )
    defaults.update(overrides)
    return CandidateRecord(**defaults)


def _make_honeypot_candidate() -> CandidateRecord:
    """Build a clearly-fraudulent honeypot candidate."""
    return _make_candidate(
        candidate_id="CAND_HONEYPOT",
        profile=Profile(
            anonymized_name="Fake Expert",
            headline="Marketing Manager with 20 years of experience",
            summary="",
            location="Delhi",
            country="India",
            years_of_experience=20.0,
            current_title="Marketing Manager",
            current_company="FakeCorp",
            current_company_size="1-10",
            current_industry="Marketing",
        ),
        career_history=[
            CareerEntry(
                company="FakeCorp",
                title="Marketing Manager",
                start_date="2024-01-01",
                end_date="2023-06-01",  # Impossible: start > end
                duration_months=6,
                is_current=True,
                industry="Marketing",
                company_size="1-10",
                description="Marketing stuff",
            ),
        ],
        skills=[
            SkillEntry(name="Python", proficiency="expert", endorsements=0, duration_months=0),
            SkillEntry(name="Machine Learning", proficiency="expert", endorsements=0, duration_months=0),
            SkillEntry(name="Deep Learning", proficiency="expert", endorsements=0, duration_months=0),
            SkillEntry(name="NLP", proficiency="expert", endorsements=0, duration_months=0),
            SkillEntry(name="PyTorch", proficiency="expert", endorsements=0, duration_months=0),
            SkillEntry(name="TensorFlow", proficiency="expert", endorsements=0, duration_months=0),
            SkillEntry(name="LLM", proficiency="expert", endorsements=0, duration_months=0),
            SkillEntry(name="RAG", proficiency="expert", endorsements=0, duration_months=0),
            SkillEntry(name="Embeddings", proficiency="expert", endorsements=0, duration_months=0),
            SkillEntry(name="FAISS", proficiency="expert", endorsements=0, duration_months=0),
            SkillEntry(name="LangChain", proficiency="expert", endorsements=0, duration_months=0),
            SkillEntry(name="MLOps", proficiency="expert", endorsements=0, duration_months=0),
        ],
        education=[],
        certifications=[],
        languages=[],
        redrob_signals=RedrobSignals(
            profile_completeness_score=20.0,
            last_active_date="2025-01-01",
            recruiter_response_rate=0.02,
        ),
    )


def _make_inactive_candidate() -> CandidateRecord:
    """Build a candidate inactive for >180 days."""
    return _make_candidate(
        candidate_id="CAND_INACTIVE",
        redrob_signals=RedrobSignals(
            profile_completeness_score=60.0,
            last_active_date="2025-06-01",
            open_to_work_flag=False,
            recruiter_response_rate=0.05,
            avg_response_time_hours=72.0,
        ),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Honeypot Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestHoneypotFeatureExtractor:
    """Tests for honeypot detection."""

    def setup_method(self):
        self.extractor = HoneypotFeatureExtractor()

    def test_clean_candidate_low_honeypot_score(self):
        """A legitimate candidate should have a low honeypot score."""
        record = _make_candidate()
        features = self.extractor.extract(record)
        assert features["honeypot_score"] < 0.3
        assert features["expert_skills_with_zero_duration"] == 0
        assert features["impossible_career_dates"] == 0

    def test_honeypot_candidate_high_score(self):
        """A fabricated candidate should have a high honeypot score."""
        record = _make_honeypot_candidate()
        features = self.extractor.extract(record)
        assert features["honeypot_score"] > 0.4
        assert features["expert_skills_with_zero_duration"] >= 10
        assert features["impossible_career_dates"] == 1

    def test_expert_zero_duration_count(self):
        """Count expert skills with 0 duration_months."""
        record = _make_honeypot_candidate()
        features = self.extractor.extract(record)
        # All 12 skills are expert with 0 duration
        assert features["expert_skills_with_zero_duration"] == 12

    def test_too_many_expert_skills(self):
        """Flag when expert skill count exceeds threshold."""
        record = _make_honeypot_candidate()
        features = self.extractor.extract(record)
        assert features["too_many_expert_skills"] == 12
        assert features["too_many_expert_skills"] > 8  # Threshold

    def test_impossible_career_dates_detected(self):
        """Detect start_date > end_date."""
        record = _make_honeypot_candidate()
        features = self.extractor.extract(record)
        assert features["impossible_career_dates"] == 1

    def test_experience_inflation(self):
        """Detect inflated years_of_experience vs career history."""
        record = _make_honeypot_candidate()
        features = self.extractor.extract(record)
        # Claims 20 years but career is 6 months → ratio = 20 / 0.5 = 40
        assert features["experience_inflation_ratio"] > 10.0

    def test_skill_duration_exceeds_experience(self):
        """Skills shouldn't last longer than total experience + grace."""
        record = _make_candidate(
            profile=Profile(years_of_experience=2.0),
            skills=[
                SkillEntry(name="Python", proficiency="expert", endorsements=0, duration_months=60),
            ],
        )
        features = self.extractor.extract(record)
        # 60 months > 2*12+12 = 36 months
        assert features["skill_duration_exceeds_experience"] == 1

    def test_clean_skill_duration_within_experience(self):
        """Skills within experience range should not flag."""
        record = _make_candidate(
            profile=Profile(years_of_experience=7.0),
            skills=[
                SkillEntry(name="Python", proficiency="expert", endorsements=0, duration_months=72),
            ],
        )
        features = self.extractor.extract(record)
        # 72 months <= 7*12+12 = 96 months
        assert features["skill_duration_exceeds_experience"] == 0


# ══════════════════════════════════════════════════════════════════════════════
# Behavioral Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestBehavioralFeatureExtractor:
    """Tests for behavioral feature extraction."""

    def setup_method(self):
        self.extractor = BehavioralFeatureExtractor()

    def test_active_candidate(self):
        """Recently active candidate should be flagged."""
        record = _make_candidate()
        features = self.extractor.extract(record)
        assert features["is_active_recently"] == 1
        assert features["days_since_active"] < 90
        assert features["open_to_work"] == 1

    def test_inactive_candidate(self):
        """Inactive candidate should not be flagged as recently active."""
        record = _make_inactive_candidate()
        features = self.extractor.extract(record)
        assert features["is_active_recently"] == 0
        assert features["days_since_active"] > 180

    def test_missing_active_date(self):
        """Missing last_active_date should return -1 for days_since."""
        record = _make_candidate(
            redrob_signals=RedrobSignals(last_active_date=""),
        )
        features = self.extractor.extract(record)
        assert features["days_since_active"] == -1
        assert features["is_active_recently"] == 0

    def test_github_presence(self):
        """GitHub score >= 0 means has_github=True."""
        record = _make_candidate()
        features = self.extractor.extract(record)
        assert features["has_github"] == 1
        assert features["github_activity_score"] == 72.0

    def test_no_github(self):
        """GitHub score -1 means no linked GitHub."""
        record = _make_candidate(
            redrob_signals=RedrobSignals(github_activity_score=-1.0),
        )
        features = self.extractor.extract(record)
        assert features["has_github"] == 0

    def test_notice_period(self):
        """Notice period ≤30 days is OK."""
        record = _make_candidate()
        features = self.extractor.extract(record)
        assert features["notice_period_ok"] == 1

        record2 = _make_candidate(
            redrob_signals=RedrobSignals(notice_period_days=90),
        )
        features2 = self.extractor.extract(record2)
        assert features2["notice_period_ok"] == 0

    def test_verification_flags(self):
        """Verification booleans should be 0/1 ints."""
        record = _make_candidate()
        features = self.extractor.extract(record)
        assert features["verified_email"] == 1
        assert features["verified_phone"] == 1
        assert features["linkedin_connected"] == 1

    def test_preferred_work_mode_encoding(self):
        """Preferred work mode should be encoded as int."""
        record = _make_candidate()
        features = self.extractor.extract(record)
        # "hybrid" → 1
        assert features["preferred_work_mode"] == 1


# ══════════════════════════════════════════════════════════════════════════════
# Career Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestCareerFeatureExtractor:
    """Tests for career feature extraction and title matching."""

    def setup_method(self):
        self.extractor = CareerFeatureExtractor()

    def test_experience_in_range(self):
        """Experience between 5-9 years should be flagged."""
        record = _make_candidate()
        features = self.extractor.extract(record)
        assert features["experience_in_range"] == 1

    def test_experience_out_of_range(self):
        """Experience outside 5-9 years should not be flagged."""
        record = _make_candidate(
            profile=Profile(years_of_experience=3.0),
        )
        features = self.extractor.extract(record)
        assert features["experience_in_range"] == 0

    def test_title_match_senior_ai_engineer(self):
        """'Senior AI Engineer' should score highly."""
        record = _make_candidate()
        features = self.extractor.extract(record)
        assert features["title_match_score"] >= 0.7

    def test_title_match_marketing_manager(self):
        """'Marketing Manager' should score 0."""
        record = _make_candidate(
            profile=Profile(current_title="Marketing Manager"),
        )
        features = self.extractor.extract(record)
        assert features["title_match_score"] == 0.0
        assert features["title_is_non_relevant"] == 1

    def test_title_is_ai_ml(self):
        """AI/ML titles should be flagged."""
        record = _make_candidate()
        features = self.extractor.extract(record)
        assert features["title_is_ai_ml"] == 1

    def test_career_progression(self):
        """Career with progression should score well."""
        record = _make_candidate(
            career_history=[
                CareerEntry(title="Junior ML Engineer", duration_months=24),
                CareerEntry(title="ML Engineer", duration_months=24),
                CareerEntry(title="Senior AI Engineer", duration_months=24, is_current=True),
            ],
        )
        features = self.extractor.extract(record)
        assert features["career_progression_score"] >= 0.9

    def test_no_career_progression(self):
        """Career without clear titles gets neutral score."""
        record = _make_candidate(
            career_history=[
                CareerEntry(title="Developer", duration_months=24),
            ],
        )
        features = self.extractor.extract(record)
        # Single entry → neutral 0.5
        assert features["career_progression_score"] == 0.5

    def test_total_career_months(self):
        """Total career months should sum correctly."""
        record = _make_candidate()
        features = self.extractor.extract(record)
        assert features["total_career_months"] == 42 + 30  # 72

    def test_experience_consistency(self):
        """Consistency ratio should be years_exp / (total_months/12)."""
        record = _make_candidate()
        features = self.extractor.extract(record)
        expected = 7.0 / (72 / 12.0)
        assert abs(features["experience_consistency"] - expected) < 0.01


# ══════════════════════════════════════════════════════════════════════════════
# Semantic Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestSemanticFeatureExtractor:
    """Tests for semantic / skill features."""

    def setup_method(self):
        self.extractor = SemanticFeatureExtractor()

    def test_ai_keyword_count(self):
        """Should count AI-related skills."""
        record = _make_candidate()
        features = self.extractor.extract(record)
        # Python, PyTorch, Machine Learning, NLP, Embeddings → 5
        assert features["ai_keyword_count"] == 5

    def test_no_ai_skills(self):
        """Candidate with no AI skills should have 0."""
        record = _make_candidate(
            skills=[
                SkillEntry(name="Excel", proficiency="expert", duration_months=60),
                SkillEntry(name="PowerPoint", proficiency="advanced", duration_months=48),
            ],
        )
        features = self.extractor.extract(record)
        assert features["ai_keyword_count"] == 0
        assert features["ai_skill_depth"] == 0.0

    def test_headline_relevance(self):
        """Headline with AI/ML should be relevant."""
        record = _make_candidate()
        features = self.extractor.extract(record)
        assert features["headline_relevance"] == 1

    def test_headline_not_relevant(self):
        """Headline without AI/ML should not be relevant."""
        record = _make_candidate(
            profile=Profile(headline="Marketing Expert and Sales Leader"),
        )
        features = self.extractor.extract(record)
        assert features["headline_relevance"] == 0


# ══════════════════════════════════════════════════════════════════════════════
# Education Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestEducationFeatureExtractor:
    """Tests for education features."""

    def setup_method(self):
        self.extractor = EducationFeatureExtractor()

    def test_tier_1_cs_degree(self):
        """IIT CS degree should be tier_1 and CS-related."""
        record = _make_candidate()
        features = self.extractor.extract(record)
        assert features["tier_1_education"] == 1
        assert features["best_education_tier"] == 4
        assert features["cs_related_field"] == 1
        assert features["highest_degree_level"] == 2  # B.Tech = bachelor = 2

    def test_no_education(self):
        """Candidate with no education entries."""
        record = _make_candidate(education=[])
        features = self.extractor.extract(record)
        assert features["highest_degree_level"] == 0
        assert features["cs_related_field"] == 0
        assert features["tier_1_education"] == 0

    def test_phd_level(self):
        """PhD should be level 4."""
        record = _make_candidate(
            education=[
                EducationEntry(degree="PhD", field_of_study="Machine Learning", tier="tier_1"),
            ],
        )
        features = self.extractor.extract(record)
        assert features["highest_degree_level"] == 4


# ══════════════════════════════════════════════════════════════════════════════
# Risk Feature Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestRiskFeatureExtractor:
    """Tests for risk / supplementary features."""

    def setup_method(self):
        self.extractor = RiskFeatureExtractor()

    def test_salary_and_certs(self):
        """Should extract salary range and cert count."""
        record = _make_candidate()
        features = self.extractor.extract(record)
        assert features["salary_expectation_min"] == 25.0
        assert features["salary_expectation_max"] == 35.0
        assert features["certification_count"] == 1
        assert features["language_count"] == 2

    def test_skill_assessments(self):
        """Should detect assessments and compute average."""
        record = _make_candidate()
        features = self.extractor.extract(record)
        assert features["has_skill_assessments"] == 1
        assert features["avg_assessment_score"] == pytest.approx(90.0, abs=0.1)


# ══════════════════════════════════════════════════════════════════════════════
# Behavioral Analyzer Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestBehavioralAnalyzer:
    """Tests for the BehavioralAnalyzer multiplier computation."""

    def setup_method(self):
        self.analyzer = BehavioralAnalyzer()

    def test_good_candidate_high_multiplier(self):
        """Active, responsive, open-to-work → high multiplier."""
        record = _make_candidate()
        result = self.analyzer.analyze(record)
        assert result.behavioral_multiplier > 0.5
        assert result.response_factor > 0.5
        assert result.activity_factor == 1.0
        assert result.availability_factor == 1.0

    def test_inactive_not_open_to_work(self):
        """Inactive + not open to work → low multiplier."""
        record = _make_inactive_candidate()
        result = self.analyzer.analyze(record)
        # Low response (0.05→max(0.1,0.05)=0.1) × inactive (0.3) × not open (0.6) = 0.018
        assert result.behavioral_multiplier < 0.1

    def test_zero_response_rate(self):
        """Zero response rate → penalty factor of 0.2."""
        record = _make_candidate(
            redrob_signals=RedrobSignals(
                recruiter_response_rate=0.0,
                last_active_date="2026-06-10",
                open_to_work_flag=True,
            ),
        )
        result = self.analyzer.analyze(record)
        assert result.response_factor == 0.2

    def test_engagement_score_range(self):
        """Engagement score should be in [0, 100]."""
        record = _make_candidate()
        result = self.analyzer.analyze(record)
        assert 0.0 <= result.engagement_score <= 100.0

    def test_multiplier_bounds(self):
        """Multiplier must always be in [0.0, 1.0]."""
        for record in [_make_candidate(), _make_honeypot_candidate(), _make_inactive_candidate()]:
            result = self.analyzer.analyze(record)
            assert 0.0 <= result.behavioral_multiplier <= 1.0


# ══════════════════════════════════════════════════════════════════════════════
# Pipeline Integration Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestFeaturePipeline:
    """Integration tests for the full pipeline."""

    def test_pipeline_single_candidate(self):
        """Pipeline should produce features for one candidate."""
        pipeline = FeaturePipeline()
        candidates = [_make_candidate()]
        store = pipeline.run(candidates)
        assert store.candidate_count == 1
        assert store.feature_count > 30  # Should have many features

    def test_pipeline_multiple_candidates(self):
        """Pipeline should handle multiple candidates."""
        pipeline = FeaturePipeline()
        candidates = [
            _make_candidate(candidate_id="CAND_0000001"),
            _make_honeypot_candidate(),
            _make_inactive_candidate(),
        ]
        store = pipeline.run(candidates)
        assert store.candidate_count == 3

        # Verify honeypot has high score
        hp_features = store.get_features("CAND_HONEYPOT")
        assert hp_features is not None
        assert hp_features["honeypot_score"] > 0.4

    def test_pipeline_all_feature_names(self):
        """All declared feature names should appear in output."""
        pipeline = FeaturePipeline()
        store = pipeline.run([_make_candidate()])
        features = store.get_features("CAND_0000001")
        assert features is not None
        for name in pipeline.all_feature_names:
            assert name in features, f"Missing feature: {name}"

    def test_pipeline_returns_dataframe(self):
        """get_all() should return a valid DataFrame."""
        pipeline = FeaturePipeline()
        store = pipeline.run([_make_candidate()])
        df = store.get_all()
        assert len(df) == 1
        assert df.index.name == "candidate_id"


# ══════════════════════════════════════════════════════════════════════════════
# Feature Store Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestFeatureStore:
    """Tests for the FeatureStore persistence layer."""

    def test_add_and_get(self):
        """Add features and retrieve them."""
        store = FeatureStore()
        store.add_features("C1", {"a": 1, "b": 2.0})
        result = store.get_features("C1")
        assert result == {"a": 1, "b": 2.0}

    def test_get_missing(self):
        """Getting a missing candidate returns None."""
        store = FeatureStore()
        assert store.get_features("MISSING") is None

    def test_save_and_load(self, tmp_path):
        """Save to Parquet and load back."""
        store = FeatureStore()
        store.add_features("C1", {"x": 1.0, "y": 2.0})
        store.add_features("C2", {"x": 3.0, "y": 4.0})

        path = tmp_path / "test_store.parquet"
        store.save(path)
        assert path.exists()

        loaded = FeatureStore.load(path)
        assert loaded.candidate_count == 2
        assert loaded.get_features("C1")["x"] == 1.0
        assert loaded.get_features("C2")["y"] == 4.0

    def test_versioned_save(self, tmp_path):
        """Save with a version suffix."""
        store = FeatureStore()
        store.add_features("C1", {"a": 1})
        path = tmp_path / "features.parquet"
        saved_path = store.save(path, version="v2")
        assert "features_v2.parquet" in str(saved_path)
        assert saved_path.exists()

    def test_metadata(self):
        """Metadata should reflect store contents."""
        store = FeatureStore()
        store.add_features("C1", {"x": 1, "y": 2})
        meta = store.metadata
        assert meta["candidate_count"] == 1
        assert "x" in meta["feature_names"]
