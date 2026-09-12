"""State definition for the LangGraph Complaint Analysis Pipeline."""

from typing import Any, TypedDict


class ComplaintAnalysisState(TypedDict):
    """Complete mutable working state flowing through the sequential LangGraph pipeline."""

    raw_input: str
    source: str
    extracted: dict[str, Any] | None
    missing_fields: list[str]
    is_complete: bool
    summary: str | None
    severity: str | None
    risk_reasoning: str | None
    recommended_sla_days: int | None
    capa_recommendation: str | None
    capa_action_type: str | None
    root_cause: str | None
    duplicate_of: str | None
    potential_duplicate: dict[str, Any] | None
    duplicate_checked: bool
    llm_errors: list[str]
    iteration: int
