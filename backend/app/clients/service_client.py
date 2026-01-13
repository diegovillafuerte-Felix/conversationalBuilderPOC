"""HTTP client for communicating with services gateway."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ServiceResult:
    """Result from a service call."""

    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    error_code: Optional[str] = None


class ServiceClient:
    """HTTP client for communicating with services gateway."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """Initialize the service client.

        Args:
            base_url: Base URL for the services gateway
            timeout: Request timeout in seconds
        """
        # Import here to avoid circular imports
        from app.config import get_settings

        settings = get_settings()
        self.base_url = base_url or getattr(
            settings, "service_gateway_url", "http://localhost:8001"
        )
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> ServiceResult:
        """Check if the services gateway is healthy.

        Returns:
            ServiceResult with health status
        """
        try:
            client = await self._get_client()
            response = await client.get("/health", timeout=5.0)
            if response.status_code == 200:
                return ServiceResult(success=True, data={"status": "healthy"})
            return ServiceResult(
                success=False,
                error=f"Unhealthy: HTTP {response.status_code}",
                error_code="UNHEALTHY",
            )
        except httpx.TimeoutException:
            logger.warning("Health check timeout for services gateway")
            return ServiceResult(
                success=False,
                error="Services gateway health check timeout",
                error_code="TIMEOUT",
            )
        except httpx.ConnectError:
            logger.warning("Cannot connect to services gateway")
            return ServiceResult(
                success=False,
                error="Services gateway unreachable",
                error_code="CONNECTION_ERROR",
            )
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                error_code="UNKNOWN_ERROR",
            )

    async def call_service(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_body: Optional[Dict] = None,
        user_id: Optional[str] = None,
        language: str = "es",
    ) -> ServiceResult:
        """Make a service call.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            params: Query parameters
            json_body: JSON body for POST/PUT requests
            user_id: User ID for X-User-Id header
            language: Language for Accept-Language header

        Returns:
            ServiceResult with success/failure and data
        """
        client = await self._get_client()

        headers = {
            "Accept-Language": language,
            "Content-Type": "application/json",
        }
        if user_id:
            headers["X-User-Id"] = user_id

        try:
            method_upper = method.upper()

            if method_upper == "GET":
                response = await client.get(
                    endpoint,
                    params=params,
                    headers=headers,
                )
            elif method_upper == "POST":
                response = await client.post(
                    endpoint,
                    json=json_body,
                    params=params,
                    headers=headers,
                )
            elif method_upper == "PUT":
                response = await client.put(
                    endpoint,
                    json=json_body,
                    headers=headers,
                )
            elif method_upper == "DELETE":
                response = await client.delete(
                    endpoint,
                    headers=headers,
                )
            else:
                return ServiceResult(
                    success=False,
                    error=f"Unknown HTTP method: {method}",
                    error_code="INVALID_METHOD",
                )

            # Handle HTTP errors
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    error_detail = error_data.get("detail", {})
                    if isinstance(error_detail, dict):
                        return ServiceResult(
                            success=False,
                            error=error_detail.get("error", f"HTTP {response.status_code}"),
                            error_code=error_detail.get("error_code", "HTTP_ERROR"),
                            data=error_detail,
                        )
                    else:
                        return ServiceResult(
                            success=False,
                            error=str(error_detail),
                            error_code="HTTP_ERROR",
                        )
                except Exception:
                    return ServiceResult(
                        success=False,
                        error=f"HTTP {response.status_code}",
                        error_code="HTTP_ERROR",
                    )

            # Parse successful response
            data = response.json()

            if data.get("success", True):
                return ServiceResult(success=True, data=data.get("data"))
            else:
                return ServiceResult(
                    success=False,
                    error=data.get("error"),
                    error_code=data.get("error_code"),
                )

        except httpx.TimeoutException:
            logger.error(f"Timeout calling {endpoint}")
            return ServiceResult(
                success=False,
                error="Service timeout",
                error_code="TIMEOUT",
            )
        except httpx.ConnectError as e:
            logger.error(f"Connection error calling {endpoint}: {e}")
            return ServiceResult(
                success=False,
                error="Service unavailable",
                error_code="CONNECTION_ERROR",
            )
        except Exception as e:
            logger.error(f"Error calling {endpoint}: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                error_code="UNKNOWN_ERROR",
            )


# Singleton instance
_service_client: Optional[ServiceClient] = None


def get_service_client() -> ServiceClient:
    """Get or create the service client singleton."""
    global _service_client
    if _service_client is None:
        _service_client = ServiceClient()
    return _service_client
