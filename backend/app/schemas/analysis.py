"""Pydantic schemas for the AI Complaint Analysis and Document Upload Pipeline."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.constants import (
    CapaActionType,
    ComplaintSource,
    ComplaintStatus,
    ComplaintType,
    Severity,
    is_valid,
)


class AnalysisRequest(BaseModel):
    """Input payload for raw complaint text analysis."""

    text: str = Field(
        ...,
        min_length=30,
        max_length=20000,
        description="Raw complaint text (email body, transcribed call, incident narrative).",
    )
    source: str = Field(
        default=ComplaintSource.MANUAL.value,
        description="Intake channel (Manual, PDF, Email).",
    )

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        """Validate source against allowed intake channels."""
        if not is_valid(value, ComplaintSource):
            allowed = [e.value for e in ComplaintSource]
            raise ValueError(f"Invalid source '{value}'. Allowed values: {allowed}")
        return value

    model_config = ConfigDict(extra="forbid")


class DocumentMetadata(BaseModel):
    """Parsed document metadata descriptor."""

    filename: str
    fileType: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class PotentialDuplicateInfo(BaseModel):
    """Potential duplicate or quality trend association descriptor."""

    complaintId: str | None = None
    complaintNumber: str | None = None
    similarity: str = "Low"  # High | Medium | Low
    explanation: str | None = None
    isPossibleTrend: bool = False

    model_config = ConfigDict(from_attributes=True)


class AnalysisResponse(BaseModel):
    """Complete structured response from the multi-node LangGraph analysis pipeline."""

    rawInput: str
    source: str
    extracted: dict[str, Any] | None = None
    missingFields: list[str] = []
    isComplete: bool = False
    summary: str | None = None
    severity: str | None = None
    riskReasoning: str | None = None
    recommendedSlaDays: int | None = None
    capaRecommendation: str | None = None
    capaActionType: str | None = None
    rootCause: str | None = None
    duplicateOf: str | None = None
    potentialDuplicate: PotentialDuplicateInfo | None = None
    duplicateChecked: bool = False
    warnings: list[str] = []
    document: DocumentMetadata | None = None

    model_config = ConfigDict(from_attributes=True)


class ExtractedComplaintData(BaseModel):
    """Normalized structured data extracted from AI analysis."""

    complainantName: str = Field(..., min_length=1, max_length=255)
    email: str | None = None
    phone: str | None = None
    productName: str = Field(..., min_length=1, max_length=255)
    batchNumber: str = Field(..., pattern=r"^[A-Z0-9-]{4,20}$")
    expiryDate: datetime | None = None
    manufactureDate: datetime | None = None
    complaintType: str = Field(default=ComplaintType.OTHER.value)
    description: str = Field(..., min_length=20, max_length=5000)
    country: str | None = None


class CreateFromAnalysisRequest(BaseModel):
    """Payload for persisting an analyzed and user-approved complaint with linked records."""

    extracted: ExtractedComplaintData
    severity: str | None = None
    summary: str | None = None
    capaRecommendation: str | None = None
    capaActionType: str | None = None
    rootCause: str | None = None
    source: str = Field(default=ComplaintSource.MANUAL.value)
    status: str = Field(default=ComplaintStatus.OPEN.value)
    documentId: str | None = None

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str | None) -> str | None:
        """Validate severity against allowed domain values if provided."""
        if value is not None and not is_valid(value, Severity):
            allowed = [e.value for e in Severity]
            raise ValueError(f"Invalid severity '{value}'. Allowed values: {allowed}")
        return value

    @field_validator("capaActionType")
    @classmethod
    def validate_capa_action_type(cls, value: str | None) -> str | None:
        """Validate CAPA action type if provided."""
        if value is not None and not is_valid(value, CapaActionType):
            allowed = [e.value for e in CapaActionType]
            raise ValueError(f"Invalid capaActionType '{value}'. Allowed values: {allowed}")
        return value

    model_config = ConfigDict(extra="forbid")
