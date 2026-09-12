"""Repository layer for database access operations on Complaint and CAPA entities.

Contains pure data access functions using Prisma. No AI or business logic
resides here. All functions operate asynchronously and handle Prisma relations.

================================================================================
PHASE 4 AI PIPELINE INTEGRATION HOOK:
In Phase 4, the LangGraph AI triage pipeline hooks into this layer:
1. Intake: When a new complaint is created via `create_complaint()`, the raw
   payload is passed to `agent.triage_graph.ainvoke(...)`.
2. Enrichment: The AI pipeline classifies `severity`, identifies `rootCause`,
   generates `aiSummary`, and recommends a `CAPA` action.
3. Persistence: The enriched predictions call `create_complaint_from_analysis()`
   or `update_complaint()` and `upsert_capa_for_complaint()` to persist AI findings.
================================================================================
"""

from datetime import datetime, timezone
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from prisma.models import CAPA, Complaint, ComplaintDocument
else:
    try:
        from prisma.models import CAPA, Complaint, ComplaintDocument
    except (ImportError, AttributeError):
        CAPA = Any
        Complaint = Any
        ComplaintDocument = Any

from app.constants import ComplaintStatus, ComplaintType, Severity
from app.database import prisma
from app.exceptions import NotFoundError
from app.schemas.analysis import CreateFromAnalysisRequest
from app.schemas.capa import CapaCreate, CapaUpdate
from app.schemas.complaint import ComplaintCreate, ComplaintUpdate

logger = logging.getLogger(__name__)

INCLUDE_RELATIONS = {
    "documents": True,
    "capa": True,
    "summary": True,
}


