import time
from fastapi import APIRouter, Depends, HTTPException
from src.api.schemas.common import BaseResponse, ResponseMetadata
from src.api.schemas.ranking import CandidateEvidenceSchema
from src.api.schemas.session import CandidateEnrichedSchema
from src.api.dependencies import get_feature_store, get_evidence_collector, get_session_manager, get_enrichment_layer
from src.api.services.explainability import ExplainabilityService
from src.features.store import FeatureStore

router = APIRouter(prefix="/candidates", tags=["explainability"])

def get_explainability_service(
    evidence_collector=Depends(get_evidence_collector)
) -> ExplainabilityService:
    return ExplainabilityService(evidence_collector)

@router.get("/{candidate_id}/evidence", response_model=BaseResponse[CandidateEvidenceSchema])
def get_candidate_evidence(
    candidate_id: str,
    explainability_service: ExplainabilityService = Depends(get_explainability_service),
    feature_store: FeatureStore = Depends(get_feature_store)
):
    """Get structured evidence for a candidate's ranking."""
    start = time.time()
    try:
        # Get feature scores for this candidate
        try:
            feature_scores = feature_store.get_features(candidate_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Candidate not found in feature store")
            
        evidence = explainability_service.get_evidence(candidate_id, feature_scores)
        
        return BaseResponse(
            data=evidence,
            metadata=ResponseMetadata(
                processing_time_ms=(time.time() - start) * 1000,
                total_results=1
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{candidate_id}", response_model=BaseResponse[CandidateEnrichedSchema])
def get_candidate_profile(
    candidate_id: str,
    session_manager = Depends(get_session_manager),
    enrichment_layer = Depends(get_enrichment_layer),
    feature_store = Depends(get_feature_store)
):
    """Retrieve the fully enriched candidate profile, prioritizing the active ranking session."""
    start = time.time()
    try:
        # 1. Search the active session first
        active_session = session_manager.get_active_session()
        if active_session:
            for c in active_session.candidates:
                if c.id == candidate_id:
                    return BaseResponse(
                        data=c,
                        metadata=ResponseMetadata(
                            processing_time_ms=(time.time() - start) * 1000,
                            total_results=1
                        )
                    )
                    
        # 2. Fallback to candidate repository and enrich without ranking scores
        # Load features from store if they exist
        try:
            features = feature_store.get_features(candidate_id)
        except KeyError:
            features = {}
            
        enriched = enrichment_layer.enrich(ranked=None, feature_scores=features, candidate_id=candidate_id)
        if not enriched:
            raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found in database.")
            
        return BaseResponse(
            data=enriched,
            metadata=ResponseMetadata(
                processing_time_ms=(time.time() - start) * 1000,
                total_results=1
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

