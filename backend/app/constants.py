"""Domain constants and enumeration types for the QMS system.

Defines all allowed values for string-backed enum fields in Prisma models.
Includes validation helpers used across Pydantic schemas and service layers.
"""

from enum import Enum
from typing import Any


class Severity(str, Enum):
    """Complaint severity classification levels."""

    CRITICAL = "Critical"
    MAJOR = "Major"
    MINOR = "Minor"


class ComplaintStatus(str, Enum):
    """Lifecycle status of a customer complaint."""

    OPEN = "Open"
    IN_PROGRESS = "InProgress"
    CLOSED = "Closed"


class ComplaintType(str, Enum):
    """Category of the pharmaceutical complaint."""

    ADVERSE_EVENT = "AdverseEvent"
    QUALITY_DEFECT = "QualityDefect"
    LABELING_ISSUE = "LabelingIssue"
    PACKAGING_ISSUE = "PackagingIssue"
    DELIVERY_ISSUE = "DeliveryIssue"
    OTHER = "Other"


class ComplaintSource(str, Enum):
    """Intake channel through which the complaint was received."""

    MANUAL = "Manual"
    PDF = "PDF"
    EMAIL = "Email"


class CapaStatus(str, Enum):
    """Workflow status of a Corrective and Preventive Action (CAPA)."""

    RECOMMENDED = "Recommended"
    IN_PROGRESS = "InProgress"
    IMPLEMENTED = "Implemented"
    VERIFIED = "Verified"
    CLOSED = "Closed"


class CapaActionType(str, Enum):
    """Type of CAPA action."""

    CORRECTIVE = "Corrective"
    PREVENTIVE = "Preventive"


class DocumentFileType(str, Enum):
    """Supported file formats for attached complaint documents."""

    PDF = "pdf"
    TXT = "txt"
    EML = "eml"


def is_valid(value: Any, enum_cls: type[Enum]) -> bool:
    """Check whether a given raw value matches any value in the target Enum class.

    Args:
        value: The string or object value to validate.
        enum_cls: The Enum subclass containing allowed values.

    Returns:
        True if value is among enum_cls values, False otherwise.
    """
    if value is None:
        return False
    return any(item.value == value for item in enum_cls)
