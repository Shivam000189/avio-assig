"""Pydantic schemas for ComplaintDocument."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator

from app.constants import DocumentFileType, is_valid


class DocumentBase(BaseModel):
    """Base fields for an attached document."""

    filename: str
    fileType: str
    extractedText: str | None = None

    @field_validator("fileType")
    @classmethod
    def validate_file_type(cls, value: str) -> str:
        """Validate that fileType is one of the supported document formats."""
        if not is_valid(value, DocumentFileType):
            allowed = [e.value for e in DocumentFileType]
            raise ValueError(f"Invalid fileType '{value}'. Allowed values: {allowed}")
        return value


class DocumentCreate(DocumentBase):
    """Schema for attaching a new document."""

    pass


class DocumentResponse(DocumentBase):
    """Response schema for document data."""

    id: str
    complaintId: str
    uploadedAt: datetime

    model_config = ConfigDict(from_attributes=True)
