from fastapi import APIRouter
from src.api.schemas.common import BaseResponse
from pydantic import BaseModel

router = APIRouter(tags=["system"])

class HealthResponse(BaseModel):
    status: str
    version: str

@router.get("/health", response_model=BaseResponse[HealthResponse])
def health_check():
    """Basic health check endpoint."""
    return BaseResponse(
        data=HealthResponse(status="ok", version="1.0.0")
    )

@router.get("/status", response_model=BaseResponse[HealthResponse])
def status_check():
    """Detailed status check for the ML services (mocked for now)."""
    return BaseResponse(
        data=HealthResponse(status="all_systems_operational", version="1.0.0")
    )
