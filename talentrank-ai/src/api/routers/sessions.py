import time
from fastapi import APIRouter, Depends, HTTPException
from src.api.schemas.common import BaseResponse, ResponseMetadata
from src.api.schemas.session import RankingSessionSchema
from src.api.dependencies import get_session_manager

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.get("/active", response_model=BaseResponse[RankingSessionSchema])
def get_active_session(session_manager = Depends(get_session_manager)):
    """Retrieve the most recently generated active ranking session."""
    start = time.time()
    session = session_manager.get_active_session()
    if not session:
        raise HTTPException(status_code=404, detail="No active ranking session found. Please perform an analysis first.")
        
    return BaseResponse(
        data=session,
        metadata=ResponseMetadata(
            processing_time_ms=(time.time() - start) * 1000,
            total_results=1
        )
    )

@router.get("/{session_id}", response_model=BaseResponse[RankingSessionSchema])
def get_session_by_id(session_id: str, session_manager = Depends(get_session_manager)):
    """Retrieve a historical ranking session by its UUID."""
    start = time.time()
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Ranking session {session_id} not found.")
        
    return BaseResponse(
        data=session,
        metadata=ResponseMetadata(
            processing_time_ms=(time.time() - start) * 1000,
            total_results=1
        )
    )
