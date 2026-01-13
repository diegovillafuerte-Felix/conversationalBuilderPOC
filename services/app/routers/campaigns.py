"""Campaigns service API router."""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.services.campaigns import CampaignsService
from app.schemas.common import ServiceResponse


router = APIRouter(prefix="/campaigns", tags=["campaigns"])

# Singleton service instance
_service: Optional[CampaignsService] = None


def get_service() -> CampaignsService:
    """Get or create service instance."""
    global _service
    if _service is None:
        _service = CampaignsService()
    return _service


# ==================== Request Schemas ====================


class RecordImpressionRequest(BaseModel):
    """Request to record a campaign impression."""
    campaign_id: str
    context: str
    converted: bool = False


# ==================== Campaign Endpoints ====================


@router.get("/active")
async def get_active_campaigns(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get currently active campaigns."""
    service = get_service()
    result = service.get_active_campaigns(user_id=x_user_id)
    return ServiceResponse(data={"campaigns": result})


@router.get("/{campaign_id}")
async def get_campaign_by_id(
    campaign_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get a specific campaign by ID."""
    service = get_service()
    result = service.get_campaign_by_id(campaign_id=campaign_id)
    if not result:
        raise HTTPException(status_code=404, detail={"error": "CAMPAIGN_NOT_FOUND"})
    return ServiceResponse(data=result)


@router.get("/{campaign_id}/eligibility")
async def check_user_eligibility(
    campaign_id: str,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Check if user is eligible for a campaign."""
    service = get_service()
    result = service.check_user_eligibility(user_id=x_user_id, campaign_id=campaign_id)
    return ServiceResponse(data=result)


@router.get("/by-context")
async def get_campaigns_for_context(
    context: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get campaigns matching a specific context."""
    service = get_service()
    result = service.get_campaigns_for_context(context=context, user_id=x_user_id)
    return ServiceResponse(data={"campaigns": result})


# ==================== Impression Endpoints ====================


@router.post("/impressions")
async def record_campaign_impression(
    request: RecordImpressionRequest,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Record a campaign impression."""
    service = get_service()
    result = service.record_campaign_impression(
        user_id=x_user_id,
        campaign_id=request.campaign_id,
        context=request.context,
        converted=request.converted,
    )
    return ServiceResponse(data=result)


@router.get("/history")
async def get_user_campaign_history(
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get user's campaign impression and conversion history."""
    service = get_service()
    result = service.get_user_campaign_history(user_id=x_user_id)
    return ServiceResponse(data=result)
