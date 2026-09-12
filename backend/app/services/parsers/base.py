"""Base classes and data structures for the document parsing subsystem."""

from dataclasses import dataclass, field
from typing import Any

from app.exceptions import FileParseError


@dataclass
class ParsedDocument:
    """Normalized output produced by document format parsers."""

    filename: str
    file_type: str  # "pdf" | "txt" | "eml"
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = ["FileParseError", "ParsedDocument"]
