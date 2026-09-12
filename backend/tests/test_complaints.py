"""Comprehensive tests for the Complaint QMS CRUD, validation, stats, and CAPA endpoints.

Strategy: We mock the Prisma client and database operations at the module level
so the complete test matrix executes deterministically and fast without requiring
a live database.
"""

from datetime import datetime, timezone
import re
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app

app = create_app()


def create_mock_complaint(
    complaint_id: str = "cuid_001",
    complaint_number: str = "CMP-2026-0001",
    severity: str = "Major",
    status: str = "Open",
    complaint_type: str = "QualityDefect",
    product_name: str = "Paracetamol 500mg Tablets",
    batch_number: str = "PT-4471-A",
    include_capa: bool = True,
) -> dict[str, Any]:
    """Helper to generate a realistic mock complaint payload for repository returns."""
    now = datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc)
    capa_payload = (
        {
            "id": "capa_001",
            "complaintId": complaint_id,
            "actionType": "Corrective",
            "recommendedAction": "Recalibrate tableting press tooling.",
            "actionOwner": "Dr. Aris Thorne",
            "dueDate": datetime(2026, 4, 30, tzinfo=timezone.utc),
            "capaStatus": "Recommended",
        }
        if include_capa
        else None
    )

    return {
        "id": complaint_id,
        "complaintNumber": complaint_number,
        "complainantName": "St. Jude Hospital Pharmacy",
        "email": "pharmacy@stjude.org",
        "phone": "+1-555-0199",
        "productName": product_name,
        "batchNumber": batch_number,
        "expiryDate": datetime(2027, 12, 31, tzinfo=timezone.utc),
        "manufactureDate": datetime(2025, 1, 15, tzinfo=timezone.utc),
        "complaintType": complaint_type,
        "description": "Defective packaging with chipped tablets discovered during dispensing.",
        "severity": severity,
        "status": status,
        "source": "PDF",
        "country": "United States",
        "aiSummary": "Chipped tablets investigation.",
        "rootCause": None,
        "createdAt": now,
        "updatedAt": now,
        "documents": [
            {
                "id": "doc_001",
                "complaintId": complaint_id,
                "filename": "report.pdf",
                "fileType": "pdf",
                "extractedText": "Sample text",
                "uploadedAt": now,
            }
        ],
        "capa": capa_payload,
        "summary": {
            "id": "sum_001",
            "complaintId": complaint_id,
            "summaryText": "Executive summary of complaint.",
            "generatedAt": now,
        },
    }


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
        patch("app.services.complaint_repository.prisma", mock_p),
    ):
        yield mock_p


# ==============================================================================
# 1. POST /complaints Tests (Creation & Validation)
# ==============================================================================


