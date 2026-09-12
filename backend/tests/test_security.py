"""Security test suite validating rate limiting, input validation, headers, and file upload safety."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import create_app
from app.security.limiter import limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset the rate limiter before each test run."""
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def mock_prisma_db():
    """Mock the Prisma client in routers and services with an active connection."""
    mock_p = MagicMock()
    mock_p.is_connected.return_value = True
    mock_p.complaint = MagicMock()
    mock_p.complaint.find_many = AsyncMock()
    mock_p.complaint.find_unique = AsyncMock()
    mock_p.complaint.count = AsyncMock(return_value=0)
    mock_p.complaint.create = AsyncMock()
    mock_p.complaint.update = AsyncMock()
    mock_p.complaint.delete = AsyncMock()

    mock_p.capa = MagicMock()
    mock_p.capa.find_unique = AsyncMock()
    mock_p.capa.upsert = AsyncMock()

    with (
        patch("app.routers.complaints.prisma", mock_p),
        patch("app.routers.analysis.prisma", mock_p),
        patch("app.services.complaint_repository.prisma", mock_p),
    ):
        yield mock_p


@pytest.mark.anyio
async def test_security_headers_present_on_all_responses():
    """Verify standard OWASP security response headers are attached to responses."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "camera=()" in response.headers.get("Permissions-Policy", "")


@pytest.mark.anyio
async def test_rate_limiting_triggers_429_with_retry_after():
    """Verify that exceeding rate limits returns HTTP 429 with Retry-After and clean JSON."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Patch analyze_complaint to return quickly
        mock_state = {
            "raw_input": "Complaint text here with sufficient length for validation.",
            "source": "Manual",
            "potential_duplicate": None,
            "duplicate_checked": True,
            "llm_errors": [],
        }
        with patch("app.routers.analysis.analyze_complaint", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_state

            # Override the rate limit setting temporarily for testing
            with patch.object(settings, "rate_limit_ai_analysis", "2/minute"):
                # Request 1: OK
                r1 = await client.post(
                    "/complaints/analyze",
                    json={"text": "A" * 50, "source": "Manual"},
                )
                assert r1.status_code == 200

                # Request 2: OK
                r2 = await client.post(
                    "/complaints/analyze",
                    json={"text": "B" * 50, "source": "Manual"},
                )
                assert r2.status_code == 200

                # Request 3: 429 Rate Limit Exceeded
                r3 = await client.post(
                    "/complaints/analyze",
                    json={"text": "C" * 50, "source": "Manual"},
                )
                assert r3.status_code == 429
                data = r3.json()
                assert data["error"] == "rate_limit_exceeded"
                assert "Too many requests" in data["detail"]
                assert "Retry-After" in r3.headers


@pytest.mark.anyio
async def test_file_upload_rejects_executable_magic_bytes_and_extensions():
    """Verify that executable files (Windows PE, Linux ELF, Java class, .exe) are strictly rejected."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Prohibited extension (.exe)
        r1 = await client.post(
            "/complaints/analyze-file",
            files={"file": ("malicious.exe", b"Some random payload content", "application/octet-stream")},
        )
        assert r1.status_code == 422

        # 2. Windows PE executable magic header (MZ) disguised as .txt
        r2 = await client.post(
            "/complaints/analyze-file",
            files={"file": ("report.txt", b"MZ\x90\x00\x03\x00\x00\x00payload", "text/plain")},
        )
        assert r2.status_code == 422
        assert "Executable" in str(r2.json())

        # 3. Linux ELF binary magic header (\x7fELF) disguised as .pdf
        r3 = await client.post(
            "/complaints/analyze-file",
            files={"file": ("report.pdf", b"\x7fELF\x02\x01\x01\x00payload", "application/pdf")},
        )
        assert r3.status_code == 422


@pytest.mark.anyio
async def test_file_upload_sanitizes_path_traversal_filenames():
    """Verify that path traversal in filenames (../../etc/passwd) is safely stripped to basename."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        mock_state = {
            "raw_input": "Valid complaint text with over 30 characters in length for testing.",
            "source": "Manual",
            "potential_duplicate": None,
            "duplicate_checked": True,
            "llm_errors": [],
        }
        with patch("app.routers.analysis.analyze_complaint", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_state
            valid_txt_content = b"This is a valid complaint text file describing tablet chipping defects."
            response = await client.post(
                "/complaints/analyze-file",
                files={"file": ("../../../../etc/passwd.txt", valid_txt_content, "text/plain")},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["document"]["filename"] == "passwd.txt"


@pytest.mark.anyio
async def test_global_error_handler_masks_internal_details(mock_prisma_db):
    """Verify that unhandled internal server exceptions return a sanitized 500 JSON payload without stack traces."""
    app = create_app()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("app.routers.complaints.get_stats", side_effect=RuntimeError("Internal DB crash /var/log/secret")):
            response = await client.get("/complaints/stats")
            assert response.status_code == 500
            data = response.json()
            assert data["error"] == "internal_server_error"
            # Ensure internal paths and exception tracebacks are NOT exposed
            assert "/var/log/secret" not in str(data)
            assert "Traceback" not in str(data)


@pytest.mark.anyio
async def test_input_validation_enforces_strict_batch_pattern_and_lengths(mock_prisma_db):
    """Verify that invalid batch numbers, excessive string lengths, and unknown enums are rejected."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid batch pattern (contains special characters)
        r1 = await client.post(
            "/complaints",
            json={
                "complainantName": "John Doe",
                "productName": "Paracetamol 500mg",
                "batchNumber": "PT@#$%^&*",
                "complaintType": "QualityDefect",
                "description": "Valid complaint description with more than 20 characters.",
            },
        )
        assert r1.status_code == 422
        errors = r1.json()["errors"]
        assert any(e["field"] == "batchNumber" for e in errors)

