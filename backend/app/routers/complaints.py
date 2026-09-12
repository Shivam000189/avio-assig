"""Complaint API endpoints for viewing, querying, modifying, and auditing customer complaints.

================================================================================
FASTAPI ROUTE ORDERING GOTCHA:
In FastAPI / Starlette routing, static path segments MUST be declared BEFORE
parameterized path segments. Specifically:
    `GET /complaints/stats`
MUST be registered BEFORE:
    `GET /complaints/{complaint_id}`
If `/complaints/{complaint_id}` were defined first, any request to `/complaints/stats`
would match `{complaint_id} = "stats"`, attempting to query the database for a
record with ID "stats" and returning 404 instead of returning analytics metrics.
================================================================================
"""

from datetime import datetime
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.config import settings
from app.database import prisma
from app.exceptions import NotFoundError
from app.schemas.capa import CapaCreate, CapaResponse, CapaUpdate
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintResponse,
    ComplaintStatsResponse,
    ComplaintUpdate,
    PaginatedComplaintsResponse,
)
from app.security.limiter import limiter
from app.services.complaint_repository import (
    create_complaint,
    delete_complaint,
    get_capa_by_complaint_id,
    get_complaint_by_id,
    get_stats,
    list_complaints,
    update_complaint,
    upsert_capa_for_complaint,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/complaints", tags=["Complaints"])


def _get_attr(obj: Any, key: str, default: Any = None) -> Any:
    """Safely get an attribute from either a Prisma model or dictionary."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


async def require_db_connection() -> None:
    """FastAPI dependency to verify database connectivity.

    Raises:
        HTTPException (503): If the Prisma client is not currently connected.
    """
    if not prisma.is_connected():
        logger.warning("Database unavailable during complaint endpoint request.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is currently unavailable.",
        )


# ==============================================================================
# 1. STATS ROUTE (Declared BEFORE {complaint_id} to prevent path shadowing)
# ==============================================================================


@router.get(
    "/stats",
    response_model=ComplaintStatsResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_db_connection)],
    summary="Get complaint analytics",
    description="Compute summary statistics (totals, by status, by severity, open by type) in a single aggregation query.",
)
@limiter.limit(lambda: settings.rate_limit_default)
async def get_complaint_statistics(request: Request) -> ComplaintStatsResponse:
    """Return aggregated complaint metrics for dashboard visualizers."""
    stats = await get_stats()
    return ComplaintStatsResponse.model_validate(stats)


# ==============================================================================
# 2. LIST & SEARCH ROUTE (Paginated)
# ==============================================================================


@router.get(
    "",
    response_model=PaginatedComplaintsResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_db_connection)],
    summary="List complaints with search and filters",
    description="Retrieve paginated complaints with optional filtering by status, severity, type, date range, and free-text search.",
)
@limiter.limit(lambda: settings.rate_limit_default)
async def get_all_complaints(
    request: Request,
    skip: Annotated[
        int,
        Query(ge=0, description="Number of records to skip for pagination"),
    ] = 0,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Max number of records to return (1-100)"),
    ] = 20,
    search: Annotated[
        str | None,
        Query(
            max_length=200,
            description="Search query across product name, batch number, complainant, description",
            examples=["Paracetamol"],
        ),
    ] = None,
    status_filter: Annotated[
        str | None,
        Query(
            alias="status",
            description="Filter by complaint status (Open, InProgress, Closed)",
            examples=["Open"],
        ),
    ] = None,
    severity: Annotated[
        str | None,
        Query(
            description="Filter by severity level (Critical, Major, Minor)",
            examples=["Major"],
        ),
    ] = None,
    complaint_type: Annotated[
        str | None,
        Query(
            alias="complaintType",
            description="Filter by complaint type (e.g. QualityDefect, AdverseEvent)",
            examples=["QualityDefect"],
        ),
    ] = None,
    created_from: Annotated[
        datetime | None,
        Query(
            description="Start date (ISO 8601) for complaint intake range",
            examples=["2026-01-01T00:00:00Z"],
        ),
    ] = None,
    created_to: Annotated[
        datetime | None,
        Query(
            description="End date (ISO 8601) for complaint intake range",
            examples=["2026-12-31T23:59:59Z"],
        ),
    ] = None,
) -> PaginatedComplaintsResponse:
    """Return paginated complaints matching search/filter criteria."""
    items, total = await list_complaints(
        status=status_filter,
        severity=severity,
        complaint_type=complaint_type,
        search=search,
        created_from=created_from,
        created_to=created_to,
        skip=skip,
        limit=limit,
    )
    return PaginatedComplaintsResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=[ComplaintResponse.model_validate(c) for c in items],
    )


# ==============================================================================
# 3. CREATE COMPLAINT
# ==============================================================================


@router.post(
    "",
    response_model=ComplaintResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_db_connection)],
    summary="Create complaint",
    description="Submit a new customer complaint. Automatically assigns a CMP-YYYY-NNNN tracking number.",
)
@limiter.limit(lambda: settings.rate_limit_default)
async def create_new_complaint(
    request: Request,
    payload: ComplaintCreate,
) -> ComplaintResponse:
    """Create a new complaint record with auto-generated tracking identifier."""
    complaint = await create_complaint(payload)
    complaint_id = _get_attr(complaint, "id")
    complaint_number = _get_attr(complaint, "complaintNumber")
    product_name = _get_attr(complaint, "productName")
    logger.info(
        "Created complaint [id=%s, complaintNumber=%s] for product '%s'",
        complaint_id,
        complaint_number,
        product_name,
    )
    return ComplaintResponse.model_validate(complaint)


# ==============================================================================
# 4. SINGLE COMPLAINT CRUD
# ==============================================================================


@router.get(
    "/{complaint_id}",
    response_model=ComplaintResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_db_connection)],
    summary="Get complaint by ID",
    description="Retrieve full details for a single complaint including documents, CAPA, and summary.",
)
@limiter.limit(lambda: settings.rate_limit_default)
async def get_single_complaint(
    request: Request,
    complaint_id: str,
) -> ComplaintResponse:
    """Return details for a specific complaint or 404 if not found."""
    try:
        complaint = await get_complaint_by_id(complaint_id)
        return ComplaintResponse.model_validate(complaint)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )


@router.put(
    "/{complaint_id}",
    response_model=ComplaintResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_db_connection)],
    summary="Update complaint",
    description="Apply partial updates to an existing complaint record with audit logging.",
)
@limiter.limit(lambda: settings.rate_limit_default)
async def update_single_complaint(
    request: Request,
    complaint_id: str,
    payload: ComplaintUpdate,
) -> ComplaintResponse:
    """Update fields on an existing complaint."""
    try:
        updated, modified_fields = await update_complaint(complaint_id, payload)
        complaint_number = _get_attr(updated, "complaintNumber")
        logger.info(
            "AUDIT: Updated complaint [id=%s, complaintNumber=%s]. Modified fields: %s",
            complaint_id,
            complaint_number,
            modified_fields,
        )
        return ComplaintResponse.model_validate(updated)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )


@router.delete(
    "/{complaint_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_db_connection)],
    summary="Delete complaint",
    description="Permanently remove a complaint and cascade-delete its documents, CAPA, and summary records.",
)
@limiter.limit(lambda: settings.rate_limit_default)
async def delete_single_complaint(
    request: Request,
    complaint_id: str,
) -> Response:
    """Delete a complaint record by ID."""
    try:
        complaint_number = await delete_complaint(complaint_id)
        logger.info(
            "AUDIT: Deleted complaint [id=%s, complaintNumber=%s]",
            complaint_id,
            complaint_number,
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )


# ==============================================================================
# 5. CAPA SUB-RESOURCE ENDPOINTS
# ==============================================================================


@router.get(
    "/{complaint_id}/capa",
    response_model=CapaResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_db_connection)],
    summary="Get complaint CAPA",
    description="Retrieve the Corrective and Preventive Action plan attached to a complaint.",
)
@limiter.limit(lambda: settings.rate_limit_default)
async def get_complaint_capa(
    request: Request,
    complaint_id: str,
) -> CapaResponse:
    """Retrieve CAPA record for a complaint."""
    try:
        capa = await get_capa_by_complaint_id(complaint_id)
        return CapaResponse.model_validate(capa)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CAPA not found" if "CAPA" in str(exc) else "Complaint not found",
        )


@router.put(
    "/{complaint_id}/capa",
    response_model=CapaResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_db_connection)],
    summary="Upsert complaint CAPA",
    description="Create or update the Corrective and Preventive Action record for a complaint.",
)
@limiter.limit(lambda: settings.rate_limit_default)
async def update_complaint_capa(
    request: Request,
    complaint_id: str,
    payload: CapaUpdate,
) -> CapaResponse:
    """Upsert CAPA details for a complaint."""
    try:
        capa = await upsert_capa_for_complaint(complaint_id, payload)
        capa_id = _get_attr(capa, "id")
        logger.info(
            "AUDIT: Upserted CAPA [id=%s] for complaint [id=%s]",
            capa_id,
            complaint_id,
        )
        return CapaResponse.model_validate(capa)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )
