from typing import Any
from src.api.schemas.analytics import (
    DashboardSummary, DistributionData, HistogramBin, HoneypotCandidateSchema, HoneypotListResponse,
    RecentRanking, PerformanceMetrics
)
from src.api.services.enrichment import RankingSessionManager

class AnalyticsService:
    def __init__(self, session_manager: RankingSessionManager):
        self.session_manager = session_manager

    def get_dashboard_summary(self) -> DashboardSummary:
        session = self.session_manager.get_active_session()
        
        # Base empty state
        if not session or not session.candidates:
            return DashboardSummary(
                total_candidates=0,
                ai_candidates=0,
                open_to_work=0,
                avg_experience=0.0,
                honeypots_detected=0,
                recent_rankings=[],
                performance=PerformanceMetrics(latency_ms=0, throughput_qps=0)
            )
            
        candidates = session.candidates
        total = len(candidates)
        ai_cands = sum(1 for c in candidates if "AI" in c.current_role or "Machine Learning" in c.current_role or c.overall_score and c.overall_score > 70)
        open_work = sum(1 for c in candidates if c.availability == "open_to_work")
        total_exp = sum(c.years_experience for c in candidates)
        honeypots = sum(1 for c in candidates if c.honeypot)
        
        return DashboardSummary(
            total_candidates=total,
            ai_candidates=ai_cands,
            open_to_work=open_work,
            avg_experience=round(total_exp / total if total else 0.0, 1),
            honeypots_detected=honeypots,
            recent_rankings=[
                RecentRanking(
                    id=session.session_id,
                    jd_title=session.job_description[:50] + "..." if session.job_description else "AI Engineer",
                    candidates=total,
                    ts=session.timestamp
                )
            ],
            performance=PerformanceMetrics(
                latency_ms=120, # Mocked metric for now
                throughput_qps=8
            )
        )

    def get_distributions(self) -> DistributionData:
        session = self.session_manager.get_active_session()
        if not session or not session.candidates:
            return DistributionData(skills=[], experience=[], company_size=[], education=[])
            
        candidates = session.candidates
        
        # Experience distribution
        exp_bins = {"0-3 yrs": 0, "4-7 yrs": 0, "8-12 yrs": 0, "13+ yrs": 0}
        for c in candidates:
            if c.years_experience <= 3:
                exp_bins["0-3 yrs"] += 1
            elif c.years_experience <= 7:
                exp_bins["4-7 yrs"] += 1
            elif c.years_experience <= 12:
                exp_bins["8-12 yrs"] += 1
            else:
                exp_bins["13+ yrs"] += 1
                
        experience_dist = [HistogramBin(label=k, count=v) for k, v in exp_bins.items() if v > 0]
        
        # Education distribution
        edu_bins = {"Tier 1": 0, "Tier 2": 0, "Tier 3": 0, "Tier 4": 0, "Unknown": 0}
        for c in candidates:
            tier = "Unknown"
            if c.education:
                best_degree = c.education[0].degree.lower()
                if "phd" in best_degree or "doctorate" in best_degree:
                    tier = "Tier 1"
                elif "master" in best_degree:
                    tier = "Tier 2"
                elif "bachelor" in best_degree:
                    tier = "Tier 3"
                else:
                    tier = "Tier 4"
            edu_bins[tier] += 1
        education_dist = [HistogramBin(label=k, count=v) for k, v in edu_bins.items() if v > 0]
        
        # Company size mock (from roles)
        company_dist = [
            HistogramBin(label="Product/Startup", count=int(len(candidates) * 0.6)),
            HistogramBin(label="Consulting/Other", count=int(len(candidates) * 0.4))
        ]
        
        # Skills dist
        skills_bins = {"High AI Skills (10+)": 0, "Medium AI Skills (4-9)": 0, "Low AI Skills (0-3)": 0}
        for c in candidates:
            ai_skills = len(c.matched_skills)
            if ai_skills >= 10:
                skills_bins["High AI Skills (10+)"] += 1
            elif ai_skills >= 4:
                skills_bins["Medium AI Skills (4-9)"] += 1
            else:
                skills_bins["Low AI Skills (0-3)"] += 1
        skills_dist = [HistogramBin(label=k, count=v) for k, v in skills_bins.items() if v > 0]

        return DistributionData(
            skills=skills_dist,
            experience=experience_dist,
            company_size=company_dist,
            education=education_dist
        )
        
    def get_honeypots(self) -> HoneypotListResponse:
        session = self.session_manager.get_active_session()
        if not session or not session.candidates:
            return HoneypotListResponse(honeypots=[])
            
        honeypots = []
        for c in session.candidates:
            if c.honeypot:
                honeypots.append(HoneypotCandidateSchema(
                    candidate_id=str(c.id),
                    reasons=c.honeypot_reasons or ["Profile flagged by contradiction engine"],
                    honeypot_score=float(c.risk_score / 100.0) if c.risk_score is not None else 1.0
                ))
            
        return HoneypotListResponse(honeypots=honeypots)
