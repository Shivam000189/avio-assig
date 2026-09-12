"""Pydantic schemas for Corrective and Preventive Actions (CAPA)."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.constants import CapaActionType, CapaStatus, is_valid


class CapaBase(BaseModel):
    """Base fields for a CAPA entry."""

    actionType: str
    recommendedAction: str = Field(..., min_length=5, max_length=5000)
    actionOwner: str | None = Field(None, max_length=255)
    dueDate: datetime | None = None
    capaStatus: str = CapaStatus.RECOMMENDED.value

    @field_validator("actionType")
    @classmethod
    def validate_action_type(cls, value: str) -> str:
        """Validate that actionType is one of the allowed values."""
        if not is_valid(value, CapaActionType):
            allowed = [e.value for e in CapaActionType]
            raise ValueError(f"Invalid actionType '{value}'. Allowed values: {allowed}")
        return value

    @field_validator("capaStatus")
    @classmethod
    def validate_capa_status(cls, value: str) -> str:
        """Validate that capaStatus is one of the allowed values."""
        if not is_valid(value, CapaStatus):
            allowed = [e.value for e in CapaStatus]
            raise ValueError(f"Invalid capaStatus '{value}'. Allowed values: {allowed}")
        return value


class CapaCreate(CapaBase):
    """Schema for creating a CAPA record."""

    model_config = ConfigDict(extra="forbid")


class CapaUpdate(BaseModel):
    """Schema for partial or upsert update of a CAPA record."""

    actionType: str | None = None
    recommendedAction: str | None = Field(None, min_length=5, max_length=5000)
    actionOwner: str | None = Field(None, max_length=255)
    dueDate: datetime | None = None
    capaStatus: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("actionType")
    @classmethod
    def validate_action_type(cls, value: str | None) -> str | None:
        """Validate actionType if provided."""
        if value is not None and not is_valid(value, CapaActionType):
            allowed = [e.value for e in CapaActionType]
            raise ValueError(f"Invalid actionType '{value}'. Allowed values: {allowed}")
        return value

    @field_validator("capaStatus")
    @classmethod
    def validate_capa_status(cls, value: str | None) -> str | None:
        """Validate capaStatus if provided."""
        if value is not None and not is_valid(value, CapaStatus):
            allowed = [e.value for e in CapaStatus]
            raise ValueError(f"Invalid capaStatus '{value}'. Allowed values: {allowed}")
        return value


class CapaResponse(CapaBase):
    """Response schema for CAPA data."""

    id: str
    complaintId: str

    model_config = ConfigDict(from_attributes=True)
