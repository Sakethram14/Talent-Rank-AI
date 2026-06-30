import time
from fastapi import APIRouter, Depends, HTTPException
from src.api.schemas.common import BaseResponse, ResponseMetadata
from src.api.schemas.ranking import RankingRequest
from src.api.schemas.session import RankingSessionSchema
from src.api.dependencies import get_feature_store, get_ranker, get_embedding_generator, get_hybrid_retriever, get_session_manager
from src.api.services.ranking import RankingService
from src.api.config_manager import config_manager


router = APIRouter(prefix="/candidates", tags=["ranking"])

def get_ranking_service(
    embedding_generator=Depends(get_embedding_generator),
    hybrid_retriever=Depends(get_hybrid_retriever),
    feature_store=Depends(get_feature_store),
    ranker=Depends(get_ranker)
) -> RankingService:
    return RankingService(embedding_generator, hybrid_retriever, feature_store, ranker)

@router.post("/rank", response_model=BaseResponse[RankingSessionSchema])
def rank_candidates(
    request: RankingRequest,
    ranking_service: RankingService = Depends(get_ranking_service),
    session_manager = Depends(get_session_manager),
    feature_store = Depends(get_feature_store)
):
    """Rank candidates for a job description and create a shared session."""
    start = time.time()
    try:
        # Get active weights from config manager
        weights = config_manager.get_active_ranking_weights()
        
        ranked = ranking_service.rank_candidates(
            job_description=request.job_description,
            top_k=request.top_k,
            filters=request.filters,
            custom_weights=weights
        )
        
        # Create session with the enriched candidates and metadata
        session = session_manager.create_session(
            job_description=request.job_description,
            ranked_candidates=ranked,
            feature_store_df=feature_store.get_all()
        )
        
        return BaseResponse(
            data=session,
            metadata=ResponseMetadata(
                processing_time_ms=(time.time() - start) * 1000,
                total_results=len(session.candidates)
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

