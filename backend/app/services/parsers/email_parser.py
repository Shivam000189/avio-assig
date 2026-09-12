"""RFC-822 Email (.eml) Document Parser."""

import email
from email import policy
import html
import re

from app.services.parsers.base import FileParseError, ParsedDocument


def _strip_html(html_str: str) -> str:
    """Strip HTML tags using regex and unescape entities without external deps."""
    text_only = re.sub(r"<[^<]+?>", " ", html_str)
    unescaped = html.unescape(text_only)
    return re.sub(r"\s+", " ", unescaped).strip()


def parse_email(filename: str, content: bytes) -> ParsedDocument:
    """Parse an RFC-822 formatted .eml email file into structured metadata and text body.

    Args:
        filename: Original file name.
        content: Raw binary email bytes.

    Returns:
        ParsedDocument with extracted header fields and sanitized body text.

    Raises:
        FileParseError: If email structure cannot be decoded.
    """
    try:
        msg = email.message_from_bytes(content, policy=policy.default)

        # Extract standard message headers
        sender = str(msg.get("From", "Unknown Sender"))
        subject = str(msg.get("Subject", "No Subject"))
        date_header = str(msg.get("Date", "Unknown Date"))
        to_header = str(msg.get("To", "Unknown Recipient"))

        body_text = ""

        if msg.is_multipart():
            # First pass: look for text/plain
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    body_text = part.get_content()
                    break

            # Second pass: fallback to text/html if text/plain is missing
            if not body_text:
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))
                    if content_type == "text/html" and "attachment" not in content_disposition:
                        raw_html = part.get_content()
                        body_text = _strip_html(raw_html)
                        break
        else:
            if msg.get_content_type() == "text/html":
                body_text = _strip_html(msg.get_content())
            else:
                body_text = msg.get_content()

        body_text = re.sub(r"\n{3,}", "\n\n", str(body_text)).strip()

        if not body_text and not subject:
            raise FileParseError(
                "Email contains neither subject nor readable body",
                "Ensure the .eml file contains valid email headers and message content.",
            )

        full_document_text = (
            f"Subject: {subject}\n"
            f"From: {sender}\n"
            f"To: {to_header}\n"
            f"Date: {date_header}\n\n"
            f"{body_text}"
        )

        metadata = {
            "from": sender,
            "subject": subject,
            "date": date_header,
            "to": to_header,
        }

        return ParsedDocument(
            filename=filename,
            file_type="eml",
            text=full_document_text.strip(),
            metadata=metadata,
        )

    except FileParseError:
        raise
    except Exception as exc:
        raise FileParseError(
            f"Failed to parse email message: {exc}",
            "Verify that the uploaded file is a valid RFC-822 .eml document.",
        ) from exc
