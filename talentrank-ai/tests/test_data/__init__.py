"""
Unit tests for the data module (parser, validator, cleaner).
"""

import sys
import json
import tempfile
from pathlib import Path
from datetime import date

import pytest

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.data.models import CandidateRecord, Profile, CareerEntry, SkillEntry, RedrobSignals, SalaryRange, EducationEntry
from src.data.validator import CandidateValidator
from src.data.cleaner import CandidateCleaner
from src.data.parser import CandidateParser


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────

def make_valid_candidate(candidate_id: str = "CAND_0000001") -> dict:
    """Create a minimal valid candidate dict for testing."""
    return {
        "candidate_id": candidate_id,
        "profile": {
            "anonymized_name": "Test User",
            "headline": "Senior AI Engineer | Python, ML, NLP",
            "summary": "Experienced AI engineer with 7 years of building production ML systems.",
            "location": "Pune",
            "country": "India",
            "years_of_experience": 7.0,
            "current_title": "Senior AI Engineer",
            "current_company": "TechCorp",
            "current_company_size": "201-500",
            "current_industry": "Technology",
        },
        "career_history": [
            {
                "company": "TechCorp",
                "title": "Senior AI Engineer",
                "start_date": "2022-01-01",
                "end_date": None,
                "duration_months": 30,
                "is_current": True,
                "industry": "Technology",
                "company_size": "201-500",
                "description": "Building production ranking and retrieval systems.",
            },
            {
                "company": "DataCo",
                "title": "ML Engineer",
                "start_date": "2019-06-01",
                "end_date": "2021-12-31",
                "duration_months": 31,
                "is_current": False,
                "industry": "Technology",
                "company_size": "51-200",
                "description": "Developed NLP pipelines and vector search infrastructure.",
            },
        ],
        "education": [
            {
                "institution": "IIT Bombay",
                "degree": "B.Tech",
                "field_of_study": "Computer Science",
                "start_year": 2013,
                "end_year": 2017,
                "grade": "8.5 CGPA",
                "tier": "tier_1",
            }
        ],
        "skills": [
            {"name": "Python", "proficiency": "expert", "endorsements": 45, "duration_months": 84},
            {"name": "Machine Learning", "proficiency": "advanced", "endorsements": 30, "duration_months": 60},
            {"name": "PyTorch", "proficiency": "advanced", "endorsements": 20, "duration_months": 36},
            {"name": "FAISS", "proficiency": "intermediate", "endorsements": 10, "duration_months": 24},
        ],
        "certifications": [],
        "languages": [
            {"language": "English", "proficiency": "professional"},
            {"language": "Hindi", "proficiency": "native"},
        ],
        "redrob_signals": {
            "profile_completeness_score": 92.0,
            "signup_date": "2024-01-15",
            "last_active_date": "2026-06-10",
            "open_to_work_flag": True,
            "profile_views_received_30d": 45,
            "applications_submitted_30d": 3,
            "recruiter_response_rate": 0.76,
            "avg_response_time_hours": 12.5,
            "skill_assessment_scores": {"Python": 88.0, "Machine Learning": 75.0},
            "connection_count": 500,
            "endorsements_received": 120,
            "notice_period_days": 30,
            "expected_salary_range_inr_lpa": {"min": 25.0, "max": 40.0},
            "preferred_work_mode": "hybrid",
            "willing_to_relocate": True,
            "github_activity_score": 72.0,
            "search_appearance_30d": 150,
            "saved_by_recruiters_30d": 12,
            "interview_completion_rate": 0.90,
            "offer_acceptance_rate": 0.75,
            "verified_email": True,
            "verified_phone": True,
            "linkedin_connected": True,
        },
    }


def make_honeypot_candidate() -> dict:
    """Create a candidate with honeypot indicators."""
    data = make_valid_candidate("CAND_9999999")
    # Expert in 10 skills with 0 duration — classic honeypot
    data["skills"] = [
        {"name": f"Skill_{i}", "proficiency": "expert", "endorsements": 50, "duration_months": 0}
        for i in range(10)
    ]
    # Claimed 8 years but career adds up to 2 years
    data["profile"]["years_of_experience"] = 8.0
    data["career_history"] = [
        {
            "company": "NewStartup",
            "title": "AI Engineer",
            "start_date": "2025-01-01",
            "end_date": None,
            "duration_months": 18,
            "is_current": True,
            "industry": "Technology",
            "company_size": "1-10",
            "description": "Building AI systems.",
        },
    ]
    return data


# ──────────────────────────────────────────────────────────────────────
# Tests: CandidateRecord.from_dict
# ──────────────────────────────────────────────────────────────────────


class TestCandidateRecord:
    def test_from_dict_valid(self):
        data = make_valid_candidate()
        record = CandidateRecord.from_dict(data)
        assert record.candidate_id == "CAND_0000001"
        assert record.profile.current_title == "Senior AI Engineer"
        assert record.profile.years_of_experience == 7.0
        assert len(record.career_history) == 2
        assert len(record.skills) == 4
        assert record.redrob_signals.recruiter_response_rate == 0.76
        assert record.redrob_signals.expected_salary_range.min_lpa == 25.0

    def test_from_dict_missing_fields(self):
        """Parsing should not crash on missing optional fields."""
        data = {
            "candidate_id": "CAND_0000002",
            "profile": {
                "anonymized_name": "Minimal User",
                "headline": "",
                "summary": "",
                "location": "",
                "country": "",
                "years_of_experience": 0,
                "current_title": "",
                "current_company": "",
                "current_company_size": "",
                "current_industry": "",
            },
            "career_history": [],
            "education": [],
            "skills": [],
            "redrob_signals": {
                "profile_completeness_score": 0,
                "signup_date": "",
                "last_active_date": "",
                "open_to_work_flag": False,
                "profile_views_received_30d": 0,
                "applications_submitted_30d": 0,
                "recruiter_response_rate": 0,
                "avg_response_time_hours": 0,
                "skill_assessment_scores": {},
                "connection_count": 0,
                "endorsements_received": 0,
                "notice_period_days": 0,
                "expected_salary_range_inr_lpa": {"min": 0, "max": 0},
                "preferred_work_mode": "",
                "willing_to_relocate": False,
                "github_activity_score": -1,
                "search_appearance_30d": 0,
                "saved_by_recruiters_30d": 0,
                "interview_completion_rate": 0,
                "offer_acceptance_rate": -1,
                "verified_email": False,
                "verified_phone": False,
                "linkedin_connected": False,
            },
        }
        record = CandidateRecord.from_dict(data)
        assert record.candidate_id == "CAND_0000002"
        assert record.profile.years_of_experience == 0
        assert len(record.skills) == 0


