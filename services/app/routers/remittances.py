"""Remittances service API router."""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.services.remittances import MockRemittancesService
from app.schemas.common import ServiceResponse


router = APIRouter(prefix="/remittances", tags=["remittances"])

# Service instances by language
_services: dict = {}


def get_service(language: str = "es") -> MockRemittancesService:
    """Get or create service instance for language."""
    if language not in _services:
        _services[language] = MockRemittancesService(language=language)
    return _services[language]


# ==================== Request Schemas ====================


class CreateQuoteRequest(BaseModel):
    """Request to create a quote."""
    amount_usd: float = Field(gt=0, description="Amount in USD")
    country: str = Field(default="MX", description="Destination country code")
    delivery_type: str = Field(default="BANK", description="Delivery method type")


class AddRecipientRequest(BaseModel):
    """Request to add a recipient."""
    first_name: str
    last_name: str
    country: str
    delivery_type: str
    city: Optional[str] = None
    state: Optional[str] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    clabe: Optional[str] = None
    account_type: Optional[str] = None
    card_number: Optional[str] = None
    wallet_type: Optional[str] = None
    phone_number: Optional[str] = None
    middle_name: Optional[str] = None


class AddDeliveryMethodRequest(BaseModel):
    """Request to add a delivery method."""
    delivery_type: str
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    clabe: Optional[str] = None
    account_type: Optional[str] = None
    card_number: Optional[str] = None
    wallet_type: Optional[str] = None
    phone_number: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


class CreateTransferRequest(BaseModel):
    """Request to create a transfer."""
    recipient_id: str
    amount_usd: float = Field(gt=0)
    delivery_method_id: Optional[str] = None
    payment_method_id: str = "pm_default"


class CreateSnplTransferRequest(BaseModel):
    """Request to create SNPL-funded transfer."""
    snpl_loan_id: str
    recipient_id: str
    amount_usd: float = Field(gt=0)
    delivery_method_id: Optional[str] = None


# ==================== Corridor & Rate Endpoints ====================