@pytest.mark.anyio
async def test_create_valid_complaint(mock_prisma_db) -> None:
    """POST /api/v1/complaints should return 201 with auto-generated CMP-YYYY-NNNN number."""
    mock_prisma_db.complaint.count.return_value = 0

    async def mock_create(data: dict, include: dict):
        return create_mock_complaint(
            complaint_id="cuid_new_1",
            complaint_number=data["complaintNumber"],
            product_name=data["productName"],
            batch_number=data["batchNumber"],
        )

    mock_prisma_db.complaint.create.side_effect = mock_create

    payload = {
        "complainantName": "Central Hospital",
        "email": "qa@centralhospital.org",
        "productName": "Paracetamol 500mg Tablets",
        "batchNumber": "PT-4471-A",
        "complaintType": "QualityDefect",
        "description": "Tablets observed to be friable and broken inside intact packaging.",
        "severity": "Major",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/complaints", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert "complaintNumber" in data
    assert re.match(r"^CMP-\d{4}-\d{4}$", data["complaintNumber"])
    assert data["productName"] == "Paracetamol 500mg Tablets"


@pytest.mark.anyio
async def test_create_invalid_severity_returns_422(mock_prisma_db) -> None:
    """POST with invalid severity string should return 422 with structured errors."""
    payload = {
        "complainantName": "Central Hospital",
        "productName": "Paracetamol 500mg Tablets",
        "batchNumber": "PT-4471-A",
        "complaintType": "QualityDefect",
        "description": "Tablets observed to be friable and broken inside intact packaging.",
        "severity": "UltraCritical",  # Invalid enum value
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/complaints", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Validation error"
    assert any(err["field"] == "severity" for err in body["errors"])


@pytest.mark.anyio
async def test_create_invalid_batch_pattern_returns_422(mock_prisma_db) -> None:
    """POST with batch number violating pattern should return 422."""
    payload = {
        "complainantName": "Central Hospital",
        "productName": "Paracetamol 500mg Tablets",
        "batchNumber": "bad batch!@#$",  # Invalid characters
        "complaintType": "QualityDefect",
        "description": "Tablets observed to be friable and broken inside intact packaging.",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/complaints", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert any(err["field"] == "batchNumber" for err in body["errors"])


@pytest.mark.anyio
async def test_create_invalid_date_order_returns_422(mock_prisma_db) -> None:
    """POST with expiryDate prior to manufactureDate should return 422."""
    payload = {
        "complainantName": "Central Hospital",
        "productName": "Paracetamol 500mg Tablets",
        "batchNumber": "PT-4471-A",
        "complaintType": "QualityDefect",
        "description": "Tablets observed to be friable and broken inside intact packaging.",
        "manufactureDate": "2026-05-01T00:00:00Z",
        "expiryDate": "2025-01-01T00:00:00Z",  # Prior to manufacture
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/complaints", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Validation error"


@pytest.mark.anyio
async def test_create_client_supplied_complaint_number_rejected(mock_prisma_db) -> None:
    """POST with extra client-supplied complaintNumber should be rejected by extra='forbid'."""
    payload = {
        "complaintNumber": "CMP-9999-9999",  # Attempted mass assignment injection
        "complainantName": "Central Hospital",
        "productName": "Paracetamol 500mg Tablets",
        "batchNumber": "PT-4471-A",
        "complaintType": "QualityDefect",
        "description": "Tablets observed to be friable and broken inside intact packaging.",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/complaints", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert any("complaintNumber" in err["field"] or "extra" in err["message"].lower() for err in body["errors"])


# ==============================================================================
# 2. PUT /complaints/{id} Tests (Partial Updates)
# ==============================================================================


@pytest.mark.anyio
async def test_update_partial_status(mock_prisma_db) -> None:
    """PUT /api/v1/complaints/{id} should update only provided fields."""
    complaint_id = "cuid_up_1"
    existing = create_mock_complaint(complaint_id=complaint_id, status="Open")
    updated_obj = create_mock_complaint(complaint_id=complaint_id, status="Closed")

    mock_prisma_db.complaint.find_unique.return_value = existing
    mock_prisma_db.complaint.update.return_value = updated_obj

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            f"/api/v1/complaints/{complaint_id}",
            json={"status": "Closed"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Closed"
    assert data["productName"] == "Paracetamol 500mg Tablets"  # unchanged


@pytest.mark.anyio
async def test_update_missing_id_returns_404(mock_prisma_db) -> None:
    """PUT on non-existent complaint ID should return 404."""
    mock_prisma_db.complaint.find_unique.return_value = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/api/v1/complaints/missing_cuid",
            json={"status": "Closed"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Complaint not found"


# ==============================================================================
# 3. DELETE /complaints/{id} Tests
# ==============================================================================


@pytest.mark.anyio
async def test_delete_complaint_returns_204(mock_prisma_db) -> None:
    """DELETE /api/v1/complaints/{id} should return 204 No Content."""
    complaint_id = "cuid_del_1"
    existing = create_mock_complaint(complaint_id=complaint_id)
    mock_prisma_db.complaint.find_unique.return_value = existing
    mock_prisma_db.complaint.delete.return_value = existing

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete(f"/api/v1/complaints/{complaint_id}")

    assert response.status_code == 204

    # Subsequent GET on missing record returns 404
    mock_prisma_db.complaint.find_unique.return_value = None
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        get_response = await client.get(f"/api/v1/complaints/{complaint_id}")
    assert get_response.status_code == 404


# ==============================================================================
# 4. GET /complaints/stats & Filter Tests
# ==============================================================================


@pytest.mark.anyio
async def test_get_complaints_stats(mock_prisma_db) -> None:
    """GET /api/v1/complaints/stats should return computed aggregations."""
    row1 = MagicMock(status="Open", severity="Critical", complaintType="AdverseEvent")
    row2 = MagicMock(status="InProgress", severity="Major", complaintType="QualityDefect")
    row3 = MagicMock(status="Closed", severity="Minor", complaintType="LabelingIssue")

    mock_prisma_db.complaint.find_many.return_value = [row1, row2, row3]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/complaints/stats")

    assert response.status_code == 200
    stats = response.json()
    assert stats["total"] == 3
    assert stats["byStatus"]["Open"] == 1
    assert stats["byStatus"]["InProgress"] == 1
    assert stats["byStatus"]["Closed"] == 1
    assert stats["bySeverity"]["Critical"] == 1
    assert stats["bySeverity"]["Major"] == 1
    assert stats["bySeverity"]["Minor"] == 1
    assert stats["openByType"]["AdverseEvent"] == 1
    assert stats["openByType"]["QualityDefect"] == 1


@pytest.mark.anyio
async def test_get_complaints_search_filter(mock_prisma_db) -> None:
    """GET /api/v1/complaints?search=paracetamol should query matching records."""
    mock_row = create_mock_complaint(product_name="Paracetamol 500mg Tablets")
    mock_prisma_db.complaint.count.return_value = 1
    mock_prisma_db.complaint.find_many.return_value = [mock_row]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/complaints?search=paracetamol")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert "Paracetamol" in data["items"][0]["productName"]


@pytest.mark.anyio
async def test_get_complaints_excessive_limit_returns_422(mock_prisma_db) -> None:
    """GET /api/v1/complaints?limit=1000 should return 422 since max limit is 100."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/complaints?limit=1000")

    assert response.status_code == 422
    body = response.json()
    assert any(err["field"] == "limit" for err in body["errors"])


# ==============================================================================
# 5. CAPA Endpoint Tests
# ==============================================================================


@pytest.mark.anyio
async def test_get_complaint_capa_found_and_not_found(mock_prisma_db) -> None:
    """GET /api/v1/complaints/{id}/capa should return 200 with CAPA or 404 when none."""
    # Case A: Found
    existing = create_mock_complaint(complaint_id="cuid_with_capa")
    mock_capa = {
        "id": "capa_001",
        "complaintId": "cuid_with_capa",
        "actionType": "Corrective",
        "recommendedAction": "Tooling recalibration",
        "actionOwner": "Dr. Thorne",
        "dueDate": None,
        "capaStatus": "Recommended",
    }
    mock_prisma_db.complaint.find_unique.return_value = existing
    mock_prisma_db.capa.find_unique.return_value = mock_capa

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/complaints/cuid_with_capa/capa")

    assert response.status_code == 200
    assert response.json()["actionType"] == "Corrective"

    # Case B: Complaint exists but has no CAPA
    mock_prisma_db.capa.find_unique.return_value = None
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response_404 = await client.get("/api/v1/complaints/cuid_with_capa/capa")
    assert response_404.status_code == 404
    assert response_404.json()["detail"] == "CAPA not found"
