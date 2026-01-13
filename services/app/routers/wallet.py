"""Wallet service API router."""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.services.wallet import MockWalletService
from app.schemas.common import ServiceResponse


router = APIRouter(prefix="/wallet", tags=["wallet"])

# Service instances by language
_services: dict = {}


def get_service(language: str = "es") -> MockWalletService:
    """Get or create service instance for language."""
    if language not in _services:
        _services[language] = MockWalletService(language=language)
    return _services[language]


# ==================== Request Schemas ====================


class AddFundsRequest(BaseModel):
    """Request to add funds to wallet."""
    amount: float = Field(gt=0)
    payment_method_id: str = "pm_1"


class AddPaymentMethodRequest(BaseModel):
    """Request to add a payment method."""
    method_type: str
    token: str


# ==================== Balance Endpoints ====================


@router.get("/balance")
async def get_balance(
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get wallet balance."""
    service = get_service(accept_language)
    result = service.get_balance(user_id=x_user_id)
    return ServiceResponse(data=result)


# ==================== Payment Methods Endpoints ====================


@router.get("/payment-methods")
async def get_payment_methods(
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get linked payment methods."""
    service = get_service(accept_language)
    result = service.get_payment_methods(user_id=x_user_id)
    return ServiceResponse(data={"payment_methods": result})


@router.post("/payment-methods")
async def add_payment_method(
    request: AddPaymentMethodRequest,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Add a new payment method."""
    service = get_service(accept_language)
    result = service.add_payment_method(
        method_type=request.method_type,
        token=request.token,
        user_id=x_user_id,
    )
    return ServiceResponse(data=result)


@router.delete("/payment-methods/{payment_method_id}")
async def remove_payment_method(
    payment_method_id: str,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Remove a payment method."""
    service = get_service(accept_language)
    result = service.remove_payment_method(
        payment_method_id=payment_method_id,
        user_id=x_user_id,
    )
    return ServiceResponse(data=result)


# ==================== Funds Endpoints ====================


@router.post("/add-funds")
async def add_funds(
    request: AddFundsRequest,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Add funds to wallet."""
    service = get_service(accept_language)
    result = service.add_funds(
        amount=request.amount,
        payment_method_id=request.payment_method_id,
        user_id=x_user_id,
    )
    return ServiceResponse(data=result)


# ==================== Transaction Endpoints ====================


@router.get("/transactions")
async def get_transactions(
    limit: int = 10,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get wallet transaction history."""
    service = get_service(accept_language)
    result = service.get_transactions(user_id=x_user_id, limit=limit)
    return ServiceResponse(data={"transactions": result})
