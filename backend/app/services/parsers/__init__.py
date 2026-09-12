"""Document parsers package with magic-byte content sniffing and polyglot file protection.

================================================================================
SECURITY & CONTENT SNIFFING ARCHITECTURE:
Relying solely on user-supplied file extensions (e.g. `.pdf` or `.txt`) exposes
the application to extension-spoofing and polyglot payload attacks (such as
disguising Windows PE executables `MZ` or ELF binaries as plain text files).

`parse_file()` enforces a two-layer validation:
1. Magic-Byte Sniffing: Validates the initial bytes (`%PDF` for PDFs, standard
   RFC headers for EML, binary signature rejection for `.exe`/`.dll`/`.elf`).
2. Type-Specific Dispatch: Dispatches to dedicated parsers with strict size
   and encoding constraints.
================================================================================
"""

import os
import re

from app.services.parsers.base import FileParseError, ParsedDocument
from app.services.parsers.email_parser import parse_email
from app.services.parsers.pdf_parser import parse_pdf
from app.services.parsers.text_parser import parse_text

# Dangerous executable magic byte signatures to explicitly reject
DANGEROUS_MAGIC_HEADERS = (
    b"MZ",                # Windows PE EXE / DLL
    b"\x7fELF",           # Linux ELF binary
    b"\xca\xfe\xba\xbe",   # Java class file / Mach-O Fat Binary
    b"\xfe\xed\xfa\xce",   # Mach-O 32-bit
    b"\xfe\xed\xfa\xcf",   # Mach-O 64-bit
    b"\xce\xfa\xed\xfe",   # Mach-O 32-bit (reverse)
    b"\xcf\xfa\xed\xfe",   # Mach-O 64-bit (reverse)
    b"\x1f\x8b",           # GZIP archive (unless decompressed)
    b"PK\x03\x04",         # ZIP / JAR (unless explicitly parsed)
    b"Rar!\x1a\x07",       # RAR archive
    b"7z\xbc\xaf\x27\x1c", # 7z archive
)

# Prohibited dangerous file extensions
PROHIBITED_EXTENSIONS = {
    ".exe", ".dll", ".so", ".dylib", ".bat", ".cmd", ".sh", ".ps1", ".vbs",
    ".js", ".jsx", ".ts", ".tsx", ".py", ".pyc", ".pyd", ".jar", ".war",
    ".php", ".asp", ".aspx", ".jsp", ".cgi", ".pl", ".bin", ".scr",
}


def sanitize_filename(filename: str) -> str:
    """Sanitize uploaded filename to prevent directory traversal and null-byte attacks."""
    if not filename:
        return "unnamed_document.txt"

    # Strip null bytes and control characters
    clean_name = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", filename)
    # Extract only the base name (strip directory traversal like ../ or ..\)
    clean_name = os.path.basename(clean_name.replace("\\", "/")).strip()
    # Remove leading dots to avoid hidden files
    clean_name = clean_name.lstrip(".")
    return clean_name or "unnamed_document.txt"


def parse_file(filename: str, content: bytes) -> ParsedDocument:
    """Detect file type via magic bytes + extension and parse into normalized ParsedDocument.

    Args:
        filename: Name of the uploaded file.
        content: Raw binary byte stream.

    Returns:
        ParsedDocument containing cleaned text and format metadata.

    Raises:
        FileParseError: If the file type is unsupported, spoofed, executable, or unparseable.
    """
    if not content:
        raise FileParseError("Uploaded file is empty.", "Provide a non-empty document.")

    safe_filename = sanitize_filename(filename)
    _, ext = os.path.splitext(safe_filename.lower())

    if ext in PROHIBITED_EXTENSIONS:
        raise FileParseError(
            f"Prohibited executable or script extension '{ext}'.",
            "Upload only PDF, TXT, or EML customer complaint documents.",
        )

    # 1. Security Check: Block binary executables & archives
    for magic in DANGEROUS_MAGIC_HEADERS:
        if content.startswith(magic):
            raise FileParseError(
                "Executable or archive binary file rejected.",
                "Binary files cannot be processed. Upload only valid PDF, TXT, or EML documents.",
            )

    # 2. PDF Detection: Starts with '%PDF'
    if content.startswith(b"%PDF") or ext == ".pdf":
        if not content.startswith(b"%PDF"):
            raise FileParseError(
                "Invalid PDF document: missing '%PDF' header.",
                "Ensure the uploaded file is a valid PDF document.",
            )
        return parse_pdf(safe_filename, content)

    # 3. EML Detection: Starts with 'From ' or contains RFC-822 headers or has .eml extension
    if (
        content.startswith(b"From ")
        or b"Subject:" in content[:1024]
        or b"Received:" in content[:1024]
        or ext == ".eml"
    ):
        return parse_email(safe_filename, content)

    # 4. Text File Detection:
    if ext == ".txt":
        return parse_text(safe_filename, content)

    # If extension is unsupported and couldn't be sniffed
    raise FileParseError(
        f"Unsupported file format '{ext}'.",
        "Allowed file formats are .pdf, .txt, and .eml.",
    )


__all__ = [
    "FileParseError",
    "ParsedDocument",
    "parse_email",
    "parse_file",
    "parse_pdf",
    "parse_text",
]
