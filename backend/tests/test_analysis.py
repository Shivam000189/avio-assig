"""Tests for the LangGraph AI Complaint Analysis Pipeline and /complaints/analyze endpoint.

All LLM calls are mocked at the `get_llm` factory layer to ensure 100% deterministic,
fast execution without network access or live Groq API keys.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage
import pytest
from httpx import ASGITransport, AsyncClient

from app.agent.llm import MODEL_FAST, MODEL_REASONING
from app.agent.llm import invoke_llm_with_retry
from app.config import settings
from app.exceptions import GroqUnavailableError
from app.main import create_app

app = create_app()

SAMPLE_RAW_TEXT = (
    "From: Dr. Marcus Vance <m.vance@stjude-hospital.org>\n"
    "Subject: Quality Complaint: Friable and Chipped Paracetamol 500mg Tablets\n"
    "During dispensing this morning, staff noticed chipped tablets in batch PT-4471-A. "
    "Please initiate an investigation and advise on quarantine procedures."
)


def mock_canned_llm_response(messages: list) -> AIMessage:
    """Return appropriate canned JSON based on the system prompt passed in messages."""
    sys_content = messages[0].content if messages else ""

    if "intake specialist" in sys_content.lower() or "intake metadata" in sys_content.lower():
        return AIMessage(
            content=json.dumps(
                {
                    "complainantName": "Dr. Marcus Vance",
                    "email": "m.vance@stjude-hospital.org",
                    "phone": "+1-555-019-2831",
                    "productName": "Paracetamol 500mg Tablets",
                    "batchNumber": "PT-4471-A",
                    "expiryDate": "2027-12-31",
                    "complaintType": "QualityDefect",
                    "description": "Friable and chipped Paracetamol tablets in batch PT-4471-A.",
                    "country": "United States",
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
                    "risk_reasoning": "Tablet friability affects dosage accuracy and unit-dose integrity under GMP standards.",
                    "recommended_sla_days": 15,
                }
            )
        )
    elif "summary" in sys_content.lower() or "executive summary" in sys_content.lower():
        return AIMessage(
            content=json.dumps(
                {
                    "summary": "Complaint regarding chipped Paracetamol 500mg tablets (batch PT-4471-A) reported by St. Jude Hospital. Investigation opened into tableting press compression tooling."
                }
            )
        )
    elif "capa" in sys_content.lower() or "21 cfr 820.100" in sys_content.lower():
        return AIMessage(
            content=json.dumps(
                {
                    "capa_recommendation": "Quarantine remaining inventory of batch PT-4471-A and inspect rotary press punch dies.",
                    "capa_action_type": "Corrective",
                }
            )
        )
    elif "root cause" in sys_content.lower() or "5-why" in sys_content.lower():
        return AIMessage(
            content=json.dumps(
                {
                    "root_cause": "Hypothesis: Mechanical shearing on rotary press punch heads due to die clearance misalignment."
                }
            )
        )

    return AIMessage(content="{}")


# ==============================================================================
# 1. HAPPY PATH TEST
# ==============================================================================


@pytest.mark.anyio
async def test_analyze_complaint_happy_path() -> None:
    """POST /api/v1/complaints/analyze should return 200 with fully populated state."""
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=mock_canned_llm_response)

    with patch("app.agent.graph.get_llm", return_value=mock_llm):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/complaints/analyze",
                json={
                    "text": SAMPLE_RAW_TEXT,
                    "source": "Email",
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "Email"
    assert data["isComplete"] is True
    assert data["extracted"]["productName"] == "Paracetamol 500mg Tablets"
    assert data["extracted"]["batchNumber"] == "PT-4471-A"
    assert data["severity"] == "Major"
    assert data["recommendedSlaDays"] == 15
    assert "friability" in data["riskReasoning"].lower()
    assert "Quarantine" in data["capaRecommendation"]
    assert data["capaActionType"] == "Corrective"
    assert "Hypothesis:" in data["rootCause"]
    assert len(data["warnings"]) == 0


# ==============================================================================
# 2. DEGRADED EXTRACTION FAILURE TEST
# ==============================================================================


@pytest.mark.anyio
async def test_analyze_complaint_degraded_on_malformed_json() -> None:
    """If extraction node produces malformed JSON twice, pipeline continues with warnings (200 OK)."""

    def mock_degraded_response(messages: list) -> AIMessage:
        sys_content = messages[0].content if messages else ""
        if "intake specialist" in sys_content.lower():
            # Returns broken non-JSON
            return AIMessage(content="Sorry, I cannot format this as JSON.")
        return mock_canned_llm_response(messages)

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=mock_degraded_response)

    with patch("app.agent.graph.get_llm", return_value=mock_llm):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/complaints/analyze",
                json={"text": SAMPLE_RAW_TEXT},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["extracted"] is None
    assert len(data["warnings"]) > 0
    assert any("extract" in w.lower() for w in data["warnings"])


# ==============================================================================
# 3. TOTAL OUTAGE TEST (502 BAD GATEWAY)
# ==============================================================================


@pytest.mark.anyio
async def test_analyze_complaint_total_failure_returns_502() -> None:
    """When all LLM calls fail completely, endpoint returns 502 Bad Gateway."""
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=GroqUnavailableError("Connection refused"))

    with patch("app.agent.graph.get_llm", return_value=mock_llm):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/complaints/analyze",
                json={"text": SAMPLE_RAW_TEXT},
            )

    assert response.status_code == 502
    assert response.json()["detail"] == "AI service unavailable"


@pytest.mark.anyio
async def test_llm_invoke_uses_gemini_fallback_when_groq_fails() -> None:
    """Groq failures should use Gemini before surfacing AI unavailability."""
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=GroqUnavailableError("invalid Groq key"))

    with patch("app.agent.llm._invoke_gemini_with_fallback", new_callable=AsyncMock) as mock_gemini:
        mock_gemini.return_value = AIMessage(content='{"summary": "Gemini fallback worked"}')
        result = await invoke_llm_with_retry(mock_llm, [])

    assert result.content == '{"summary": "Gemini fallback worked"}'
    mock_gemini.assert_awaited_once()


# ==============================================================================
# 4. MODEL ROUTING VERIFICATION TEST
# ==============================================================================


@pytest.mark.anyio
async def test_model_routing_tiers_enforced() -> None:
    """Verify that gemma2-9b-it is used for fast nodes and llama-3.3-70b-versatile for reasoning nodes."""
    captured_models: list[str] = []

    def mock_get_llm(model: str = MODEL_FAST, temperature: float = 0.1, max_tokens: int = 1024):
        captured_models.append(model)
        mock_instance = MagicMock()
        mock_instance.ainvoke = AsyncMock(side_effect=mock_canned_llm_response)
        return mock_instance

    mock_candidate = {
        "complaintId": "cuid_001",
        "complaintNumber": "CMP-2026-0001",
        "productName": "Paracetamol 500mg Tablets",
        "batchNumber": "PT-4471-A",
        "description": "Sample defect",
    }

    with (
        patch("app.agent.graph.get_llm", side_effect=mock_get_llm),
        patch("app.agent.graph.fetch_candidates", return_value=[mock_candidate]),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/api/v1/complaints/analyze",
                json={"text": SAMPLE_RAW_TEXT},
            )

    # 7 nodes in sequence:
    # 1. extract -> MODEL_FAST (gemma2-9b-it)
    # 2. duplicate_check -> MODEL_REASONING (llama-3.3-70b-versatile)
    # 3. completeness -> MODEL_FAST (gemma2-9b-it)
    # 4. risk_assess -> MODEL_REASONING (llama-3.3-70b-versatile)
    # 5. summarize -> MODEL_FAST (gemma2-9b-it)
    # 6. capa -> MODEL_REASONING (llama-3.3-70b-versatile)
    # 7. root_cause -> MODEL_REASONING (llama-3.3-70b-versatile)
    assert len(captured_models) == 7
    assert captured_models[0] == MODEL_FAST
    assert captured_models[1] == MODEL_REASONING
    assert captured_models[2] == MODEL_FAST
    assert captured_models[3] == MODEL_REASONING
    assert captured_models[4] == MODEL_FAST
    assert captured_models[5] == MODEL_REASONING
    assert captured_models[6] == MODEL_REASONING


@pytest.mark.anyio
async def test_complaint_chat_returns_grounded_response() -> None:
    """The complaint chat endpoint returns the LLM response when Groq is available."""
    mock_llm = MagicMock()
    with (
        patch("app.routers.analysis.get_llm", return_value=mock_llm) as mock_get_llm,
        patch("app.routers.analysis.invoke_llm_with_retry", new_callable=AsyncMock) as mock_invoke,
    ):
        mock_invoke.return_value = AIMessage(content="The complaint is classified as Major.")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/complaints/chat",
                json={
                    "message": "What is the current severity?",
                    "complaint_context": {
                        "severity": "Major",
                        "riskReasoning": "Tablet friability affects dosage accuracy.",
                        "recommendedSlaDays": 15,
                        "productName": "Paracetamol 500mg Tablets",
                    },
                },
            )

    assert response.status_code == 200
    assert response.json() == {"response": "The complaint is classified as Major."}
    mock_get_llm.assert_called_once_with(model=settings.groq_model_fast, temperature=0.3)
    mock_invoke.assert_awaited_once()


@pytest.mark.anyio
async def test_complaint_chat_falls_back_when_groq_unavailable() -> None:
    """The complaint chat endpoint avoids a 502 by answering from local context."""
    with patch("app.routers.analysis.get_llm", side_effect=GroqUnavailableError("offline")):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/complaints/chat",
                json={
                    "message": "What is the current severity?",
                    "complaint_context": {
                        "severity": "Major",
                        "riskReasoning": "Tablet friability affects dosage accuracy.",
                        "recommendedSlaDays": 15,
                    },
                },
            )

    assert response.status_code == 200
    assert response.json() == {
        "response": (
            "Severity is Major. Reasoning: Tablet friability affects dosage accuracy. "
            "Recommended SLA is 15 days."
        )
    }