def _get_attr(obj: Any, key: str, default: Any = None) -> Any:
    """Safely get an attribute from either a Prisma model or dictionary."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _build_where_clause(
    status: str | None = None,
    severity: str | None = None,
    complaint_type: str | None = None,
    search: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> dict[str, Any]:
    """Helper to build Prisma where filter dictionary from query parameters."""
    where: dict[str, Any] = {}
    if status is not None:
        where["status"] = status
    if severity is not None:
        where["severity"] = severity
    if complaint_type is not None:
        where["complaintType"] = complaint_type

    if search:
        where["OR"] = [
            {"productName": {"contains": search, "mode": "insensitive"}},
            {"batchNumber": {"contains": search, "mode": "insensitive"}},
            {"complainantName": {"contains": search, "mode": "insensitive"}},
            {"description": {"contains": search, "mode": "insensitive"}},
        ]

    if created_from is not None or created_to is not None:
        created_at_filter: dict[str, datetime] = {}
        if created_from is not None:
            created_at_filter["gte"] = created_from
        if created_to is not None:
            created_at_filter["lte"] = created_to
        where["createdAt"] = created_at_filter

    return where


async def list_complaints(
    status: str | None = None,
    severity: str | None = None,
    complaint_type: str | None = None,
    search: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Complaint], int]:
    """Retrieve paginated complaints matching search/filter parameters.

    Returns:
        A tuple of (items, total_count).
    """
    where = _build_where_clause(
        status=status,
        severity=severity,
        complaint_type=complaint_type,
        search=search,
        created_from=created_from,
        created_to=created_to,
    )

    total = await prisma.complaint.count(where=where)
    complaints = await prisma.complaint.find_many(
        where=where,
        include=INCLUDE_RELATIONS,
        order={"createdAt": "desc"},
        skip=skip,
        take=limit,
    )
    return complaints, total


async def get_complaint_by_id(complaint_id: str) -> Complaint:
    """Retrieve a single complaint by its unique ID.

    Raises:
        NotFoundError: If no complaint exists with the specified ID.
    """
    complaint = await prisma.complaint.find_unique(
        where={"id": complaint_id},
        include=INCLUDE_RELATIONS,
    )
    if not complaint:
        raise NotFoundError(f"Complaint with ID '{complaint_id}' not found.")
    return complaint


async def get_complaints_by_batch(batch_number: str) -> list[Complaint]:
    """Retrieve all complaints associated with a specific manufacturing batch number.

    NOTE: This query is critical for Phase 6 (Duplicate Detection & Batch Trend Analysis).
    """
    return await prisma.complaint.find_many(
        where={"batchNumber": batch_number},
        include=INCLUDE_RELATIONS,
        order={"createdAt": "desc"},
    )


async def create_complaint(data: ComplaintCreate) -> Complaint:
    """Create a new complaint record with an auto-generated complaint number."""
    current_year = datetime.now(timezone.utc).year
    total_count = await prisma.complaint.count()
    complaint_number = f"CMP-{current_year}-{total_count + 1:04d}"

    create_data = data.model_dump(exclude_unset=True)
    create_data["complaintNumber"] = complaint_number

    created = await prisma.complaint.create(
        data=create_data,
        include=INCLUDE_RELATIONS,
    )
    return created


async def create_complaint_from_analysis(data: CreateFromAnalysisRequest) -> Complaint:
    """Create a Complaint along with its linked ComplaintSummary and optional CAPA atomically.

    ============================================================================
    GMP AUDIT TRAIL INTEGRITY RATIONALE:
    In pharmaceutical manufacturing compliance (FDA 21 CFR Part 11 / Annex 11),
    partial database states (e.g. an orphan complaint created without its mandatory
    summary or an incomplete CAPA record) invalidate the data integrity audit trail.
    Wrapping the creation of the parent complaint, summary, and CAPA in an atomic
    database transaction ensures all records commit together or cleanly rollback.
    ============================================================================
    """
    current_year = datetime.now(timezone.utc).year
    total_count = await prisma.complaint.count()
    complaint_number = f"CMP-{current_year}-{total_count + 1:04d}"

    extracted_dict = data.extracted.model_dump(exclude_unset=True)

    create_payload: dict[str, Any] = {
        "complaintNumber": complaint_number,
        "complainantName": extracted_dict.get("complainantName", "Unknown Complainant"),
        "email": extracted_dict.get("email"),
        "phone": extracted_dict.get("phone"),
        "productName": extracted_dict.get("productName", "Unknown Product"),
        "batchNumber": extracted_dict.get("batchNumber", "UNKNOWN"),
        "expiryDate": extracted_dict.get("expiryDate"),
        "manufactureDate": extracted_dict.get("manufactureDate"),
        "complaintType": extracted_dict.get("complaintType", "Other"),
        "description": extracted_dict.get("description", ""),
        "country": extracted_dict.get("country"),
        "severity": data.severity,
        "status": data.status,
        "source": data.source,
        "aiSummary": data.summary,
        "rootCause": data.rootCause,
    }

    # Atomic nested summary creation
    if data.summary:
        create_payload["summary"] = {
            "create": {
                "summaryText": data.summary,
            }
        }

    # Atomic nested CAPA creation (only if recommended)
    if data.capaRecommendation:
        create_payload["capa"] = {
            "create": {
                "actionType": data.capaActionType or "Corrective",
                "recommendedAction": data.capaRecommendation,
                "capaStatus": "Recommended",
            }
        }

    # Prisma nested creates are executed within an atomic database transaction
    created = await prisma.complaint.create(
        data=create_payload,
        include=INCLUDE_RELATIONS,
    )
    return created


async def attach_document_to_complaint(
    complaint_id: str,
    filename: str,
    file_type: str,
    extracted_text: str | None = None,
) -> ComplaintDocument:
    """Store an uploaded document record associated with a complaint.

    Raises:
        NotFoundError: If complaint_id is not found.
    """
    complaint = await prisma.complaint.find_unique(where={"id": complaint_id})
    if not complaint:
        raise NotFoundError(f"Complaint with ID '{complaint_id}' not found.")

    doc = await prisma.complaintdocument.create(
        data={
            "complaintId": complaint_id,
            "filename": filename,
            "fileType": file_type,
            "extractedText": extracted_text,
        }
    )
    return doc


async def update_complaint(
    complaint_id: str,
    data: ComplaintUpdate,
) -> tuple[Complaint, list[str]]:
    """Update an existing complaint record by ID with partial update semantics.

    Returns:
        A tuple of (updated_complaint, modified_field_names) for audit logging.

    Raises:
        NotFoundError: If the complaint does not exist.
    """
    existing = await prisma.complaint.find_unique(where={"id": complaint_id})
    if not existing:
        raise NotFoundError(f"Complaint with ID '{complaint_id}' not found.")

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        full_existing = await get_complaint_by_id(complaint_id)
        return full_existing, []

    existing_manufacture_date = _get_attr(existing, "manufactureDate")
    existing_expiry_date = _get_attr(existing, "expiryDate")
    manufacture_date = update_data.get("manufactureDate", existing_manufacture_date)
    expiry_date = update_data.get("expiryDate", existing_expiry_date)
    if manufacture_date and expiry_date and expiry_date <= manufacture_date:
        raise ValueError("expiryDate must be chronologically after manufactureDate.")

    modified_fields = list(update_data.keys())

    updated = await prisma.complaint.update(
        where={"id": complaint_id},
        data=update_data,
        include=INCLUDE_RELATIONS,
    )
    return updated, modified_fields


async def delete_complaint(complaint_id: str) -> str:
    """Delete a complaint record and cascade-delete its documents, summary, and CAPA.

    Returns:
        The complaintNumber of the deleted record.

    Raises:
        NotFoundError: If the complaint does not exist.
    """
    existing = await prisma.complaint.find_unique(where={"id": complaint_id})
    if not existing:
        raise NotFoundError(f"Complaint with ID '{complaint_id}' not found.")

    complaint_number = _get_attr(existing, "complaintNumber", "UNKNOWN")

    await prisma.complaint.delete(where={"id": complaint_id})
    return complaint_number


async def count_complaints(
    status: str | None = None,
    severity: str | None = None,
) -> int:
    """Count complaints matching optional status and severity filters."""
    where: dict[str, Any] = {}
    if status is not None:
        where["status"] = status
    if severity is not None:
        where["severity"] = severity
    return await prisma.complaint.count(where=where)


async def get_stats() -> dict[str, Any]:
    """Compute aggregate complaint metrics in a single database query."""
    rows = await prisma.complaint.find_many()

    total = len(rows)

    by_status = {s.value: 0 for s in ComplaintStatus}
    by_severity = {s.value: 0 for s in Severity}
    open_by_type = {t.value: 0 for t in ComplaintType}

    for row in rows:
        status_val = _get_attr(row, "status")
        if status_val in by_status:
            by_status[status_val] += 1

        severity_val = _get_attr(row, "severity")
        if severity_val in by_severity:
            by_severity[severity_val] += 1

        if status_val in (ComplaintStatus.OPEN.value, ComplaintStatus.IN_PROGRESS.value):
            type_val = _get_attr(row, "complaintType")
            if type_val in open_by_type:
                open_by_type[type_val] += 1

    return {
        "total": total,
        "byStatus": by_status,
        "bySeverity": by_severity,
        "openByType": open_by_type,
    }


async def get_capa_by_complaint_id(complaint_id: str) -> CAPA:
    """Retrieve the CAPA action associated with a specific complaint.

    Raises:
        NotFoundError: If the complaint does not exist or has no CAPA.
    """
    complaint = await prisma.complaint.find_unique(where={"id": complaint_id})
    if not complaint:
        raise NotFoundError(f"Complaint with ID '{complaint_id}' not found.")

    capa = await prisma.capa.find_unique(where={"complaintId": complaint_id})
    if not capa:
        raise NotFoundError(f"No CAPA found for complaint '{complaint_id}'.")
    return capa


async def upsert_capa_for_complaint(
    complaint_id: str,
    data: CapaCreate | CapaUpdate,
) -> CAPA:
    """Create or update a CAPA record for a specific complaint.

    Raises:
        NotFoundError: If the complaint does not exist.
    """
    complaint = await prisma.complaint.find_unique(where={"id": complaint_id})
    if not complaint:
        raise NotFoundError(f"Complaint with ID '{complaint_id}' not found.")

    payload = data.model_dump(exclude_unset=True)

    create_payload = {
        "complaintId": complaint_id,
        "actionType": payload.get("actionType", "Corrective"),
        "recommendedAction": payload.get("recommendedAction", "Pending evaluation"),
        "actionOwner": payload.get("actionOwner"),
        "dueDate": payload.get("dueDate"),
        "capaStatus": payload.get("capaStatus", "Recommended"),
    }

    capa = await prisma.capa.upsert(
        where={"complaintId": complaint_id},
        data={
            "create": create_payload,
            "update": payload,
        },
    )
    return capa


async def apply_ai_insights_to_complaint(
    complaint_id: str,
    state: dict[str, Any],
) -> Complaint:
    """Apply LangGraph AI analysis predictions to an existing complaint record.

    Updates severity, aiSummary, rootCause in place, and upserts ComplaintSummary and CAPA.

    Raises:
        NotFoundError: If the complaint does not exist.
    """
    existing = await prisma.complaint.find_unique(
        where={"id": complaint_id},
        include=INCLUDE_RELATIONS,
    )
    if not existing:
        raise NotFoundError(f"Complaint with ID '{complaint_id}' not found.")

    update_fields: dict[str, Any] = {}
    if state.get("severity"):
        update_fields["severity"] = state["severity"]
    if state.get("summary"):
        update_fields["aiSummary"] = state["summary"]
    if state.get("root_cause"):
        update_fields["rootCause"] = state["root_cause"]

    # 1. Update Complaint fields in place
    if update_fields:
        await prisma.complaint.update(
            where={"id": complaint_id},
            data=update_fields,
        )

    # 2. Upsert ComplaintSummary
    if state.get("summary"):
        await prisma.complaintsummary.upsert(
            where={"complaintId": complaint_id},
            data={
                "create": {
                    "complaintId": complaint_id,
                    "summaryText": state["summary"],
                },
                "update": {
                    "summaryText": state["summary"],
                },
            },
        )

    # 3. Upsert CAPA (only if recommended)
    if state.get("capa_recommendation"):
        await prisma.capa.upsert(
            where={"complaintId": complaint_id},
            data={
                "create": {
                    "complaintId": complaint_id,
                    "actionType": state.get("capa_action_type") or "Corrective",
                    "recommendedAction": state["capa_recommendation"],
                    "capaStatus": "Recommended",
                },
                "update": {
                    "actionType": state.get("capa_action_type") or "Corrective",
                    "recommendedAction": state["capa_recommendation"],
                },
            },
        )

    # Return refreshed complaint with all relations loaded
    refreshed = await prisma.complaint.find_unique(
        where={"id": complaint_id},
        include=INCLUDE_RELATIONS,
    )
    return refreshed or existing
