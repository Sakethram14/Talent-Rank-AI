from fastapi import APIRouter
from src.api.schemas.common import BaseResponse
from src.api.config_manager import config_manager, RankingWeightsUpdate
from pydantic import BaseModel

router = APIRouter(prefix="/config", tags=["config"])

class ConfigResponse(BaseModel):
    ranking_weights: dict[str, float]

@router.get("", response_model=BaseResponse[ConfigResponse])
def get_config():
    """Get the current active configuration weights."""
    return BaseResponse(
        data=ConfigResponse(
            ranking_weights=config_manager.get_active_ranking_weights()
        )
    )

@router.post("/weights", response_model=BaseResponse[ConfigResponse])
def update_ranking_weights(updates: RankingWeightsUpdate):
    """Update ranking weights safely at runtime (for Sandbox)."""
    new_weights = config_manager.update_ranking_weights(updates)
    return BaseResponse(
        data=ConfigResponse(
            ranking_weights=new_weights
        )
    )
