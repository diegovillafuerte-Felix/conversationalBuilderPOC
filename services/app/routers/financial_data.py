"""Financial Data service API router."""

from fastapi import APIRouter, Header

from app.schemas.common import ServiceResponse
from app.services.financial_data import FinancialDataService

router = APIRouter(prefix="/financial-data", tags=["financial-data"])

# Singleton service instance
_service: FinancialDataService | None = None


def get_service() -> FinancialDataService:
    """Get or create service instance."""
    global _service
    if _service is None:
        _service = FinancialDataService()
    return _service


# ==================== Financial Summary Endpoints ====================


@router.get("/summary")
async def get_user_financial_summary(
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get user's financial activity summary."""
    service = get_service()
    result = service.get_user_financial_summary(user_id=x_user_id)
    return ServiceResponse(data=result)


# ==================== Rate Trends Endpoints ====================


@router.get("/rate-trends")
async def get_rate_trends(
    corridor: str = "USD_MXN",
    days: int = 30,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get exchange rate trends for a corridor."""
    service = get_service()
    result = service.get_rate_trends(corridor=corridor, days=days)
    return ServiceResponse(data=result)


# ==================== Optimization Tips Endpoints ====================


@router.get("/optimization-tips")
async def get_fee_optimization_tips(
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get personalized fee optimization tips."""
    service = get_service()
    result = service.get_fee_optimization_tips(user_id=x_user_id)
    return ServiceResponse(data={"tips": result})


# ==================== Spending Analysis Endpoints ====================


@router.get("/spending-analysis")
async def get_spending_analysis(
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Analyze user's spending patterns."""
    service = get_service()
    result = service.get_spending_analysis(user_id=x_user_id)
    return ServiceResponse(data=result)


# ==================== Savings Recommendations Endpoints ====================


@router.get("/savings-recommendations")
async def get_savings_recommendations(
    x_user_id: str = Header("user_demo", alias="X-User-Id"),
    accept_language: str = Header("es", alias="Accept-Language"),
) -> ServiceResponse:
    """Get savings recommendations."""
    service = get_service()
    result = service.get_savings_recommendations(user_id=x_user_id)
    return ServiceResponse(data=result)
