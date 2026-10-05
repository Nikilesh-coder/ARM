"""
ReportForge AI - API Response Conventions
Consistent response models and envelope helpers.
"""

from typing import Generic, TypeVar, Optional, Any, Dict
from pydantic import BaseModel

T = TypeVar("T")


class ResponseMeta(BaseModel):
    page: Optional[int] = None
    page_size: Optional[int] = None
    total_count: Optional[int] = None
    extra: Optional[Dict[str, Any]] = None


class ApiResponse(BaseModel, Generic[T]):
    """Standardized top-level API envelope."""
    success: bool = True
    data: T
    message: Optional[str] = None
    meta: Optional[ResponseMeta] = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ApiErrorResponse(BaseModel):
    """Standardized error envelope."""
    success: bool = False
    error: ErrorDetail


def envelope(data: T, message: Optional[str] = None, meta: Optional[ResponseMeta] = None) -> ApiResponse[T]:
    """Helper to wrap data in standard envelope."""
    return ApiResponse(success=True, data=data, message=message, meta=meta)
