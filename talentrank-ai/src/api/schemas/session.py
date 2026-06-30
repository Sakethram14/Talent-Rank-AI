from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class ScoreBreakdownSchema(BaseModel):
    semantic: float
    behavior: float
    career: float
    skill: float
    risk: float
    availability: float

class CareerEntrySchema(BaseModel):
    company: str
    role: str
    start: str
    end: Optional[str] = None
    highlights: Optional[List[str]] = None

class EducationEntrySchema(BaseModel):
    school: str
    degree: str
    year: int

class EvidenceObjectSchema(BaseModel):
    id: str
    type: str
    title: str
    detail: str
    weight: float
    source: Optional[str] = None

class CandidateEnrichedSchema(BaseModel):
    id: str
    name: str
    headline: str
    location: str
    years_experience: float
    current_company: str
    current_role: str
    avatar_seed: str
    overall_score: Optional[float] = None
    confidence: Optional[float] = None
    risk_score: Optional[float] = None
    scores: Optional[ScoreBreakdownSchema] = None
    matched_skills: List[str]
    missing_skills: List[str]
    all_skills: List[str]
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    risk_flags: Optional[List[str]] = None
    availability: str
    notice_period_days: int
    recommendation: Optional[str] = None
    recommendation_text: Optional[str] = None
    honeypot: bool = False
    honeypot_reasons: Optional[List[str]] = None
    hidden_gem_score: Optional[float] = None
    career: List[CareerEntrySchema]
    education: List[EducationEntrySchema]
    evidence: Optional[List[EvidenceObjectSchema]] = None

class RankingSessionSchema(BaseModel):
    session_id: str
    timestamp: str
    job_description: str
    total_pool: int
    candidates: List[CandidateEnrichedSchema]
    extracted: Dict[str, Any]
    analytics: Dict[str, Any]
    hidden_gems: List[CandidateEnrichedSchema]
    honeypots: List[CandidateEnrichedSchema]
