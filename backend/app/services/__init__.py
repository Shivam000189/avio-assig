"""Services and repositories package."""

from app.services.complaint_repository import (
    apply_ai_insights_to_complaint,
    attach_document_to_complaint,
    count_complaints,
    create_complaint,
    create_complaint_from_analysis,
    delete_complaint,
    get_capa_by_complaint_id,
    get_complaint_by_id,
    get_complaints_by_batch,
    get_stats,
    list_complaints,
    update_complaint,
    upsert_capa_for_complaint,
)
from app.services.duplicate_service import fetch_candidates

__all__ = [
    "apply_ai_insights_to_complaint",
    "attach_document_to_complaint",
    "count_complaints",
    "create_complaint",
    "create_complaint_from_analysis",
    "delete_complaint",
    "fetch_candidates",
    "get_capa_by_complaint_id",
    "get_complaint_by_id",
    "get_complaints_by_batch",
    "get_stats",
    "list_complaints",
    "update_complaint",
    "upsert_capa_for_complaint",
]
