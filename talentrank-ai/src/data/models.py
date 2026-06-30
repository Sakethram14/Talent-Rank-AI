"""
Data models for TalentRank AI.

Lightweight typed representations of candidate records.
These are plain dataclasses (not Pydantic) for speed during
bulk processing of 100k records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CareerEntry:
    """A single career history entry."""
    company: str = ""
    title: str = ""
    start_date: str = ""
    end_date: Optional[str] = None
    duration_months: int = 0
    is_current: bool = False
    industry: str = ""
    company_size: str = ""
    description: str = ""


@dataclass
class EducationEntry:
    """A single education entry."""
    institution: str = ""
    degree: str = ""
    field_of_study: str = ""
    start_year: int = 0
    end_year: int = 0
    grade: Optional[str] = None
    tier: str = "unknown"


@dataclass
class SkillEntry:
    """A single skill entry."""
    name: str = ""
    proficiency: str = ""
    endorsements: int = 0
    duration_months: int = 0


@dataclass
class CertificationEntry:
    """A single certification entry."""
    name: str = ""
    issuer: str = ""
    year: int = 0


@dataclass
class LanguageEntry:
    """A single language entry."""
    language: str = ""
    proficiency: str = ""


@dataclass
class SalaryRange:
    """Expected salary range in INR LPA."""
    min_lpa: float = 0.0
    max_lpa: float = 0.0


@dataclass
class RedrobSignals:
    """Behavioral signals from the Redrob platform."""
    profile_completeness_score: float = 0.0
    signup_date: str = ""
    last_active_date: str = ""
    open_to_work_flag: bool = False
    profile_views_received_30d: int = 0
    applications_submitted_30d: int = 0
    recruiter_response_rate: float = 0.0
    avg_response_time_hours: float = 0.0
    skill_assessment_scores: dict[str, float] = field(default_factory=dict)
    connection_count: int = 0
    endorsements_received: int = 0
    notice_period_days: int = 0
    expected_salary_range: SalaryRange = field(default_factory=SalaryRange)
    preferred_work_mode: str = ""
    willing_to_relocate: bool = False
    github_activity_score: float = -1.0
    search_appearance_30d: int = 0
    saved_by_recruiters_30d: int = 0
    interview_completion_rate: float = 0.0
    offer_acceptance_rate: float = -1.0
    verified_email: bool = False
    verified_phone: bool = False
    linkedin_connected: bool = False


@dataclass
class Profile:
    """Candidate profile information."""
    anonymized_name: str = ""
    headline: str = ""
    summary: str = ""
    location: str = ""
    country: str = ""
    years_of_experience: float = 0.0
    current_title: str = ""
    current_company: str = ""
    current_company_size: str = ""
    current_industry: str = ""


@dataclass
class CandidateRecord:
    """
    Complete typed representation of a single candidate.

    This is the canonical internal format used throughout the pipeline.
    """
    candidate_id: str = ""
    profile: Profile = field(default_factory=Profile)
    career_history: list[CareerEntry] = field(default_factory=list)
    education: list[EducationEntry] = field(default_factory=list)
    skills: list[SkillEntry] = field(default_factory=list)
    certifications: list[CertificationEntry] = field(default_factory=list)
    languages: list[LanguageEntry] = field(default_factory=list)
    redrob_signals: RedrobSignals = field(default_factory=RedrobSignals)

    # Metadata flags set by the pipeline
    is_honeypot: bool = False
    honeypot_reasons: list[str] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)
    is_valid: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CandidateRecord:
        """
        Parse a raw dict (from JSONL) into a typed CandidateRecord.

        This is the single point of conversion from untyped JSON to
        typed internal representation.
        """
        profile_data = data.get("profile", {})
        profile = Profile(
            anonymized_name=profile_data.get("anonymized_name", ""),
            headline=profile_data.get("headline", ""),
            summary=profile_data.get("summary", ""),
            location=profile_data.get("location", ""),
            country=profile_data.get("country", ""),
            years_of_experience=float(profile_data.get("years_of_experience", 0)),
            current_title=profile_data.get("current_title", ""),
            current_company=profile_data.get("current_company", ""),
            current_company_size=profile_data.get("current_company_size", ""),
            current_industry=profile_data.get("current_industry", ""),
        )

        career_history = [
            CareerEntry(
                company=c.get("company", ""),
                title=c.get("title", ""),
                start_date=c.get("start_date", ""),
                end_date=c.get("end_date"),
                duration_months=int(c.get("duration_months", 0)),
                is_current=bool(c.get("is_current", False)),
                industry=c.get("industry", ""),
                company_size=c.get("company_size", ""),
                description=c.get("description", ""),
            )
            for c in data.get("career_history", [])
        ]

        education = [
            EducationEntry(
                institution=e.get("institution", ""),
                degree=e.get("degree", ""),
                field_of_study=e.get("field_of_study", ""),
                start_year=int(e.get("start_year", 0)),
                end_year=int(e.get("end_year", 0)),
                grade=e.get("grade"),
                tier=e.get("tier", "unknown"),
            )
            for e in data.get("education", [])
        ]

        skills = [
            SkillEntry(
                name=s.get("name", ""),
                proficiency=s.get("proficiency", ""),
                endorsements=int(s.get("endorsements", 0)),
                duration_months=int(s.get("duration_months", 0)),
            )
            for s in data.get("skills", [])
        ]

        certifications = [
            CertificationEntry(
                name=c.get("name", ""),
                issuer=c.get("issuer", ""),
                year=int(c.get("year", 0)),
            )
            for c in data.get("certifications", [])
        ]

        languages = [
            LanguageEntry(
                language=l.get("language", ""),
                proficiency=l.get("proficiency", ""),
            )
            for l in data.get("languages", [])
        ]

        signals_data = data.get("redrob_signals", {})
        salary = signals_data.get("expected_salary_range_inr_lpa", {})
        redrob_signals = RedrobSignals(
            profile_completeness_score=float(signals_data.get("profile_completeness_score", 0)),
            signup_date=signals_data.get("signup_date", ""),
            last_active_date=signals_data.get("last_active_date", ""),
            open_to_work_flag=bool(signals_data.get("open_to_work_flag", False)),
            profile_views_received_30d=int(signals_data.get("profile_views_received_30d", 0)),
            applications_submitted_30d=int(signals_data.get("applications_submitted_30d", 0)),
            recruiter_response_rate=float(signals_data.get("recruiter_response_rate", 0)),
            avg_response_time_hours=float(signals_data.get("avg_response_time_hours", 0)),
            skill_assessment_scores=dict(signals_data.get("skill_assessment_scores", {})),
            connection_count=int(signals_data.get("connection_count", 0)),
            endorsements_received=int(signals_data.get("endorsements_received", 0)),
            notice_period_days=int(signals_data.get("notice_period_days", 0)),
            expected_salary_range=SalaryRange(
                min_lpa=float(salary.get("min", 0)),
                max_lpa=float(salary.get("max", 0)),
            ),
            preferred_work_mode=signals_data.get("preferred_work_mode", ""),
            willing_to_relocate=bool(signals_data.get("willing_to_relocate", False)),
            github_activity_score=float(signals_data.get("github_activity_score", -1)),
            search_appearance_30d=int(signals_data.get("search_appearance_30d", 0)),
            saved_by_recruiters_30d=int(signals_data.get("saved_by_recruiters_30d", 0)),
            interview_completion_rate=float(signals_data.get("interview_completion_rate", 0)),
            offer_acceptance_rate=float(signals_data.get("offer_acceptance_rate", -1)),
            verified_email=bool(signals_data.get("verified_email", False)),
            verified_phone=bool(signals_data.get("verified_phone", False)),
            linkedin_connected=bool(signals_data.get("linkedin_connected", False)),
        )

        return cls(
            candidate_id=data.get("candidate_id", ""),
            profile=profile,
            career_history=career_history,
            education=education,
            skills=skills,
            certifications=certifications,
            languages=languages,
            redrob_signals=redrob_signals,
        )
