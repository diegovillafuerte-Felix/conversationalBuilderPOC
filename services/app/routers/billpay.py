"""BillPay service API router."""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.services.billpay import MockBillPayService
from app.schemas.common import ServiceResponse


router = APIRouter(prefix="/billpay", tags=["billpay"])

# Service instances by language
_services: dict = {}


def get_service(language: str = "es") -> MockBillPayService:
    """Get or create service instance for language."""
    if language not in _services:
        _services[language] = MockBillPayService(language=language)
    return _services[language]


# ==================== Request Schemas ====================


class CalculatePaymentRequest(BaseModel):
    """Request to calculate payment amount."""
    biller_id: str
    amount_mxn: float = Field(gt=0)


class PayBillRequest(BaseModel):
    """Request to pay a bill."""
    biller_id: str
    account_number: str
    amount: float = Field(gt=0)
    payment_method_id: str = "pm_default"


class SaveBillerRequest(BaseModel):
    """Request to save a biller."""
    biller_id: str
    account_number: str
    nickname: str


# ==================== Biller Endpoints ====================


@router.get("/billers")
async def get_billers(
    category: Optional[str] = None,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get available billers."""
    service = get_service(accept_language)
    result = service.get_billers(category=category)
    return ServiceResponse(data={"billers": result})


@router.get("/billers/{biller_id}")
async def get_biller(
    biller_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get a specific biller."""
    service = get_service(accept_language)
    result = service.get_biller(biller_id=biller_id)
    if not result:
        raise HTTPException(status_code=404, detail={"error": "BILLER_NOT_FOUND"})
    return ServiceResponse(data=result)


@router.get("/billers/{biller_id}/details")
async def get_bill_details(
    biller_id: str,
    account_number: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get bill details for an account."""
    service = get_service(accept_language)
    try:
        result = service.get_bill_details(
            biller_id=biller_id,
            account_number=account_number,
            user_id=x_user_id,
        )
        return ServiceResponse(data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})


# ==================== Saved Billers Endpoints ====================


@router.get("/saved")
async def get_saved_billers(
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get user's saved billers."""
    service = get_service(accept_language)
    result = service.get_saved_billers(user_id=x_user_id)
    return ServiceResponse(data={"billers": result})


@router.post("/saved")
async def save_biller(
    request: SaveBillerRequest,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Save a biller for quick access."""
    service = get_service(accept_language)
    try:
        result = service.save_biller(
            biller_id=request.biller_id,
            account_number=request.account_number,
            nickname=request.nickname,
            user_id=x_user_id,
        )
        return ServiceResponse(data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})


# ==================== Payment Endpoints ====================


@router.post("/calculate")
async def calculate_payment(
    request: CalculatePaymentRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Calculate USD amount for a bill payment."""
    service = get_service(accept_language)
    result = service.calculate_payment(
        biller_id=request.biller_id,
        amount_mxn=request.amount_mxn,
    )
    return ServiceResponse(data=result)


@router.post("/payments")
async def pay_bill(
    request: PayBillRequest,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Pay a bill."""
    service = get_service(accept_language)
    try:
        result = service.pay_bill(
            biller_id=request.biller_id,
            account_number=request.account_number,
            amount=request.amount,
            payment_method_id=request.payment_method_id,
            user_id=x_user_id,
        )
        return ServiceResponse(data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})


@router.get("/history")
async def get_payment_history(
    limit: int = 5,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get bill payment history."""
    service = get_service(accept_language)
    result = service.get_payment_history(user_id=x_user_id, limit=limit)
    return ServiceResponse(data={"payments": result})