@router.get("/corridors")
async def get_corridors(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get all supported country corridors."""
    service = get_service(accept_language)
    result = service.get_corridors(user_id=x_user_id)
    return ServiceResponse(data=result)


@router.get("/exchange-rate")
async def get_exchange_rate(
    country: str = "MX",
    to_currency: Optional[str] = None,
    from_currency: str = "USD",
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get current exchange rate for a corridor."""
    service = get_service(accept_language)
    result = service.get_exchange_rate(
        country=country,
        to_currency=to_currency,
        from_currency=from_currency,
        user_id=x_user_id,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return ServiceResponse(data=result)


@router.post("/quotes")
async def create_quote(
    request: CreateQuoteRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Create a quote with fees and conversion."""
    service = get_service(accept_language)
    result = service.create_quote(
        amount_usd=request.amount_usd,
        country=request.country,
        delivery_type=request.delivery_type,
        user_id=x_user_id,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return ServiceResponse(data=result)


# ==================== Recipient Endpoints ====================


@router.get("/recipients")
async def list_recipients(
    country: Optional[str] = None,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """List user's saved recipients."""
    service = get_service(accept_language)
    result = service.list_recipients(country=country, user_id=x_user_id)
    return ServiceResponse(data=result)


@router.get("/recipients/{recipient_id}")
async def get_recipient(
    recipient_id: str,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get a specific recipient's details."""
    service = get_service(accept_language)
    result = service.get_recipient(recipient_id=recipient_id, user_id=x_user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result)
    return ServiceResponse(data=result)


@router.post("/recipients")
async def add_recipient(
    request: AddRecipientRequest,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Add a new recipient with delivery method."""
    service = get_service(accept_language)
    result = service.add_recipient(
        first_name=request.first_name,
        last_name=request.last_name,
        country=request.country,
        delivery_type=request.delivery_type,
        city=request.city,
        state=request.state,
        bank_name=request.bank_name,
        account_number=request.account_number,
        clabe=request.clabe,
        account_type=request.account_type,
        card_number=request.card_number,
        wallet_type=request.wallet_type,
        phone_number=request.phone_number,
        middle_name=request.middle_name,
        user_id=x_user_id,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return ServiceResponse(data=result)


@router.delete("/recipients/{recipient_id}")
async def delete_recipient(
    recipient_id: str,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Delete a recipient."""
    service = get_service(accept_language)
    result = service.delete_recipient(recipient_id=recipient_id, user_id=x_user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result)
    return ServiceResponse(data=result)


@router.post("/recipients/{recipient_id}/delivery-methods")
async def add_delivery_method(
    recipient_id: str,
    request: AddDeliveryMethodRequest,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Add a delivery method to an existing recipient."""
    service = get_service(accept_language)
    result = service.add_delivery_method(
        recipient_id=recipient_id,
        delivery_type=request.delivery_type,
        bank_name=request.bank_name,
        account_number=request.account_number,
        clabe=request.clabe,
        account_type=request.account_type,
        card_number=request.card_number,
        wallet_type=request.wallet_type,
        phone_number=request.phone_number,
        city=request.city,
        state=request.state,
        user_id=x_user_id,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return ServiceResponse(data=result)


# ==================== Delivery Method Endpoints ====================


@router.get("/delivery-methods")
async def get_delivery_methods(
    country: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get available delivery methods for a country."""
    service = get_service(accept_language)
    result = service.get_delivery_methods(country=country, user_id=x_user_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return ServiceResponse(data=result)


# ==================== Limits Endpoints ====================


@router.get("/limits")
async def get_user_limits(
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get user's KYC level and limits."""
    service = get_service(accept_language)
    result = service.get_user_limits(user_id=x_user_id)
    return ServiceResponse(data=result)


# ==================== Transfer Endpoints ====================


@router.post("/transfers")
async def create_transfer(
    request: CreateTransferRequest,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Create and execute a remittance transfer."""
    service = get_service(accept_language)
    result = service.create_transfer(
        recipient_id=request.recipient_id,
        amount_usd=request.amount_usd,
        delivery_method_id=request.delivery_method_id,
        payment_method_id=request.payment_method_id,
        user_id=x_user_id,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return ServiceResponse(data=result)


@router.get("/transfers")
async def list_transfers(
    limit: int = 5,
    status: Optional[str] = None,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get user's recent transfers."""
    service = get_service(accept_language)
    result = service.list_transfers(limit=limit, status=status, user_id=x_user_id)
    return ServiceResponse(data=result)


@router.get("/transfers/{transfer_id}")
async def get_transfer_status(
    transfer_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get status of a specific transfer."""
    service = get_service(accept_language)
    result = service.get_transfer_status(transfer_id=transfer_id, user_id=x_user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result)
    return ServiceResponse(data=result)


@router.post("/transfers/{transfer_id}/cancel")
async def cancel_transfer(
    transfer_id: str,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Cancel a pending transfer."""
    service = get_service(accept_language)
    result = service.cancel_transfer(transfer_id=transfer_id, user_id=x_user_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return ServiceResponse(data=result)


@router.post("/snpl-transfers")
async def create_snpl_transfer(
    request: CreateSnplTransferRequest,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Create a remittance transfer funded by SNPL credit."""
    service = get_service(accept_language)
    result = service.create_snpl_transfer(
        snpl_loan_id=request.snpl_loan_id,
        recipient_id=request.recipient_id,
        amount_usd=request.amount_usd,
        delivery_method_id=request.delivery_method_id,
        user_id=x_user_id,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return ServiceResponse(data=result)


# ==================== Quick Send Endpoints ====================


@router.get("/quick-send")
async def get_quick_send_options(
    limit: int = 5,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get recent transfers that can be quickly repeated."""
    service = get_service(accept_language)
    result = service.get_quick_send_options(user_id=x_user_id, limit=limit)
    return ServiceResponse(data=result)
