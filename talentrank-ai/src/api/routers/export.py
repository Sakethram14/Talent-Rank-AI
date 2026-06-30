from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from src.api.services.export import ExportService
from src.api.dependencies import get_session_manager
from src.api.services.enrichment import RankingSessionManager

router = APIRouter(prefix="/export", tags=["export"])

def get_export_service() -> ExportService:
    return ExportService()

@router.get("/csv", response_class=PlainTextResponse)
def export_hackathon_csv(
    session_manager: RankingSessionManager = Depends(get_session_manager),
    export_service: ExportService = Depends(get_export_service)
):
    """Generate and return the official submission CSV format from the active session."""
    try:
        active_session = session_manager.get_active_session()
        if not active_session or not active_session.candidates:
            raise HTTPException(status_code=400, detail="No active ranking session found. Please perform a search first.")
            
        # 1. Extract candidate IDs in their ranked order
        candidate_ids = [c.id for c in active_session.candidates]
        
        # 2. Generate CSV format
        csv_content = export_service.generate_hackathon_csv(candidate_ids)
        return PlainTextResponse(content=csv_content, media_type="text/csv")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
