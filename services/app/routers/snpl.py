"""SNPL (Send Now Pay Later) service API router."""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.services.snpl import MockSNPLService
from app.schemas.common import ServiceResponse


router = APIRouter(prefix="/snpl", tags=["snpl"])

# Service instances by language
_services: dict = {}


def get_service(language: str = "es") -> MockSNPLService:
    """Get or create service instance for language."""
    if language not in _services:
        _services[language] = MockSNPLService(language=language)
    return _services[language]


# ==================== Request Schemas ====================


class CalculateTermsRequest(BaseModel):
    """Request to calculate loan terms."""
    amount: float = Field(gt=0, le=1000)
    weeks: int = Field(gt=0)


class SubmitApplicationRequest(BaseModel):
    """Request to submit SNPL application."""
    amount: float = Field(gt=0, le=1000)
    term_weeks: int = Field(gt=0)


class MakePaymentRequest(BaseModel):
    """Request to make a payment."""
    loan_id: Optional[str] = None
    amount: float = Field(gt=0)
    payment_method_id: str = "pm_default"


class UseForRemittanceRequest(BaseModel):
    """Request to use credit for remittance."""
    transfer_id: str
    recipient_name: str
    amount_usd: float = Field(gt=0)
    country: str


# ==================== Eligibility Endpoints ====================


@router.get("/eligibility")
async def get_snpl_eligibility(
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Check user's SNPL eligibility and pre-approved amount."""
    service = get_service(accept_language)
    result = service.get_snpl_eligibility(user_id=x_user_id)
    return ServiceResponse(data=result)


# ==================== Terms Endpoints ====================


@router.post("/calculate")
async def calculate_terms(
    request: CalculateTermsRequest,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Calculate loan terms for given amount and duration."""
    service = get_service(accept_language)
    result = service.calculate_terms(
        amount=request.amount,
        weeks=request.weeks,
        user_id=x_user_id,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return ServiceResponse(data=result)


# ==================== Application Endpoints ====================


@router.post("/applications")
async def submit_snpl_application(
    request: SubmitApplicationRequest,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Submit a new SNPL loan application."""
    service = get_service(accept_language)
    result = service.submit_snpl_application(
        amount=request.amount,
        term_weeks=request.term_weeks,
        user_id=x_user_id,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return ServiceResponse(data=result)


# ==================== Overview Endpoints ====================


@router.get("/overview")
async def get_snpl_overview(
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get user's SNPL overview (active loans, total balance)."""
    service = get_service(accept_language)
    result = service.get_snpl_overview(user_id=x_user_id)
    return ServiceResponse(data=result)


# ==================== Loan Endpoints ====================


@router.get("/loans")
async def list_loans(
    status: Optional[str] = None,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """List user's loans."""
    service = get_service(accept_language)
    result = service.list_loans(user_id=x_user_id, status=status)
    return ServiceResponse(data=result)


@router.get("/loans/{loan_id}")
async def get_loan_details(
    loan_id: str,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get details of a specific loan."""
    service = get_service(accept_language)
    result = service.get_loan_details(loan_id=loan_id, user_id=x_user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result)
    return ServiceResponse(data=result)


@router.get("/loans/{loan_id}/schedule")
async def get_payment_schedule(
    loan_id: str,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get payment schedule for a loan."""
    service = get_service(accept_language)
    result = service.get_payment_schedule(loan_id=loan_id, user_id=x_user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result)
    return ServiceResponse(data=result)


@router.post("/loans/{loan_id}/use-for-remittance")
async def use_credit_for_remittance(
    loan_id: str,
    request: UseForRemittanceRequest,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Use SNPL credit for a remittance transfer."""
    service = get_service(accept_language)
    result = service.use_credit_for_remittance(
        loan_id=loan_id,
        transfer_id=request.transfer_id,
        recipient_name=request.recipient_name,
        amount_usd=request.amount_usd,
        country=request.country,
        user_id=x_user_id,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return ServiceResponse(data=result)


# ==================== Payment Endpoints ====================


@router.get("/payments")
async def get_payment_history(
    loan_id: Optional[str] = None,
    limit: int = 10,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get payment history."""
    service = get_service(accept_language)
    if loan_id:
        result = service.get_payment_history(loan_id=loan_id, user_id=x_user_id, limit=limit)
    else:
        # Return all payments across all loans
        result = {"payments": [], "count": 0}
    return ServiceResponse(data=result)


@router.post("/payments")
async def make_snpl_payment(
    request: MakePaymentRequest,
    loan_id: Optional[str] = None,
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Make a payment on a loan."""
    resolved_loan_id = loan_id or request.loan_id
    if not resolved_loan_id:
        raise HTTPException(status_code=400, detail={"error": "loan_id is required"})

    service = get_service(accept_language)
    result = service.make_snpl_payment(
        loan_id=resolved_loan_id,
        amount=request.amount,
        payment_method_id=request.payment_method_id,
        user_id=x_user_id,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return ServiceResponse(data=result)
