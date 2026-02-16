"""Common schemas used across all services."""

from typing import Any

from pydantic import BaseModel


class ServiceResponse(BaseModel):
    """Standard service response wrapper."""

    success: bool = True
    data: Any | None = None
    error: str | None = None
    error_code: str | None = None


class ErrorDetail(BaseModel):
    """Error detail model."""

    error: str
    error_code: str
    details: dict | None = None