# ──────────────────────────────────────────────────────────────────────
# Tests: CandidateValidator
# ──────────────────────────────────────────────────────────────────────


class TestCandidateValidator:
    def setup_method(self):
        from src.config.settings import reset_settings
        reset_settings()
        self.validator = CandidateValidator()

    def test_validate_valid_candidate(self):
        record = CandidateRecord.from_dict(make_valid_candidate())
        result = self.validator.validate(record)
        assert result.is_valid, f"Expected valid, got errors: {result.validation_errors}"

    def test_validate_invalid_candidate_id(self):
        data = make_valid_candidate()
        data["candidate_id"] = "INVALID_ID"
        record = CandidateRecord.from_dict(data)
        result = self.validator.validate(record)
        assert not result.is_valid
        assert any("candidate_id" in e for e in result.validation_errors)

    def test_validate_negative_experience(self):
        data = make_valid_candidate()
        data["profile"]["years_of_experience"] = -5
        record = CandidateRecord.from_dict(data)
        # The cleaner clamps to 0, but the validator catches -5 before cleaning
        result = self.validator.validate(record)
        assert any("years_of_experience" in e for e in result.validation_errors)

    def test_validate_invalid_proficiency(self):
        data = make_valid_candidate()
        data["skills"][0]["proficiency"] = "godlike"
        record = CandidateRecord.from_dict(data)
        result = self.validator.validate(record)
        assert any("proficiency" in e for e in result.validation_errors)

    def test_duplicate_detection(self):
        records = [
            CandidateRecord.from_dict(make_valid_candidate("CAND_0000001")),
            CandidateRecord.from_dict(make_valid_candidate("CAND_0000001")),
            CandidateRecord.from_dict(make_valid_candidate("CAND_0000002")),
        ]
        duplicates = self.validator.check_duplicates(records)
        assert "CAND_0000001" in duplicates
        assert len(duplicates) == 1


# ──────────────────────────────────────────────────────────────────────
# Tests: CandidateCleaner
# ──────────────────────────────────────────────────────────────────────


class TestCandidateCleaner:
    def setup_method(self):
        self.cleaner = CandidateCleaner(reference_date=date(2026, 6, 15))

    def test_clean_normalizes_text(self):
        data = make_valid_candidate()
        data["profile"]["headline"] = "  Senior  AI   Engineer  "
        record = CandidateRecord.from_dict(data)
        cleaned = self.cleaner.clean(record)
        assert cleaned.profile.headline == "Senior AI Engineer"

    def test_clean_clamps_experience(self):
        data = make_valid_candidate()
        data["profile"]["years_of_experience"] = -10
        record = CandidateRecord.from_dict(data)
        cleaned = self.cleaner.clean(record)
        assert cleaned.profile.years_of_experience == 0.0

    def test_clean_clamps_response_rate(self):
        data = make_valid_candidate()
        data["redrob_signals"]["recruiter_response_rate"] = 1.5
        record = CandidateRecord.from_dict(data)
        cleaned = self.cleaner.clean(record)
        assert cleaned.redrob_signals.recruiter_response_rate == 1.0

    def test_days_since_valid_date(self):
        ref = date(2026, 6, 15)
        days = CandidateCleaner.days_since("2026-06-10", ref)
        assert days == 5

    def test_days_since_invalid_date(self):
        ref = date(2026, 6, 15)
        days = CandidateCleaner.days_since("not-a-date", ref)
        assert days == -1


# ──────────────────────────────────────────────────────────────────────
# Tests: CandidateParser
# ──────────────────────────────────────────────────────────────────────


class TestCandidateParser:
    def test_parser_with_temp_file(self, tmp_path):
        """Test parsing from a temporary JSONL file."""
        jsonl_file = tmp_path / "test_candidates.jsonl"
        candidates = [make_valid_candidate(f"CAND_{i:07d}") for i in range(5)]
        with open(jsonl_file, "w", encoding="utf-8") as f:
            for c in candidates:
                f.write(json.dumps(c) + "\n")

        from src.config.settings import reset_settings
        reset_settings()

        parser = CandidateParser(filepath=jsonl_file)
        records = parser.load_all()
        assert len(records) == 5
        assert records[0].candidate_id == "CAND_0000000"
        assert records[4].candidate_id == "CAND_0000004"

    def test_parser_max_records(self, tmp_path):
        """Test that max_records limits output."""
        jsonl_file = tmp_path / "test_candidates.jsonl"
        candidates = [make_valid_candidate(f"CAND_{i:07d}") for i in range(10)]
        with open(jsonl_file, "w", encoding="utf-8") as f:
            for c in candidates:
                f.write(json.dumps(c) + "\n")

        from src.config.settings import reset_settings
        reset_settings()

        parser = CandidateParser(filepath=jsonl_file)
        records = parser.load_all(max_records=3)
        assert len(records) == 3
