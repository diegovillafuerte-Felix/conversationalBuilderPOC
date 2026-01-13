"""Authentication and authorization for the Felix Orchestrator API."""

import logging
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# HTTP Bearer token security scheme
security = HTTPBearer()


async def verify_admin_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """
    Verify admin API token for protected endpoints.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        The validated token

    Raises:
        HTTPException: If token is invalid or missing
    """
    token = credentials.credentials

    # Check if admin token is configured
    if not settings.admin_api_token:
        logger.warning(
            "⚠️  ADMIN_API_TOKEN not configured - admin endpoints are UNPROTECTED! "
            "This is ONLY acceptable in development. Set ADMIN_API_TOKEN for production!"
        )
        # In development without token, allow access but warn
        if settings.debug:
            return "dev-bypass-token"
        else:
            # In production, fail hard
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Admin authentication not configured - set ADMIN_API_TOKEN"
            )

    # Verify token matches configured admin token
    if token != settings.admin_api_token:
        logger.warning(f"Invalid admin token attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing admin token"
        )

    return token


# Optional: Add a dependency that allows bypassing auth in debug mode for development
async def verify_admin_token_optional(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """
    Verify admin token but allow bypass in debug mode.

    WARNING: Only use this in development! Production should use verify_admin_token.
    """
    if settings.debug and not settings.admin_api_token:
        logger.warning("Admin auth bypassed in DEBUG mode - DO NOT USE IN PRODUCTION")
        return "debug-bypass"

    return await verify_admin_token(credentials)
