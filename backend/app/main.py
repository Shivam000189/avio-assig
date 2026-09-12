"""FastAPI application factory and lifespan management.

Creates the ASGI application via `create_app()`, wiring up middleware,
custom validation exception handlers, and the router tree.
"""

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.database import connect_db, disconnect_db
from app.routers.analysis import router as analysis_router
from app.routers.complaints import router as complaints_router
from app.routers.health import router as health_router
from app.security.limiter import limiter, rate_limit_exceeded_handler

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Manage startup and shutdown events for the application.

    On startup: connect the Prisma client.
    On shutdown: disconnect the Prisma client.
    """
    logger.info("Starting up — connecting to database…")
    await connect_db()
    yield
    logger.info("Shutting down — disconnecting from database…")
    await disconnect_db()


def create_app() -> FastAPI:
    """Build and return a fully-configured FastAPI application instance."""

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )

    # -- Rate Limiter State & Handlers -----------------------------------------
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # -- CORS ------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -- Security Headers Middleware -------------------------------------------
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):  # noqa: ANN001
        response = await call_next(request)
        # Prevent MIME-sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Prevent clickjacking / iframe embedding
        response.headers["X-Frame-Options"] = "DENY"
        # XSS auditor block mode
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # Referrer privacy policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Modern permissions policy restricting sensitive browser features
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    # -- Routers (Analysis router MUST precede complaints_router to avoid /analyze shadowing) --
    app.include_router(health_router)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(analysis_router)
    app.include_router(analysis_router, prefix="/api/v1")
    app.include_router(complaints_router)
    app.include_router(complaints_router, prefix="/api/v1")

    # -- Custom 422 Request Validation Exception Handler -----------------------
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Format 422 validation errors into structured per-field error objects."""
        formatted_errors: list[dict[str, str]] = []
        for err in exc.errors():
            loc = err.get("loc", ())
            # Extract the leaf attribute name (e.g. 'batchNumber', 'expiryDate', 'text')
            field_name = str(loc[-1]) if loc else "non_field"
            raw_msg = err.get("msg", "Invalid value")
            # Strip Pydantic v2 internal prefix if present
            if raw_msg.startswith("Value error, "):
                raw_msg = raw_msg[len("Value error, ") :]
            formatted_errors.append(
                {
                    "field": field_name,
                    "message": raw_msg,
                }
            )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validation error",
                "errors": formatted_errors,
            },
        )

    # -- Global Unhandled Exception Handler ------------------------------------
    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Sanitize 500 error responses: Log full stack trace server-side, never leak to client."""
        logger.exception(
            "Unhandled exception on %s %s",
            request.method,
            request.url.path,
        )
        return JSONResponse(
            content={
                "detail": "An internal server error occurred. Please contact the system administrator.",
                "error": "internal_server_error",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # -- Request-logging and Error Protection middleware -----------------------
    @app.middleware("http")
    async def log_requests(request: Request, call_next):  # noqa: ANN001
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "Unhandled exception on %s %s (%.1f ms): %s",
                request.method,
                request.url.path,
                elapsed_ms,
                exc,
            )
            return JSONResponse(
                content={
                    "detail": "An internal server error occurred. Please contact the system administrator.",
                    "error": "internal_server_error",
                },
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s → %s (%.1f ms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    return app
