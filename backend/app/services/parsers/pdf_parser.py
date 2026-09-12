"""PDF Document Parser using pypdf."""

import io
import logging
import re

from pypdf import PdfReader

from app.services.parsers.base import FileParseError, ParsedDocument

logger = logging.getLogger(__name__)


def parse_pdf(filename: str, content: bytes) -> ParsedDocument:
    """Extract plain text from a text-based PDF document.

    Args:
        filename: Original uploaded file name.
        content: Raw binary payload of the PDF file.

    Returns:
        ParsedDocument with extracted text and page count metadata.

    Raises:
        FileParseError: If the PDF is encrypted, corrupt, or contains <20 chars (scanned/image-based).
    """
    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                raise FileParseError(
                    "Encrypted PDF document",
                    "Please upload an unencrypted, password-free PDF file.",
                )

        extracted_pages: list[str] = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                extracted_pages.append(page_text.strip())

        full_text = "\n\n".join(extracted_pages)
        # Collapse 3+ consecutive newlines into 2
        cleaned_text = re.sub(r"\n{3,}", "\n\n", full_text).strip()

        if len(cleaned_text) < 20:
            raise FileParseError(
                "PDF appears to be image-based or empty",
                "Upload a text-based PDF or paste the complaint text manually.",
            )

        return ParsedDocument(
            filename=filename,
            file_type="pdf",
            text=cleaned_text,
            metadata={"page_count": len(reader.pages), "extracted_chars": len(cleaned_text)},
        )

    except FileParseError:
        raise
    except Exception as exc:
        logger.error("Failed to parse PDF '%s': %s", filename, exc)
        raise FileParseError(
            f"Failed to read PDF structure: {exc}",
            "Ensure the PDF file is not corrupted and is text-based.",
        ) from exc
