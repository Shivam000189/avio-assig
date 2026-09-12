"""Tests for Phase 6: Duplicate Complaint Detection and AI Insights on Saved Complaints.

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

from app.agent.llm import MODEL_FAST, MODEL_REASONING
from app.main import create_app

app = create_app()

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "samples" / "files"


def create_mock_db_complaint(
    complaint_id: str = "cuid_cmp_0001",
    complaint_number: str = "CMP-2026-0001",
    severity: str | None = "Major",
    status: str = "Open",
    complaint_type: str = "QualityDefect",
    product_name: str = "Paracetamol 500mg Tablets",
    batch_number: str = "PT-4471-A",
    include_capa: bool = True,
    include_summary: bool = True,
    source: str = "Manual",
) -> dict[str, Any]:
    """Helper to generate realistic mock complaint payload."""
    now = datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc)
    capa_payload = (
        {
            "id": "capa_0001",
            "complaintId": complaint_id,
            "actionType": "Corrective",
            "recommendedAction": "Inspect tableting press punch tooling for lot PT-4471-A.",
            "actionOwner": "QA Lead",
            "dueDate": datetime(2026, 4, 30, tzinfo=timezone.utc),
            "capaStatus": "Recommended",
        }
        if include_capa
        else None
    )
    summary_payload = (
        {
            "id": "sum_0001",
            "complaintId": complaint_id,
            "summaryText": "Friable tablets reported from pharmacy dispensing.",
            "generatedAt": now,
        }
        if include_summary
        else None
    )

    return {
        "id": complaint_id,
        "complaintNumber": complaint_number,
        "complainantName": "Farmacia Central",
        "email": "qa@farmaciacentral.es",
        "phone": "+34 91 555 0192",
        "productName": product_name,
        "batchNumber": batch_number,
        "expiryDate": datetime(2027, 12, 31, tzinfo=timezone.utc),
        "manufactureDate": datetime(2025, 1, 15, tzinfo=timezone.utc),
        "complaintType": complaint_type,
        "description": "Friable and chipped tablets observed across multiple blister cards in batch PT-4471-A.",
        "severity": severity,
        "status": status,
        "source": source,
        "country": "Spain",
        "aiSummary": "Friable tablets reported from pharmacy dispensing." if include_summary else None,
        "rootCause": "Punch head wear." if include_summary else None,
        "createdAt": now,
        "updatedAt": now,
        "documents": [],
        "capa": capa_payload,
        "summary": summary_payload,
    }


@pytest.fixture
def mock_prisma_db():
    """Mock Prisma database client."""
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

    mock_p.complaintsummary = MagicMock()
    mock_p.complaintsummary.upsert = AsyncMock()

    mock_p.complaintDocument = MagicMock()
    mock_p.complaintDocument.create = AsyncMock()

    with (
        patch("app.routers.analysis.prisma", mock_p),
        patch("app.services.duplicate_service.prisma", mock_p),
        patch("app.services.complaint_repository.prisma", mock_p),
    ):
        yield mock_p


def mock_canned_llm_response(messages: list) -> AIMessage:
    """Deterministic LLM responses for graph nodes including duplicate check."""
    sys_content = messages[0].content if messages else ""

    if "intake specialist" in sys_content.lower() or "intake metadata" in sys_content.lower():
        return AIMessage(
            content=json.dumps(
                {
                    "complainantName": "Juan Perez",
                    "email": "j.perez@farmaciasanjeronimo.es",
                    "phone": "+34 91 666 4321",
                    "productName": "Paracetamol 500mg Tablets",
                    "batchNumber": "PT-4471-A",
                    "expiryDate": "2027-12-31",
                    "complaintType": "QualityDefect",
                    "description": "Tablets severely chipped on the perimeter from lot PT-4471-A.",
                    "country": "Spain",
                }
            )
        )
    elif "signal detection" in sys_content.lower() or "duplicate" in sys_content.lower():
        return AIMessage(
            content=json.dumps(
                {
                    "is_duplicate": True,
                    "matched_complaint_number": "CMP-2026-0001",
                    "similarity": "High",
                    "explanation": "Matching batch PT-4471-A and identical tablet chipping defect reported.",
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
                    "severity": "Major",
                    "risk_reasoning": "Tablet friability affects dosage accuracy and unit-dose integrity.",
                    "recommended_sla_days": 15,
                }
            )
        )
    elif "summary" in sys_content.lower() or "executive summary" in sys_content.lower():
        return AIMessage(
            content=json.dumps(
                {
                    "summary": "Second pharmacy complaint regarding chipped Paracetamol tablets in batch PT-4471-A."
                }
            )
        )
    elif "capa" in sys_content.lower() or "21 cfr 820.100" in sys_content.lower():
        return AIMessage(
            content=json.dumps(
                {
                    "capa_recommendation": "Extend quarantine of batch PT-4471-A and audit tableting press punch clearance.",
                    "capa_action_type": "Corrective",
                }
            )
        )
    elif "root cause" in sys_content.lower() or "5-why" in sys_content.lower():
        return AIMessage(
            content=json.dumps(
                {
                    "root_cause": "Hypothesis: Die misalignment causing excessive tablet edge shearing during ejection."
                }
            )
        )

    return AIMessage(content="{}")


# ==============================================================================
# 1. DUPLICATE DETECTED TEST
# ==============================================================================


@pytest.mark.anyio
async def test_duplicate_detected_for_matching_batch(mock_prisma_db) -> None:
    """Analyze complaint with same batch PT-4471-A flags potential duplicate CMP-2026-0001."""
    # Mock existing candidate complaint in database
    existing_cand = MagicMock()
    existing_cand.id = "cuid_cmp_0001"
    existing_cand.complaintNumber = "CMP-2026-0001"
    existing_cand.productName = "Paracetamol 500mg Tablets"
    existing_cand.batchNumber = "PT-4471-A"
    existing_cand.description = "Chipped tablets in blister cards."
    existing_cand.severity = "Major"
    existing_cand.status = "Open"
    existing_cand.createdAt = datetime(2026, 3, 1, tzinfo=timezone.utc)

    mock_prisma_db.complaint.find_many.return_value = [existing_cand]

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=mock_canned_llm_response)

    duplicate_file_path = SAMPLE_DIR / "complaint_duplicate_chipping.txt"
    with open(duplicate_file_path, "rb") as f:
        file_bytes = f.read()

    with patch("app.agent.graph.get_llm", return_value=mock_llm):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/complaints/analyze-file",
                files={"file": ("complaint_duplicate_chipping.txt", file_bytes, "text/plain")},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["duplicateChecked"] is True
    assert data["potentialDuplicate"] is not None
    assert data["potentialDuplicate"]["complaintNumber"] == "CMP-2026-0001"
    assert data["potentialDuplicate"]["similarity"] == "High"
    assert "PT-4471-A" in data["potentialDuplicate"]["explanation"]


# ==============================================================================
# 2. NO CANDIDATES FOUND TEST (UNIQUE BATCH)
# ==============================================================================


@pytest.mark.anyio
async def test_no_candidates_skips_duplicate_llm_call(mock_prisma_db) -> None:
    """When no matching candidates exist in database, duplicate LLM reasoning is bypassed."""
    mock_prisma_db.complaint.find_many.return_value = []

    called_models: list[str] = []

    def mock_get_llm(model: str = MODEL_FAST, temperature: float = 0.1, max_tokens: int = 1024):
        called_models.append(model)
        mock_inst = MagicMock()
        mock_inst.ainvoke = AsyncMock(side_effect=mock_canned_llm_response)
        return mock_inst

    with patch("app.agent.graph.get_llm", side_effect=mock_get_llm):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/complaints/analyze",
                json={
                    "text": "Unique medication complaint for batch UNIQ-9999 with broken bottle seal and leak.",
                    "source": "Manual",
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert data["duplicateChecked"] is True
    assert data["potentialDuplicate"] is None

    # Nodes executed: extract (1), completeness (2), risk_assess (3), summarize (4), capa (5), root_cause (6)
    # Duplicate node was bypassed, so exactly 6 LLM calls occurred
    assert len(called_models) == 6


# ==============================================================================
# 3. EXTRACTION TOO WEAK TEST
# ==============================================================================


@pytest.mark.anyio
async def test_extraction_too_weak_skips_candidate_query(mock_prisma_db) -> None:
    """When extraction yields neither product nor batch, duplicate search is gracefully bypassed."""

    def mock_weak_extraction(messages: list) -> AIMessage:
        sys_content = messages[0].content if messages else ""
        if "intake specialist" in sys_content.lower():
            return AIMessage(
                content=json.dumps(
                    {
                        "complainantName": "Anonymous",
                        "productName": "UNKNOWN PRODUCT",
                        "batchNumber": "UNKNOWN",
                        "description": "Indecipherable voicemail report.",
                    }
                )
            )
        return mock_canned_llm_response(messages)

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=mock_weak_extraction)

    with patch("app.agent.graph.get_llm", return_value=mock_llm):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/complaints/analyze",
                json={"text": "Vague report without clear product name or batch information provided."},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["duplicateChecked"] is True
    assert data["potentialDuplicate"] is None


# ==============================================================================
# 4. DUPLICATE NODE LLM FAILURE DEGRADATION
# ==============================================================================


@pytest.mark.anyio
async def test_duplicate_node_failure_degrades_gracefully(mock_prisma_db) -> None:
    """If duplicate reasoning LLM returns broken JSON, pipeline continues and logs warning."""
    existing_cand = MagicMock()
    existing_cand.id = "cuid_001"
    existing_cand.complaintNumber = "CMP-2026-0001"
    existing_cand.productName = "Paracetamol 500mg Tablets"
    existing_cand.batchNumber = "PT-4471-A"
    existing_cand.description = "Sample defect"
    existing_cand.severity = "Major"
    existing_cand.status = "Open"
    existing_cand.createdAt = datetime.now(timezone.utc)
    mock_prisma_db.complaint.find_many.return_value = [existing_cand]

    def mock_broken_duplicate(messages: list) -> AIMessage:
        sys_content = messages[0].content if messages else ""
        if "signal detection" in sys_content.lower() or "duplicate" in sys_content.lower():
            return AIMessage(content="Malformed response cannot parse as JSON")
        return mock_canned_llm_response(messages)

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=mock_broken_duplicate)

    with patch("app.agent.graph.get_llm", return_value=mock_llm):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/complaints/analyze",
                json={
                    "text": "Complaint regarding Paracetamol 500mg Tablets batch PT-4471-A with chipped tablets.",
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert data["duplicateChecked"] is True
    assert data["potentialDuplicate"] is None
    assert len(data["warnings"]) > 0
    assert any("duplicate_check" in w.lower() for w in data["warnings"])


# ==============================================================================
# 5. AI INSIGHTS ON SAVED COMPLAINT TEST (IDEMPOTENCY)
# ==============================================================================


@pytest.mark.anyio
async def test_ai_insights_on_saved_complaint_idempotent(mock_prisma_db) -> None:
    """POST /complaints/{id}/ai-insights runs AI analysis on saved record and updates in place."""
    enriched_record = create_mock_db_complaint(
        complaint_id="cuid_manual_10",
        complaint_number="CMP-2026-0010",
        severity="Major",
        include_capa=True,
        include_summary=True,
    )

    mock_prisma_db.complaint.find_unique.return_value = enriched_record

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=mock_canned_llm_response)

    with patch("app.agent.graph.get_llm", return_value=mock_llm):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. First invocation: updates severity, summary, CAPA
            resp1 = await client.post("/api/v1/complaints/cuid_manual_10/ai-insights")
            assert resp1.status_code == 200
            data1 = resp1.json()
            assert data1["severity"] == "Major"
            assert data1["summary"] is not None
            assert data1["capa"] is not None

            # 2. Second invocation: idempotent update
            resp2 = await client.post("/api/v1/complaints/cuid_manual_10/ai-insights")
            assert resp2.status_code == 200
            data2 = resp2.json()
            assert data2["severity"] == "Major"


# ==============================================================================
# 6. AI INSIGHTS NOT FOUND TEST (404)
# ==============================================================================


@pytest.mark.anyio
async def test_ai_insights_missing_id_returns_404(mock_prisma_db) -> None:
    """POST /complaints/{invalid_id}/ai-insights returns 404 Not Found."""
    mock_prisma_db.complaint.find_unique.return_value = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/complaints/nonexistent_id/ai-insights")

    assert response.status_code == 404


# ==============================================================================
# 7. AI INSIGHTS DB FAILURE ROLLBACK TEST
# ==============================================================================


@pytest.mark.anyio
async def test_ai_insights_rollback_on_db_failure(mock_prisma_db) -> None:
    """If DB update fails during ai-insights, endpoint returns 500."""
    existing_record = create_mock_db_complaint(
        complaint_id="cuid_fail_1",
        complaint_number="CMP-2026-0099",
        severity=None,
    )
    mock_prisma_db.complaint.find_unique.return_value = existing_record
    mock_prisma_db.complaint.update.side_effect = RuntimeError("Simulated DB Write Lock Error")

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=mock_canned_llm_response)

    with patch("app.agent.graph.get_llm", return_value=mock_llm):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/complaints/cuid_fail_1/ai-insights")
            assert response.status_code == 500
