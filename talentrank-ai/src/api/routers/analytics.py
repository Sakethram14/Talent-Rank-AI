import time
from fastapi import APIRouter, Depends, HTTPException
from src.api.schemas.common import BaseResponse, ResponseMetadata
from src.api.schemas.analytics import DashboardSummary, DistributionData, HoneypotListResponse
from src.api.dependencies import get_session_manager
from src.api.services.analytics import AnalyticsService
from src.api.services.enrichment import RankingSessionManager

router = APIRouter(prefix="/analytics", tags=["analytics"])

def get_analytics_service(
    session_manager: RankingSessionManager = Depends(get_session_manager)
) -> AnalyticsService:
    return AnalyticsService(session_manager)

@router.get("/dashboard", response_model=BaseResponse[DashboardSummary])
def get_dashboard_summary(
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get high-level summary metrics for the recruiter dashboard."""
    start = time.time()
    try:
        summary = analytics_service.get_dashboard_summary()
        return BaseResponse(
            data=summary,
            metadata=ResponseMetadata(
                processing_time_ms=(time.time() - start) * 1000
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/distributions", response_model=BaseResponse[DistributionData])
def get_distributions(
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get histograms for experience, skills, education, etc."""
    start = time.time()
    try:
        dists = analytics_service.get_distributions()
        return BaseResponse(
            data=dists,
            metadata=ResponseMetadata(
                processing_time_ms=(time.time() - start) * 1000
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/honeypots", response_model=BaseResponse[HoneypotListResponse])
def get_honeypots(
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get the Wall of Shame (all identified honeypots)."""
    start = time.time()
    try:
        honeypots = analytics_service.get_honeypots()
        return BaseResponse(
            data=honeypots,
            metadata=ResponseMetadata(
                processing_time_ms=(time.time() - start) * 1000,
                total_results=len(honeypots.honeypots)
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
