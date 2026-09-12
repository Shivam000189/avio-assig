"""Plain Text (.txt) Document Parser."""

import re

from app.services.parsers.base import FileParseError, ParsedDocument


def parse_text(filename: str, content: bytes) -> ParsedDocument:
    """Decode raw bytes into normalized UTF-8 text.

    Args:
        filename: Original file name.
        content: Raw binary text content.

    Returns:
        ParsedDocument containing cleaned text and character metrics.

    Raises:
        FileParseError: If the text content is empty.
    """
    try:
        decoded = content.decode("utf-8", errors="replace")
        cleaned_text = re.sub(r"\n{3,}", "\n\n", decoded).strip()

        if not cleaned_text:
            raise FileParseError(
                "Text file is empty",
                "Please provide a text file containing complaint information.",
            )

        return ParsedDocument(
            filename=filename,
            file_type="txt",
            text=cleaned_text,
            metadata={
                "encoding": "utf-8",
                "char_count": len(cleaned_text),
                "line_count": len(cleaned_text.splitlines()),
            },
        )
    except FileParseError:
        raise
    except Exception as exc:
        raise FileParseError(
            f"Failed to process text file: {exc}",
            "Ensure the file contains valid UTF-8 or ASCII plain text.",
        ) from exc
