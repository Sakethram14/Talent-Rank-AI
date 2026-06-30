from pydantic import BaseModel

class RecentRanking(BaseModel):
    id: str
    jd_title: str
    candidates: int
    ts: str

class PerformanceMetrics(BaseModel):
    latency_ms: int
    throughput_qps: int

class DashboardSummary(BaseModel):
    total_candidates: int
    ai_candidates: int
    open_to_work: int
    avg_experience: float
    honeypots_detected: int
    recent_rankings: list[RecentRanking]
    performance: PerformanceMetrics

class HistogramBin(BaseModel):
    label: str
    count: int

class DistributionData(BaseModel):
    skills: list[HistogramBin]
    experience: list[HistogramBin]
    company_size: list[HistogramBin]
    education: list[HistogramBin]

class HoneypotCandidateSchema(BaseModel):
    candidate_id: str
    reasons: list[str]
    honeypot_score: float

class HoneypotListResponse(BaseModel):
    honeypots: list[HoneypotCandidateSchema]
