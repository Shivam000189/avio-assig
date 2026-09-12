"""Pydantic schemas for Complaints, including pagination, stats, and strict validation."""

from datetime import datetime
from typing import Any
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.constants import (
    ComplaintSource,
    ComplaintStatus,
    ComplaintType,
    Severity,
    is_valid,
)
from app.schemas.capa import CapaResponse
from app.schemas.document import DocumentResponse

# ------------------------------------------------------------------------------
# SECURITY NOTE — MASS ASSIGNMENT PROTECTION:
# Mass assignment vulnerabilities occur when clients inject sensitive internal
# or generated fields (such as system IDs, complaint numbers, or audit stamps)
# directly into creation/update payloads. By setting `extra="forbid"` on input
# schemas and explicitly omitting `complaintNumber` from them, we guarantee that
# human-readable complaint identifiers are strictly server-generated.
# ------------------------------------------------------------------------------


class ComplaintSummaryResponse(BaseModel):
    """Response schema for ComplaintSummary."""

    id: str
    complaintId: str
    summaryText: str
    generatedAt: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplaintBase(BaseModel):
    """Base fields for a customer complaint."""

    complainantName: str = Field(..., min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    productName: str = Field(..., min_length=1, max_length=255)
    batchNumber: str = Field(
        ...,
        pattern=r"^[A-Z0-9-]{4,20}$",
        description="Pharmaceutical lot or batch number (4-20 alphanumeric characters or hyphens).",
    )
    expiryDate: datetime | None = None
    manufactureDate: datetime | None = None
    complaintType: str
    description: str = Field(
        ...,
        min_length=20,
        max_length=5000,
        description="Detailed description of the customer complaint (min 20 characters).",
    )
    severity: str | None = None
    status: str = ComplaintStatus.OPEN.value
    source: str = ComplaintSource.MANUAL.value
    country: str | None = Field(None, max_length=100)
    aiSummary: str | None = None
    rootCause: str | None = None

    @field_validator("complaintType")
    @classmethod
    def validate_complaint_type(cls, value: str) -> str:
        """Validate complaintType against allowed domain values."""
        if not is_valid(value, ComplaintType):
            allowed = [e.value for e in ComplaintType]
            raise ValueError(f"Invalid complaintType '{value}'. Allowed values: {allowed}")
        return value

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str | None) -> str | None:
        """Validate severity against allowed domain values if provided."""
        if value is not None and not is_valid(value, Severity):
            allowed = [e.value for e in Severity]
            raise ValueError(f"Invalid severity '{value}'. Allowed values: {allowed}")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        """Validate status against allowed domain values."""
        if not is_valid(value, ComplaintStatus):
            allowed = [e.value for e in ComplaintStatus]
            raise ValueError(f"Invalid status '{value}'. Allowed values: {allowed}")
        return value

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        """Validate source against allowed domain values."""
        if not is_valid(value, ComplaintSource):
            allowed = [e.value for e in ComplaintSource]
            raise ValueError(f"Invalid source '{value}'. Allowed values: {allowed}")
        return value

    @model_validator(mode="after")
    def validate_date_order(self) -> "ComplaintBase":
        """Ensure expiryDate is strictly after manufactureDate when both are supplied."""
        if self.manufactureDate and self.expiryDate:
            if self.expiryDate <= self.manufactureDate:
                raise ValueError("expiryDate must be chronologically after manufactureDate.")
        return self


class ComplaintCreate(ComplaintBase):
    """Payload schema for creating a new complaint.

    Extra attributes like `complaintNumber` or `id` are strictly forbidden.
    """

    model_config = ConfigDict(extra="forbid")


class ComplaintUpdate(BaseModel):
    """Payload schema for updating an existing complaint.

    Supports partial updates. Explicitly passing null clears a nullable field.
    Extra fields (e.g. complaintNumber) are strictly forbidden.
    """

    complainantName: str | None = Field(None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    productName: str | None = Field(None, min_length=1, max_length=255)
    batchNumber: str | None = Field(
        None,
        pattern=r"^[A-Z0-9-]{4,20}$",
        description="Pharmaceutical lot or batch number.",
    )
    expiryDate: datetime | None = None
    manufactureDate: datetime | None = None
    complaintType: str | None = None
    description: str | None = Field(None, min_length=20, max_length=5000)
    severity: str | None = None
    status: str | None = None
    source: str | None = None
    country: str | None = Field(None, max_length=100)
    aiSummary: str | None = None
    rootCause: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("complaintType")
    @classmethod
    def validate_complaint_type(cls, value: str | None) -> str | None:
        """Validate complaintType if provided."""
        if value is not None and not is_valid(value, ComplaintType):
            allowed = [e.value for e in ComplaintType]
            raise ValueError(f"Invalid complaintType '{value}'. Allowed values: {allowed}")
        return value

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str | None) -> str | None:
        """Validate severity if provided."""
        if value is not None and not is_valid(value, Severity):
            allowed = [e.value for e in Severity]
            raise ValueError(f"Invalid severity '{value}'. Allowed values: {allowed}")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        """Validate status if provided."""
        if value is not None and not is_valid(value, ComplaintStatus):
            allowed = [e.value for e in ComplaintStatus]
            raise ValueError(f"Invalid status '{value}'. Allowed values: {allowed}")
        return value

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str | None) -> str | None:
        """Validate source if provided."""
        if value is not None and not is_valid(value, ComplaintSource):
            allowed = [e.value for e in ComplaintSource]
            raise ValueError(f"Invalid source '{value}'. Allowed values: {allowed}")
        return value

    @model_validator(mode="after")
    def validate_date_order(self) -> "ComplaintUpdate":
        """Ensure expiryDate is strictly after manufactureDate when both are supplied."""
        if self.manufactureDate and self.expiryDate:
            if self.expiryDate <= self.manufactureDate:
                raise ValueError("expiryDate must be chronologically after manufactureDate.")
        return self


class ComplaintResponse(BaseModel):
    """Complete response schema for a complaint including relations and system metadata."""

    id: str
    complaintNumber: str
    complainantName: str
    email: str | None = None
    phone: str | None = None
    productName: str
    batchNumber: str
    expiryDate: datetime | None = None
    manufactureDate: datetime | None = None
    complaintType: str
    description: str
    severity: str | None = None
    status: str
    source: str
    country: str | None = None
    aiSummary: str | None = None
    rootCause: str | None = None
    createdAt: datetime
    updatedAt: datetime
    documents: list[DocumentResponse] = []
    capa: CapaResponse | None = None
    summary: ComplaintSummaryResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedComplaintsResponse(BaseModel):
    """Paginated envelope for complaint listings."""

    total: int
    skip: int
    limit: int
    items: list[ComplaintResponse]


class ComplaintStatsResponse(BaseModel):
    """Statistical summary aggregations for dashboard analytics."""

    total: int
    byStatus: dict[str, int]
    bySeverity: dict[str, int]
    openByType: dict[str, int]
