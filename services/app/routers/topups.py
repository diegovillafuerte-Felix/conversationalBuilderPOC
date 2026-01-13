"""TopUps service API router."""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, AliasChoices

from app.services.topups import MockTopUpsService
from app.schemas.common import ServiceResponse


router = APIRouter(prefix="/topups", tags=["topups"])

# Service instances by language
_services: dict = {}


def get_service(language: str = "es") -> MockTopUpsService:
    """Get or create service instance for language."""
    if language not in _services:
        _services[language] = MockTopUpsService(language=language)
    return _services[language]


# ==================== Request Schemas ====================


class DetectCarrierRequest(BaseModel):
    """Request to detect carrier from phone number."""
    phone_number: str = Field(
        ...,
        validation_alias=AliasChoices("phoneNumber", "phone_number")
    )


class SendTopupRequest(BaseModel):
    """Request to send a top-up."""
    phone_number: str = Field(
        ...,
        validation_alias=AliasChoices("phoneNumber", "phone_number")
    )
    carrier_id: str = Field(
        ...,
        validation_alias=AliasChoices("carrierId", "carrier_id")
    )
    amount: float = Field(gt=0)
    payment_method_id: str = Field(
        default="pm_default",
        validation_alias=AliasChoices("paymentMethodId", "payment_method_id")
    )


# ==================== Carrier Endpoints ====================


@router.get("/carriers")
async def get_carriers(
    country: str = "MX",
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get available carriers for a country."""
    service = get_service(accept_language)
    result = service.get_carriers(country=country)
    return ServiceResponse(data=result)


@router.get("/carriers/{carrier_id}")
async def get_carrier(
    carrier_id: str,
    country: str = "MX",
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get a specific carrier."""
    service = get_service(accept_language)
    result = service.get_carrier(carrier_id=carrier_id, country=country)
    if not result:
        raise HTTPException(status_code=404, detail={"error": "CARRIER_NOT_FOUND"})
    return ServiceResponse(data=result)


@router.get("/carriers/{carrier_id}/plans")
async def get_carrier_plans(
    carrier_id: str,
    country: str = "MX",
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get available plans for a carrier."""
    service = get_service(accept_language)
    result = service.get_carrier_plans(carrier_id=carrier_id, country=country)
    return ServiceResponse(data={"plans": result})


# ==================== Phone Number Endpoints ====================


@router.get("/frequent-numbers")
async def get_frequent_numbers(
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get user's frequently topped-up numbers."""
    service = get_service(accept_language)
    result = service.get_frequent_numbers(user_id=x_user_id)
    return ServiceResponse(data=result)


@router.post("/detect-carrier")
async def detect_carrier(
    request: DetectCarrierRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Detect carrier from phone number."""
    service = get_service(accept_language)
    result = service.detect_carrier(phone_number=request.phone_number)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result)
    return ServiceResponse(data=result)


# ==================== Pricing Endpoints ====================


@router.get("/price")
async def get_topup_price(
    carrier_id: str,
    amount: float,
    country: str = "MX",
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get the USD price for a top-up."""
    service = get_service(accept_language)
    try:
        result = service.get_topup_price(carrier_id=carrier_id, amount=amount, country=country)
        return ServiceResponse(data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})


# ==================== TopUp Endpoints ====================


@router.post("")
async def send_topup(
    request: SendTopupRequest,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Send a mobile top-up."""
    service = get_service(accept_language)
    try:
        result = service.send_topup(
            phone_number=request.phone_number,
            carrier_id=request.carrier_id,
            amount=request.amount,
            payment_method_id=request.payment_method_id,
            user_id=x_user_id,
        )
        return ServiceResponse(data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})


@router.get("/history")
async def get_topup_history(
    limit: int = 5,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get top-up history."""
    service = get_service(accept_language)
    result = service.get_topup_history(user_id=x_user_id, limit=limit)
    return ServiceResponse(data=result)
