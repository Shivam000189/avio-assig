"""Analysis API router providing AI triage, file parsing, and saved-complaint ingestion endpoints.

================================================================================
FASTAPI ROUTE ORDERING GOTCHA:
In FastAPI / Starlette, static route path segments MUST be evaluated before
parameterized path segments.
The routes:
    `POST /api/v1/complaints/analyze`
    `POST /api/v1/complaints/analyze-file`
    `POST /api/v1/complaints/from-analysis`
MUST all be registered in `main.py` BEFORE `complaints_router` (which contains
`GET/PUT/DELETE /complaints/{complaint_id}`).
================================================================================
"""

import logging
import os
import time
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)

from app.config import settings
from app.database import prisma
from app.exceptions import FileParseError, GroqUnavailableError, NotFoundError
from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    CreateFromAnalysisRequest,
    DocumentMetadata,
    PotentialDuplicateInfo,
)
from app.schemas.complaint import ComplaintResponse
from app.security.limiter import limiter
from app.services.analysis_service import analyze_complaint
from app.services.complaint_repository import (
    apply_ai_insights_to_complaint,
    attach_document_to_complaint,
    create_complaint_from_analysis,
    get_complaint_by_id,
)
from app.services.parsers import parse_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/complaints", tags=["AI Analysis Engine"])

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".eml"}


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
# 1. TEXT ANALYSIS ENDPOINT
# ==============================================================================


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze complaint text with AI",
    description="Run the 7-node LangGraph pipeline on raw text to extract entities, check duplicates, evaluate completeness, classify risk, generate a summary, recommend CAPA, and hypothesize root cause.",
)
@limiter.limit(lambda: settings.rate_limit_ai_analysis)
async def analyze_raw_complaint(
    request: Request,
    payload: AnalysisRequest,
) -> AnalysisResponse:
    """Analyze unstructured complaint text via sequential LangGraph pipeline."""
    try:
        state = await analyze_complaint(raw_input=payload.text, source=payload.source)

        pot_dup = state.get("potential_duplicate")
        potential_dup_model = (
            PotentialDuplicateInfo.model_validate(pot_dup) if pot_dup else None
        )

        return AnalysisResponse(
            rawInput=state["raw_input"],
            source=state["source"],
            extracted=state.get("extracted"),
            missingFields=state.get("missing_fields", []),
            isComplete=state.get("is_complete", False),
            summary=state.get("summary"),
            severity=state.get("severity"),
            riskReasoning=state.get("risk_reasoning"),
            recommendedSlaDays=state.get("recommended_sla_days"),
            capaRecommendation=state.get("capa_recommendation"),
            capaActionType=state.get("capa_action_type"),
            rootCause=state.get("root_cause"),
            duplicateOf=state.get("duplicate_of"),
            potentialDuplicate=potential_dup_model,
            duplicateChecked=state.get("duplicate_checked", False),
            warnings=state.get("llm_errors", []),
            document=None,
        )
    except GroqUnavailableError as exc:
        logger.error("AI service failure during /complaints/analyze: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service unavailable",
        )


# ==============================================================================
# 2. FILE UPLOAD & ANALYSIS ENDPOINT
# ==============================================================================


@router.post(
    "/analyze-file",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and analyze complaint document (PDF / TXT / EML)",
    description="Upload a complaint document (.pdf, .txt, .eml). Extracts text, sniffs magic bytes, executes the LangGraph AI pipeline, and optionally attaches the document to a complaint.",
)
@limiter.limit(lambda: settings.rate_limit_uploads)
async def analyze_complaint_file(
    request: Request,
    file: Annotated[UploadFile, File(description="Complaint document (.pdf, .txt, .eml)")],
    complaint_id: Annotated[
        str | None,
        Form(description="Optional complaint ID to attach the uploaded document to"),
    ] = None,
) -> AnalysisResponse:
    """Parse uploaded document and execute AI analysis pipeline."""
    filename = file.filename or "uploaded_file"
    _, ext = os.path.splitext(filename.lower())

    # 1. Extension Validation
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": f"Unsupported file type '{ext}'",
                "allowed": sorted(list(ALLOWED_EXTENSIONS)),
            },
        )

    # 2. Size Validation (Max 10MB)
    max_bytes = settings.max_upload_mb * 1024 * 1024
    content = await file.read()
    file_size = len(content)

    if file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large (max {settings.max_upload_mb}MB)",
        )

    # 3. Document Parsing with Magic Byte Sniffing
    parse_start = time.perf_counter()
    try:
        parsed_doc = parse_file(filename=filename, content=content)
    except FileParseError as parse_err:
        logger.warning("File parsing failed for '%s': %s", filename, parse_err.message)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "detail": parse_err.message,
                "hint": parse_err.hint,
            },
        )

    # 4. Content Substantiveness Check
    if len(parsed_doc.text) < 30:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "detail": "Could not extract enough text from file",
                "hint": "Upload a document containing at least 30 characters of readable complaint narrative.",
            },
        )

    parse_ms = (time.perf_counter() - parse_start) * 1000

    # 5. Determine Intake Source Channel
    if parsed_doc.file_type == "pdf":
        source_channel = "PDF"
    elif parsed_doc.file_type == "eml":
        source_channel = "Email"
    else:
        source_channel = "Manual"

    # 6. Optional Document Persistence to existing complaint
    if complaint_id:
        try:
            await attach_document_to_complaint(
                complaint_id=complaint_id,
                filename=parsed_doc.filename,
                file_type=parsed_doc.file_type,
                extracted_text=parsed_doc.text,
            )
            logger.info("Persisted ComplaintDocument for complaint [%s]", complaint_id)
        except NotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Complaint not found",
            )

    # 7. Execute AI Analysis Pipeline
    graph_start = time.perf_counter()
    try:
        state = await analyze_complaint(raw_input=parsed_doc.text, source=source_channel)
    except GroqUnavailableError as exc:
        logger.error("AI service failure during /complaints/analyze-file: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service unavailable",
        )

    graph_ms = (time.perf_counter() - graph_start) * 1000

    logger.info(
        "File upload analysis complete for '%s' (size=%d bytes, chars=%d, parse_ms=%.1f, graph_ms=%.1f)",
        filename,
        file_size,
        len(parsed_doc.text),
        parse_ms,
        graph_ms,
    )

    pot_dup = state.get("potential_duplicate")
    potential_dup_model = (
        PotentialDuplicateInfo.model_validate(pot_dup) if pot_dup else None
    )

    return AnalysisResponse(
        rawInput=state["raw_input"],
        source=state["source"],
        extracted=state.get("extracted"),
        missingFields=state.get("missing_fields", []),
        isComplete=state.get("is_complete", False),
        summary=state.get("summary"),
        severity=state.get("severity"),
        riskReasoning=state.get("risk_reasoning"),
        recommendedSlaDays=state.get("recommended_sla_days"),
        capaRecommendation=state.get("capa_recommendation"),
        capaActionType=state.get("capa_action_type"),
        rootCause=state.get("root_cause"),
        duplicateOf=state.get("duplicate_of"),
        potentialDuplicate=potential_dup_model,
        duplicateChecked=state.get("duplicate_checked", False),
        warnings=state.get("llm_errors", []),
        document=DocumentMetadata(
            filename=parsed_doc.filename,
            fileType=parsed_doc.file_type,
            metadata=parsed_doc.metadata,
        ),
    )


