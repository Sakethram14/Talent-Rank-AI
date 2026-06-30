from typing import Any
from pydantic import BaseModel, Field

class RankingFilter(BaseModel):
    """Optional filters for ranking requests."""
    min_experience_years: float | None = None
    max_experience_years: float | None = None
    locations: list[str] | None = None
    exclude_honeypots: bool = False

class RankingRequest(BaseModel):
    """Request payload for ranking candidates."""
    job_description: str
    top_k: int = Field(100, ge=1, le=1000)
    filters: RankingFilter | None = None

class RankedCandidateSchema(BaseModel):
    """Schema for a ranked candidate."""
    candidate_id: str
    final_score: float
    retrieval_score: float
    feature_score: float
    behavioral_multiplier: float
    is_honeypot: bool
    
class RankingResponse(BaseModel):
    """Data payload for ranking results."""
    candidates: list[RankedCandidateSchema]

class EvidenceItemSchema(BaseModel):
    signal_name: str
    value: Any
    impact: str
    weight: float
    description: str

class CandidateEvidenceSchema(BaseModel):
    """Schema for explainability evidence."""
    candidate_id: str
    overall_score: float = 0.0
    positive_signals: list[EvidenceItemSchema]
    negative_signals: list[EvidenceItemSchema]
    neutral_signals: list[EvidenceItemSchema]
    behavioral_summary: dict[str, Any]
    career_summary: dict[str, Any]
    risk_flags: list[str]
    is_honeypot: bool
    honeypot_reasons: list[str]
