"""Rate limiting infrastructure for the Pharma Complaint QMS API.

Utilizes slowapi (backed by limits) with tier-aware, configurable rate limits.
All thresholds can be overridden via environment variables.
"""

from collections.abc import Callable
import logging
from typing import Any

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """Resolve the true client IP address, safely checking proxy headers.

    Checks X-Forwarded-For if available, otherwise falls back to standard
    remote address.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # First IP in the comma-separated chain is the client IP
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip:
            return client_ip
    return get_remote_address(request) or "127.0.0.1"


# Singleton Limiter instance configured with application settings
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=[settings.rate_limit_default] if settings.rate_limit_enabled else [],
    enabled=settings.rate_limit_enabled,
    storage_uri="memory://",
    headers_enabled=False,
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Custom HTTP 429 response handler returning structured, generic JSON.

    Sets Retry-After header and logs rate limit breach server-side.
    """
    client_ip = get_client_ip(request)
    logger.warning(
        "Rate limit exceeded for IP %s on path %s %s: %s",
        client_ip,
        request.method,
        request.url.path,
        exc.detail,
    )

    retry_after = "60"
    if hasattr(exc, "retry_after") and exc.retry_after:
        retry_after = str(int(exc.retry_after))

    headers = {
        "Retry-After": retry_after,
        "X-RateLimit-Exceeded": "true",
    }

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": "Too many requests. Please slow down and try again later.",
            "error": "rate_limit_exceeded",
            "retryAfterSeconds": int(retry_after),
        },
        headers=headers,
    )