# ==============================================================================
# 3. SAVED-COMPLAINT FROM ANALYSIS BRIDGE ENDPOINT
# ==============================================================================


@router.post(
    "/from-analysis",
    response_model=ComplaintResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_db_connection)],
    summary="Create complaint from AI analysis",
    description="Persist a verified AI-analyzed complaint with its linked summary and optional CAPA in an atomic database transaction.",
)
@limiter.limit(lambda: settings.rate_limit_default)
async def create_complaint_from_ai_analysis(
    request: Request,
    payload: CreateFromAnalysisRequest,
) -> ComplaintResponse:
    """Persist an analyzed and approved complaint with summary and CAPA atomically."""
    complaint = await create_complaint_from_analysis(payload)
    complaint_id = getattr(complaint, "id", None) or (complaint.get("id") if isinstance(complaint, dict) else None)
    complaint_num = getattr(complaint, "complaintNumber", None) or (complaint.get("complaintNumber") if isinstance(complaint, dict) else None)
    logger.info(
        "Created complaint from AI analysis [id=%s, complaintNumber=%s]",
        complaint_id,
        complaint_num,
    )
    return ComplaintResponse.model_validate(complaint)


# ==============================================================================
# 4. AI INSIGHTS ON SAVED COMPLAINTS ENDPOINT
# ==============================================================================


@router.post(
    "/{complaint_id}/ai-insights",
    response_model=ComplaintResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_db_connection)],
    summary="Generate AI insights for an existing complaint",
    description="Execute the LangGraph AI pipeline on an already-saved complaint (e.g. created manually) and update its severity, summary, root cause, and CAPA in place.",
)
@limiter.limit(lambda: settings.rate_limit_ai_analysis)
async def generate_complaint_ai_insights(
    request: Request,
    complaint_id: str,
) -> ComplaintResponse:
    """Run AI analysis on an already-saved complaint and persist updated insights idempotently."""
    try:
        existing = await get_complaint_by_id(complaint_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with ID '{complaint_id}' not found.",
        )

    # Build unstructured narrative from complaint entity fields
    narrative_parts = [
        f"Product Name: {getattr(existing, 'productName', '')}",
        f"Batch / Lot Number: {getattr(existing, 'batchNumber', '')}",
        f"Complaint Type: {getattr(existing, 'complaintType', '')}",
        f"Complainant Name: {getattr(existing, 'complainantName', '')}",
        f"Description of Incident: {getattr(existing, 'description', '')}",
    ]
    raw_input = "\n".join(narrative_parts)
    intake_source = getattr(existing, "source", "Manual") or "Manual"

    try:
        state = await analyze_complaint(raw_input=raw_input, source=intake_source)
    except GroqUnavailableError as exc:
        logger.error("AI service failure during /complaints/%s/ai-insights: %s", complaint_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service unavailable",
        )

    # Partial failure logging
    updated_fields = []
    skipped_fields = []
    for key in ("severity", "summary", "capa_recommendation", "root_cause"):
        if state.get(key):
            updated_fields.append(key)
        else:
            skipped_fields.append(key)

    logger.info(
        "Applying AI insights to complaint [%s]: updated=%s, skipped=%s",
        complaint_id,
        updated_fields,
        skipped_fields,
    )

    # Apply updates idempotently to DB
    updated_complaint = await apply_ai_insights_to_complaint(complaint_id, state)
    return ComplaintResponse.model_validate(updated_complaint)
