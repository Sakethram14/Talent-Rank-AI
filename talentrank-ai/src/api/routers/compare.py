import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from src.api.schemas.common import BaseResponse, ResponseMetadata
from src.api.schemas.session import CandidateEnrichedSchema
from src.api.dependencies import get_feature_store, get_session_manager, get_enrichment_layer
from src.features.store import FeatureStore

router = APIRouter(prefix="/candidates", tags=["compare"])

class CompareRequest(BaseModel):
    candidate_ids: List[str]

@router.post("/compare", response_model=BaseResponse[List[CandidateEnrichedSchema]])
def compare_candidates(
    request: CompareRequest,
    session_manager = Depends(get_session_manager),
    enrichment_layer = Depends(get_enrichment_layer),
    feature_store: FeatureStore = Depends(get_feature_store)
):
    """Compare multiple candidates side-by-side using their full enriched profiles."""
    start = time.time()
    
    if len(request.candidate_ids) < 2 or len(request.candidate_ids) > 5:
        raise HTTPException(status_code=400, detail="Please provide between 2 and 5 candidates to compare.")
        
    try:
        results = []
        active_session = session_manager.get_active_session()
        
        for cid in request.candidate_ids:
            found = False
            # Try active session first
            if active_session:
                for c in active_session.candidates:
                    if c.id == cid:
                        results.append(c)
                        found = True
                        break
                        
            if not found:
                # Fallback to repository
                try:
                    features = feature_store.get_features(cid)
                except KeyError:
                    features = {}
                    
                enriched = enrichment_layer.enrich(ranked=None, feature_scores=features, candidate_id=cid)
                if not enriched:
                    raise HTTPException(status_code=404, detail=f"Candidate {cid} not found in database.")
                results.append(enriched)
            
        return BaseResponse(
            data=results,
            metadata=ResponseMetadata(
                processing_time_ms=(time.time() - start) * 1000,
                total_results=len(results)
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
