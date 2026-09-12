"""Analysis service orchestrating the LangGraph complaint intelligence pipeline.

================================================================================
PHASE 5 DESIGN & WORKER SCALING NOTE:
1. Pipeline Invariance: The LangGraph pipeline (extract -> completeness -> risk_assess
   -> summarize -> capa -> root_cause) remains completely UNCHANGED in Phase 5.
   Only the input ingestion layer is expanded to feed parsed text from PDF/EML/TXT files.
2. Background Worker Scaling: In-memory CPU-bound parsing of files <=10MB runs
   inline within async endpoints. At enterprise scale (>100MB documents, scanned OCR),
   file parsing would be offloaded to Celery / ARQ background worker tasks, with
   FastAPI returning a 202 Accepted job token for asynchronous status polling.
================================================================================
"""

import logging
import time

from app.agent.graph import compiled_graph
from app.agent.state import ComplaintAnalysisState
from app.exceptions import GroqUnavailableError

logger = logging.getLogger(__name__)


async def analyze_complaint(
    raw_input: str,
    source: str = "Manual",
) -> ComplaintAnalysisState:
    """Execute the multi-node LangGraph pipeline on raw complaint text.

    Args:
        raw_input: Unstructured complaint text (email body, transcription, incident report).
        source: Intake channel ("Manual", "PDF", "Email").

    Returns:
        The populated ComplaintAnalysisState dictionary.

    Raises:
        GroqUnavailableError: If the pipeline fails completely (no extraction and multiple LLM errors).
    """
    initial_state: ComplaintAnalysisState = {
        "raw_input": raw_input,
        "source": source,
        "extracted": None,
        "missing_fields": [],
        "is_complete": False,
        "summary": None,
        "severity": None,
        "risk_reasoning": None,
        "recommended_sla_days": None,
        "capa_recommendation": None,
        "capa_action_type": None,
        "root_cause": None,
        "duplicate_of": None,
        "llm_errors": [],
        "iteration": 0,
    }

    start_time = time.perf_counter()
    logger.info(
        "Initiating LangGraph analysis pipeline for complaint text (%d characters, source=%s)...",
        len(raw_input),
        source,
    )

    try:
        final_state: ComplaintAnalysisState = await compiled_graph.ainvoke(initial_state)
    except GroqUnavailableError:
        raise
    except Exception as exc:
        logger.error("LangGraph pipeline execution crashed: %s", exc)
        raise GroqUnavailableError(f"AI pipeline encountered an unrecoverable error: {exc}") from exc

    total_latency_ms = (time.perf_counter() - start_time) * 1000
    llm_errors = final_state.get("llm_errors", [])

    logger.info(
        "Pipeline completed in %.2f ms. Status: %s. Warnings: %d",
        total_latency_ms,
        "SUCCESS" if not llm_errors else "DEGRADED",
        len(llm_errors),
    )

    if final_state.get("extracted") is None and len(llm_errors) >= 3:
        logger.error(
            "All pipeline nodes failed to execute. Raising GroqUnavailableError. Errors: %s",
            llm_errors,
        )
        raise GroqUnavailableError(
            "The AI analysis engine is unavailable or could not process the input."
        )

    return final_state
