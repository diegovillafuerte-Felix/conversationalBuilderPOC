"""Common schemas used across all services."""

from typing import Any, Optional

from pydantic import BaseModel


class ServiceResponse(BaseModel):
    """Standard service response wrapper."""

    success: bool = True
    data: Optional[Any] = None
    error: Optional[str] = None
    error_code: Optional[str] = None


class ErrorDetail(BaseModel):
    """Error detail model."""

    error: str
    error_code: str
    details: Optional[dict] = None
