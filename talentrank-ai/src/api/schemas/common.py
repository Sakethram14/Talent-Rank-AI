from typing import Any, Generic, TypeVar, Optional
from pydantic import BaseModel, Field

T = TypeVar('T')

class ResponseMetadata(BaseModel):
    """Metadata included in every API response."""
    processing_time_ms: float = 0.0
    total_results: int | None = None
    version: str = "1.0.0"

class ErrorDetail(BaseModel):
    """Detailed error information."""
    code: str
    message: str
    details: Optional[Any] = None

class BaseResponse(BaseModel, Generic[T]):
    """Standardized API response wrapper."""
    data: Optional[T] = None
    metadata: ResponseMetadata = Field(default_factory=ResponseMetadata)
    errors: list[ErrorDetail] = Field(default_factory=list)
    success: bool = True

class ErrorResponse(BaseResponse[None]):
    """Standardized error response."""
    success: bool = False
