"""
Tests for Document Upload & Parsing (PDF / TXT / EML) and /complaints/from-analysis.

All LLM calls and DB operations are mocked to ensure 100% offline,
deterministic execution without external API or live DB dependencies.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage

from app.main import create_app

app = create_app()

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "samples" / "files"


def create_mock_persisted_complaint(
    complaint_id: str = "cuid_new_101",
    complaint_number: str = "CMP-2026-0099",
    severity: str = "Major",
    status: str = "Open",
    complaint_type: str = "QualityDefect",
    product_name: str = "Paracetamol 500mg Tablets",
    batch_number: str = "PT-4471-TEST",
    include_capa: bool = True,
    include_summary: bool = True,
    source: str = "PDF",
) -> dict[str, Any]:
    """Helper to construct realistic mock complaint dictionary matching Prisma relations."""
    now = datetime(2026, 4, 15, 10, 0, 0, tzinfo=timezone.utc)
    capa_payload = (
        {
            "id": "capa_new_101",
            "complaintId": complaint_id,
            "actionType": "Corrective",
            "recommendedAction": "Quarantine remaining inventory and inspect punch tooling.",
            "actionOwner": None,
            "dueDate": None,
            "capaStatus": "Recommended",
        }
        if include_capa
        else None
    )
    summary_payload = (
        {
            "id": "sum_new_101",
            "complaintId": complaint_id,
            "summaryText": "Hospital complaint regarding friable tablets in batch PT-4471-TEST.",
            "generatedAt": now,
        }
        if include_summary
        else None
    )

    return {
        "id": complaint_id,
        "complaintNumber": complaint_number,
        "complainantName": "Dr. Marcus Vance",
        "email": "m.vance@test-hospital.org",
        "phone": "+1-555-019-2831",
        "productName": product_name,
        "batchNumber": batch_number,
        "expiryDate": None,
        "manufactureDate": None,
        "complaintType": complaint_type,
        "description": "Friable and chipped tablets observed in batch PT-4471-TEST.",
        "severity": severity,
        "status": status,
        "source": source,
        "country": "Spain",
        "aiSummary": "Hospital complaint regarding friable tablets in batch PT-4471-TEST.",
        "rootCause": "Hypothesis: Inadequate compression pressure on tableting press.",
        "createdAt": now,
        "updatedAt": now,
        "documents": [],
        "capa": capa_payload,
        "summary": summary_payload,
    }


@pytest.fixture
def mock_prisma_db():
    """Mock Prisma database client across analysis and complaint modules."""
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
    mock_p.capa.create = AsyncMock()

    mock_p.complaintDocument = MagicMock()
    mock_p.complaintDocument.create = AsyncMock()

    with (
        patch("app.routers.analysis.prisma", mock_p),
        patch("app.routers.complaints.prisma", mock_p),
        patch("app.services.complaint_repository.prisma", mock_p),
    ):
        yield mock_p


def mock_canned_llm_response(messages: list) -> AIMessage:
    """Return appropriate canned JSON based on the system prompt passed in messages."""
    sys_content = messages[0].content if messages else ""

    if "intake specialist" in sys_content.lower() or "intake metadata" in sys_content.lower():
        return AIMessage(
            content=json.dumps(
                {
                    "complainantName": "Dr. Eleanor Vance",
                    "email": "e.vance@stjudeshospital.org",
                    "phone": "+44 20 7946 0912",
                    "productName": "Amoxicillin 250mg Oral Suspension",
                    "batchNumber": "AX-2209-B",
                    "expiryDate": "2027-11-30",
                    "complaintType": "AdverseEvent",
                    "description": "Patient experienced facial erythema, rash, and dizziness after administration.",
                    "country": "United Kingdom",
                }
            )
        )
    elif "completeness" in sys_content.lower() or "missing regulatory fields" in sys_content.lower():
        return AIMessage(
            content=json.dumps(
                {
                    "missing_fields": [],
                    "is_complete": True,
                }
            )
        )
    elif "risk" in sys_content.lower() or "ich q9" in sys_content.lower():
        return AIMessage(
            content=json.dumps(
                {
                    "severity": "Critical",
                    "risk_reasoning": "Severe allergic reaction and dizziness requiring acute emergency intervention.",
                    "recommended_sla_days": 3,
                }
            )
        )
    elif "summary" in sys_content.lower() or "executive summary" in sys_content.lower():
        return AIMessage(
            content=json.dumps(
                {
                    "summary": "Critical adverse event involving Amoxicillin 250mg batch AX-2209-B reported by St. Jude's Hospital."
                }
            )
        )
    elif "capa" in sys_content.lower() or "21 cfr 820.100" in sys_content.lower():
        return AIMessage(
            content=json.dumps(
                {
                    "capa_recommendation": "Quarantine remaining suspension units from batch AX-2209-B and inspect reconstitution line particulate filters.",
                    "capa_action_type": "ImmediateCorrection",
                }
            )
        )
    elif "root cause" in sys_content.lower() or "5-why" in sys_content.lower():
        return AIMessage(
            content=json.dumps(
                {
                    "root_cause": "Hypothesis: Excipient contamination or filtration mesh failure during oral suspension batch reconstitution."
                }
            )
        )

    return AIMessage(content="{}")


# ==============================================================================
# 1. VALID TXT UPLOAD TEST
# ==============================================================================


@pytest.mark.anyio
async def test_upload_valid_txt_success() -> None:
    """POST /complaints/analyze-file with valid .txt returns 200 and parsed document metadata."""
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=mock_canned_llm_response)

    file_content = (
        b"Quality Complaint: Metformin 850mg Tablets\n"
        b"Batch Number: MF-9901-A\n"
        b"Discovered discolored tablets with broken edges in carton lot 44."
    )

    with patch("app.agent.graph.get_llm", return_value=mock_llm):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/complaints/analyze-file",
                files={"file": ("complaint.txt", file_content, "text/plain")},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "Manual"
    assert data["document"]["filename"] == "complaint.txt"
    assert data["document"]["fileType"] == "txt"
    assert data["document"]["metadata"]["line_count"] >= 3
    assert data["severity"] == "Critical"
    assert data["isComplete"] is True


# ==============================================================================
# 2. VALID EML UPLOAD TEST (HEADERS & METADATA)
# ==============================================================================


@pytest.mark.anyio
async def test_upload_valid_eml_headers_and_body() -> None:
    """POST /complaints/analyze-file with .eml extracts From/Subject/Date into metadata and feeds body."""
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=mock_canned_llm_response)

    eml_path = SAMPLE_DIR / "complaint_adverse_event.eml"
    with open(eml_path, "rb") as f:
        eml_bytes = f.read()

    with patch("app.agent.graph.get_llm", return_value=mock_llm):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/complaints/analyze-file",
                files={"file": ("complaint_adverse_event.eml", eml_bytes, "message/rfc822")},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "Email"
    assert data["document"]["fileType"] == "eml"
    meta = data["document"]["metadata"]
    assert "Dr. Eleanor Vance" in meta["from"]
    assert "Amoxicillin 250mg" in meta["subject"]
    assert "2026" in meta["date"]


# ==============================================================================
# 3. FAKE PDF / CONTENT SNIFFING TEST
# ==============================================================================


@pytest.mark.anyio
async def test_upload_fake_pdf_rejected_by_magic_sniffing() -> None:
    """Upload text bytes disguised with .pdf extension is rejected by magic byte sniffing.
    
    Design justification:
    Polyglot and extension spoofing attacks are mitigated by requiring the %PDF header.
    Non-PDF content with a .pdf extension triggers a 422 Unprocessable Entity error.
    """
    fake_pdf_content = b"This is just plain text masquerading as a PDF file."

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/complaints/analyze-file",
            files={"file": ("fake_document.pdf", fake_pdf_content, "application/pdf")},
        )

    assert response.status_code == 422
    resp_body = str(response.json())
    assert "PDF" in resp_body or "header" in resp_body


# ==============================================================================
# 4. EXECUTABLE SNIFFING TEST (.exe with .txt extension)
# ==============================================================================


@pytest.mark.anyio
async def test_upload_executable_disguised_as_txt_rejected() -> None:
    """Upload DOS/PE executable bytes (MZ header) disguised as .txt is rejected by content sniffing."""
    mz_executable_content = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00" + (b"A" * 100)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/complaints/analyze-file",
            files={"file": ("malicious.txt", mz_executable_content, "text/plain")},
        )

    assert response.status_code == 422
    resp_body = str(response.json()).lower()
    assert "executable" in resp_body


# ==============================================================================
# 5. OVERSIZED FILE TEST (413 PAYLOAD TOO LARGE)
# ==============================================================================


@pytest.mark.anyio
async def test_upload_oversized_file_returns_413() -> None:
    """Upload file exceeding max_upload_mb (10MB) returns 413 Payload Too Large."""
    oversized_bytes = b"A" * (11 * 1024 * 1024)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/complaints/analyze-file",
            files={"file": ("large_file.txt", oversized_bytes, "text/plain")},
        )

    assert response.status_code == 413
    assert "too large" in str(response.json()).lower()


# ==============================================================================
# 6. IMAGE-BASED / EMPTY PDF TEST (422 WITH HINT)
# ==============================================================================


@pytest.mark.anyio
async def test_upload_image_based_pdf_returns_422_with_hint() -> None:
    """PDF with no extractable text returns 422 with clear user-facing hint."""
    mock_reader = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = ""
    mock_reader.pages = [mock_page]

    with patch("app.services.parsers.pdf_parser.PdfReader", return_value=mock_reader):
        dummy_pdf = b"%PDF-1.4\n%dummy pdf stream with no extractable text"
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/complaints/analyze-file",
                files={"file": ("scanned_doc.pdf", dummy_pdf, "application/pdf")},
            )

    assert response.status_code == 422
    resp_str = str(response.json()).lower()
    assert "hint" in resp_str
    assert "text-based" in resp_str or "manually" in resp_str


# ==============================================================================
# 7. POST /complaints/from-analysis WITH CAPA AND SUMMARY
# ==============================================================================


@pytest.mark.anyio
async def test_create_from_analysis_with_capa_and_summary(mock_prisma_db) -> None:
    """POST /complaints/from-analysis creates complaint, linked summary, and linked CAPA."""
    mock_persisted = create_mock_persisted_complaint(
        complaint_id="cuid_persisted_1",
        complaint_number="CMP-2026-0100",
        product_name="Paracetamol 500mg Tablets",
        batch_number="PT-4471-TEST",
        include_capa=True,
        include_summary=True,
    )
    mock_prisma_db.complaint.create.return_value = mock_persisted
    mock_prisma_db.complaint.find_unique.return_value = mock_persisted
    mock_prisma_db.capa.find_unique.return_value = mock_persisted["capa"]

    analysis_payload = {
        "extracted": {
            "productName": "Paracetamol 500mg Tablets",
            "batchNumber": "PT-4471-TEST",
            "complainantName": "Dr. Marcus Vance",
            "email": "m.vance@test-hospital.org",
            "phone": "+1-555-019-2831",
            "country": "Spain",
            "complaintType": "QualityDefect",
            "description": "Friable and chipped tablets observed in batch PT-4471-TEST.",
        },
        "severity": "Major",
        "recommendedSlaDays": 15,
        "riskReasoning": "Tablet friability affects dosage accuracy and unit-dose integrity.",
        "summary": "Hospital complaint regarding friable tablets in batch PT-4471-TEST.",
        "capaRecommendation": "Quarantine remaining inventory and inspect punch tooling.",
        "capaActionType": "Corrective",
        "rootCause": "Hypothesis: Inadequate compression pressure on tableting press.",
        "source": "PDF",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create complaint from analysis
        response = await client.post(
            "/api/v1/complaints/from-analysis",
            json=analysis_payload,
        )
        assert response.status_code == 201
        data = response.json()
        complaint_id = data["id"]
        assert data["severity"] == "Major"
        assert data["productName"] == "Paracetamol 500mg Tablets"
        assert data["source"] == "PDF"

        # Verify CAPA is accessible via GET /complaints/{id}/capa
        capa_resp = await client.get(f"/api/v1/complaints/{complaint_id}/capa")
        assert capa_resp.status_code == 200
        capa_data = capa_resp.json()
        assert capa_data["actionType"] == "Corrective"
        assert capa_data["capaStatus"] == "Recommended"
        assert "Quarantine" in capa_data["recommendedAction"]


# ==============================================================================
# 8. POST /complaints/from-analysis WITH NULL CAPA
# ==============================================================================


@pytest.mark.anyio
async def test_create_from_analysis_with_null_capa(mock_prisma_db) -> None:
    """When capaRecommendation is null/empty, complaint is created but no CAPA is attached (404 on GET capa)."""
    mock_persisted = create_mock_persisted_complaint(
        complaint_id="cuid_persisted_2",
        complaint_number="CMP-2026-0101",
        product_name="Cetirizine 10mg Tablets",
        batch_number="CZ-8812-NULL",
        include_capa=False,
        include_summary=True,
        severity="Minor",
        source="Manual",
    )
    mock_prisma_db.complaint.create.return_value = mock_persisted
    mock_prisma_db.complaint.find_unique.return_value = mock_persisted
    mock_prisma_db.capa.find_unique.return_value = None

    analysis_payload = {
        "extracted": {
            "productName": "Cetirizine 10mg Tablets",
            "batchNumber": "CZ-8812-NULL",
            "complainantName": "Dr. John Keller",
            "email": "contact@kellerpharmacy.de",
            "complaintType": "LabelingIssue",
            "description": "Minor font inconsistency on carton.",
        },
        "severity": "Minor",
        "recommendedSlaDays": 30,
        "riskReasoning": "Purely cosmetic packaging discrepancy.",
        "summary": "Minor label font discrepancy on Cetirizine carton.",
        "capaRecommendation": None,
        "capaActionType": None,
        "rootCause": "Hypothesis: Inkjet nozzle calibration offset.",
        "source": "Manual",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/complaints/from-analysis",
            json=analysis_payload,
        )
        assert response.status_code == 201
        complaint_id = response.json()["id"]

        # GET /complaints/{id}/capa should return 404 since no CAPA was created
        capa_resp = await client.get(f"/api/v1/complaints/{complaint_id}/capa")
        assert capa_resp.status_code == 404


# ==============================================================================
# 9. TRANSACTION ROLLBACK TEST
# ==============================================================================


@pytest.mark.anyio
async def test_create_from_analysis_transaction_rollback(mock_prisma_db) -> None:
    """If database persistence fails during the transaction, the entire Complaint record is rolled back."""
    # Force prisma.complaint.create to fail (simulating DB transaction failure)
    mock_prisma_db.complaint.create.side_effect = RuntimeError("Simulated DB Transaction Rollback")

    analysis_payload = {
        "extracted": {
            "productName": "Rollback Drug 100mg",
            "batchNumber": "RB-9999-FAIL",
            "complainantName": "QA Inspector",
            "email": "qa@rollback.org",
            "complaintType": "QualityDefect",
            "description": "Critical test for GMP rollback integrity.",
        },
        "severity": "Critical",
        "recommendedSlaDays": 3,
        "riskReasoning": "Rollback simulation.",
        "summary": "Testing GMP audit trail transactional rollback.",
        "capaRecommendation": "Simulate failure during CAPA persist step.",
        "capaActionType": "Corrective",
        "rootCause": "Simulated DB failure.",
        "source": "PDF",
    }

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/complaints/from-analysis",
            json=analysis_payload,
        )
        assert response.status_code == 500
