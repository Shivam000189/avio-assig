"""LangGraph Complaint Analysis Sequential Workflow Pipeline.

================================================================================
PIPELINE ARCHITECTURE (ASCII FLOW DIAGRAM):
--------------------------------------------------------------------------------
                  ┌───────────────────────────────┐
                  │             START             │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │ 1. extract                    │ (gemma2-9b-it, temp=0.1)
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │ 2. duplicate_check            │ (llama-3.3-70b-versatile, temp=0.1)
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │ 3. completeness               │ (gemma2-9b-it, temp=0.0)
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │ 4. risk_assess                │ (llama-3.3-70b-versatile, temp=0.2)
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │ 5. summarize_text             │ (gemma2-9b-it, temp=0.3)
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │ 6. capa                       │ (llama-3.3-70b-versatile, temp=0.3)
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │ 7. hypothesize_root_cause     │ (llama-3.3-70b-versatile, temp=0.3)
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │              END              │
                  └───────────────────────────────┘
================================================================================
NODE I/O & PURITY ARCHITECTURAL NOTE:
LangGraph nodes in Python are async functions that accept state and return delta updates.
Executing database I/O inside `duplicate_check_node` to fetch candidate matches is standard
in retrieval-augmented agent workflows.

HOW TO DECOUPLE FOR PURE-FUNCTION EXECUTION:
If a strictly pure function execution model is required (e.g., deterministic replay without
mock engines), candidate retrieval can be shifted upstream to `analyze_complaint()` and
passed as a list of candidate dictionaries in `ComplaintAnalysisState` prior to invoking
`compiled_graph.ainvoke()`.
================================================================================
WARM COMPILATION RATIONALE:
The LangGraph StateGraph is compiled ONCE at the module level into `compiled_graph`.
Compiling graph topology at process startup verifies node bindings, schema transitions,
and edge routes ahead of time, ensuring 0ms compilation latency during HTTP request handling.
================================================================================
"""

import json
import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agent.llm import MODEL_FAST, MODEL_REASONING, get_llm
from app.agent.prompts import (
    CAPA_SCHEMA_HINT,
    CAPA_SYSTEM_PROMPT,
    COMPLETENESS_SCHEMA_HINT,
    COMPLETENESS_SYSTEM_PROMPT,
    DUPLICATE_SCHEMA_HINT,
    DUPLICATE_SYSTEM_PROMPT,
    EXTRACT_SCHEMA_HINT,
    EXTRACT_SYSTEM_PROMPT,
    RISK_ASSESS_SCHEMA_HINT,
    RISK_ASSESS_SYSTEM_PROMPT,
    ROOT_CAUSE_SCHEMA_HINT,
    ROOT_CAUSE_SYSTEM_PROMPT,
    SUMMARIZE_SCHEMA_HINT,
    SUMMARIZE_SYSTEM_PROMPT,
)
from app.agent.state import ComplaintAnalysisState
from app.agent.utils import run_json_node
from app.services.duplicate_service import fetch_candidates

logger = logging.getLogger(__name__)


# ==============================================================================
# NODE IMPLEMENTATIONS
# ==============================================================================


async def extract_node(state: ComplaintAnalysisState) -> dict[str, Any]:
    """Node 1: Extract structured complaint entity fields from raw text."""
    logger.info("Executing Node 1: Extract Complaint Intake Metadata...")
    llm = get_llm(model=MODEL_FAST, temperature=0.1)

    user_content = (
        f"Raw Complaint Input:\n{state.get('raw_input', '')}\n\n"
        f"Intake Channel / Source: {state.get('source', 'Manual')}"
    )

    result = await run_json_node(
        node_name="extract",
        llm=llm,
        system_prompt=EXTRACT_SYSTEM_PROMPT,
        user_content=user_content,
        schema_hint=EXTRACT_SCHEMA_HINT,
    )

    if "__error__" in result:
        err_list = list(state.get("llm_errors") or [])
        err_list.append(result["__error__"])
        return {"extracted": None, "llm_errors": err_list}

    return {"extracted": result}


async def duplicate_check_node(state: ComplaintAnalysisState) -> dict[str, Any]:
    """Node 2: Evaluate duplicate candidate matches and quality signal trending."""
    logger.info("Executing Node 2: Duplicate Detection & Signal Trending (Reasoning Tier)...")
    extracted = state.get("extracted")

    # 1. Retrieve candidates from database repository layer
    candidates = await fetch_candidates(extracted=extracted, limit=5)

    if not candidates:
        logger.info("No candidate duplicate complaints found in database.")
        return {
            "potential_duplicate": None,
            "duplicate_of": None,
            "duplicate_checked": True,
        }

    # 2. Invoke reasoning model for LLM-as-judge duplicate classification
    llm = get_llm(model=MODEL_REASONING, temperature=0.1)

    extracted_str = json.dumps(extracted or {}, indent=2, default=str)
    candidates_str = json.dumps(candidates, indent=2, default=str)

    user_content = (
        f"New Complaint Narrative:\n{state.get('raw_input', '')}\n\n"
        f"New Complaint Extracted Data:\n{extracted_str}\n\n"
        f"Existing Candidate Complaints in Database:\n{candidates_str}"
    )

    result = await run_json_node(
        node_name="duplicate_check",
        llm=llm,
        system_prompt=DUPLICATE_SYSTEM_PROMPT,
        user_content=user_content,
        schema_hint=DUPLICATE_SCHEMA_HINT,
    )

    if "__error__" in result:
        err_list = list(state.get("llm_errors") or [])
        err_list.append(result["__error__"])
        return {
            "potential_duplicate": None,
            "duplicate_of": None,
            "duplicate_checked": True,
            "llm_errors": err_list,
        }

    is_duplicate = bool(result.get("is_duplicate", False))
    similarity = str(result.get("similarity", "Low"))
    matched_complaint_number = result.get("matched_complaint_number")
    explanation = result.get("explanation", "")

    # Surface duplicates or potential cross-batch manufacturing trends (Medium similarity)
    potential_duplicate = None
    duplicate_of = None

    if is_duplicate or similarity in ("High", "Medium"):
        # Match candidate ID
        matched_id = None
        for cand in candidates:
            if cand.get("complaintNumber") == matched_complaint_number:
                matched_id = cand.get("complaintId")
                break
        if not matched_id and candidates:
            matched_id = candidates[0].get("complaintId")
            if not matched_complaint_number:
                matched_complaint_number = candidates[0].get("complaintNumber")

        potential_duplicate = {
            "complaintId": matched_id,
            "complaintNumber": matched_complaint_number,
            "similarity": similarity,
            "explanation": explanation,
            "isPossibleTrend": (similarity == "Medium" and not is_duplicate),
        }
        if is_duplicate:
            duplicate_of = matched_complaint_number

    return {
        "potential_duplicate": potential_duplicate,
        "duplicate_of": duplicate_of,
        "duplicate_checked": True,
    }


async def completeness_node(state: ComplaintAnalysisState) -> dict[str, Any]:
    """Node 3: Evaluate missing regulatory fields and record completeness."""
    logger.info("Executing Node 3: Check Complaint Completeness...")
    llm = get_llm(model=MODEL_FAST, temperature=0.0)

    extracted_str = json.dumps(state.get("extracted") or {}, indent=2)
    user_content = f"Extracted Complaint Entity Data:\n{extracted_str}"

    result = await run_json_node(
        node_name="completeness",
        llm=llm,
        system_prompt=COMPLETENESS_SYSTEM_PROMPT,
        user_content=user_content,
        schema_hint=COMPLETENESS_SCHEMA_HINT,
    )

    if "__error__" in result:
        err_list = list(state.get("llm_errors") or [])
        err_list.append(result["__error__"])
        return {
            "missing_fields": ["productName", "batchNumber", "description"],
            "is_complete": False,
            "llm_errors": err_list,
        }

    return {
        "missing_fields": result.get("missing_fields", []),
        "is_complete": bool(result.get("is_complete", False)),
    }


async def risk_assess_node(state: ComplaintAnalysisState) -> dict[str, Any]:
    """Node 4: Assess clinical risk, assign severity (Critical/Major/Minor), and calculate SLA."""
    logger.info("Executing Node 4: Risk & Severity Classification (Reasoning Tier)...")
    llm = get_llm(model=MODEL_REASONING, temperature=0.2)

    extracted_str = json.dumps(state.get("extracted") or {}, indent=2)
    user_content = (
        f"Raw Complaint Description:\n{state.get('raw_input', '')}\n\n"
        f"Extracted Metadata:\n{extracted_str}"
    )

    result = await run_json_node(
        node_name="risk_assess",
        llm=llm,
        system_prompt=RISK_ASSESS_SYSTEM_PROMPT,
        user_content=user_content,
        schema_hint=RISK_ASSESS_SCHEMA_HINT,
    )

    if "__error__" in result:
        err_list = list(state.get("llm_errors") or [])
        err_list.append(result["__error__"])
        return {
            "severity": None,
            "risk_reasoning": None,
            "recommended_sla_days": None,
            "llm_errors": err_list,
        }

    return {
        "severity": result.get("severity"),
        "risk_reasoning": result.get("risk_reasoning"),
        "recommended_sla_days": result.get("recommended_sla_days"),
    }


async def summarize_node(state: ComplaintAnalysisState) -> dict[str, Any]:
    """Node 5: Synthesize a professional 2-3 sentence executive summary for QA management."""
    logger.info("Executing Node 5: Generate Executive Summary...")
    llm = get_llm(model=MODEL_FAST, temperature=0.3)

    extracted_str = json.dumps(state.get("extracted") or {}, indent=2)
    user_content = (
        f"Raw Complaint Text:\n{state.get('raw_input', '')}\n\n"
        f"Extracted Information:\n{extracted_str}\n\n"
        f"Assessed Severity: {state.get('severity', 'Unknown')}"
    )

    result = await run_json_node(
        node_name="summarize",
        llm=llm,
        system_prompt=SUMMARIZE_SYSTEM_PROMPT,
        user_content=user_content,
        schema_hint=SUMMARIZE_SCHEMA_HINT,
    )

    if "__error__" in result:
        err_list = list(state.get("llm_errors") or [])
        err_list.append(result["__error__"])
        return {"summary": None, "llm_errors": err_list}

    return {"summary": result.get("summary")}


async def capa_node(state: ComplaintAnalysisState) -> dict[str, Any]:
    """Node 6: Recommend actionable Corrective and Preventive Action (CAPA) steps."""
    logger.info("Executing Node 6: Formulate CAPA Plan (Reasoning Tier)...")
    llm = get_llm(model=MODEL_REASONING, temperature=0.3)

    extracted_str = json.dumps(state.get("extracted") or {}, indent=2)
    user_content = (
        f"Extracted Complaint Information:\n{extracted_str}\n\n"
        f"Severity: {state.get('severity', 'Major')}\n"
        f"Risk Analysis: {state.get('risk_reasoning', 'None provided')}"
    )

    result = await run_json_node(
        node_name="capa",
        llm=llm,
        system_prompt=CAPA_SYSTEM_PROMPT,
        user_content=user_content,
        schema_hint=CAPA_SCHEMA_HINT,
    )

    if "__error__" in result:
        err_list = list(state.get("llm_errors") or [])
        err_list.append(result["__error__"])
        return {
            "capa_recommendation": None,
            "capa_action_type": None,
            "llm_errors": err_list,
        }

    return {
        "capa_recommendation": result.get("capa_recommendation"),
        "capa_action_type": result.get("capa_action_type"),
    }


async def root_cause_node(state: ComplaintAnalysisState) -> dict[str, Any]:
    """Node 7: Formulate most probable root cause hypothesis."""
    logger.info("Executing Node 7: Hypothesize Root Cause Mechanism (Reasoning Tier)...")
    llm = get_llm(model=MODEL_REASONING, temperature=0.3)

    extracted_str = json.dumps(state.get("extracted") or {}, indent=2)
    user_content = (
        f"Extracted Metadata:\n{extracted_str}\n\n"
        f"Severity: {state.get('severity', 'Unknown')}\n"
        f"CAPA Action: {state.get('capa_recommendation', 'None')}"
    )

    result = await run_json_node(
        node_name="root_cause",
        llm=llm,
        system_prompt=ROOT_CAUSE_SYSTEM_PROMPT,
        user_content=user_content,
        schema_hint=ROOT_CAUSE_SCHEMA_HINT,
    )

    if "__error__" in result:
        err_list = list(state.get("llm_errors") or [])
        err_list.append(result["__error__"])
        return {"root_cause": None, "llm_errors": err_list}

    return {"root_cause": result.get("root_cause")}


# ==============================================================================
# GRAPH ASSEMBLY & WARM COMPILATION
# ==============================================================================

graph_builder = StateGraph(ComplaintAnalysisState)

graph_builder.add_node("extract", extract_node)
graph_builder.add_node("duplicate_check", duplicate_check_node)
graph_builder.add_node("completeness", completeness_node)
graph_builder.add_node("risk_assess", risk_assess_node)
graph_builder.add_node("summarize_text", summarize_node)
graph_builder.add_node("capa", capa_node)
graph_builder.add_node("hypothesize_root_cause", root_cause_node)

# Linear Sequential Flow (7 Nodes)
graph_builder.add_edge(START, "extract")
graph_builder.add_edge("extract", "duplicate_check")
graph_builder.add_edge("duplicate_check", "completeness")
graph_builder.add_edge("completeness", "risk_assess")
graph_builder.add_edge("risk_assess", "summarize_text")
graph_builder.add_edge("summarize_text", "capa")
graph_builder.add_edge("capa", "hypothesize_root_cause")
graph_builder.add_edge("hypothesize_root_cause", END)

# Compiled once at module load time
compiled_graph = graph_builder.compile()


async def run_complaint_analysis(
    raw_input: str,
    source: str = "Manual",
) -> ComplaintAnalysisState:
    """Execute the compiled LangGraph pipeline on raw complaint input."""
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
        "potential_duplicate": None,
        "duplicate_checked": False,
        "llm_errors": [],
        "iteration": 1,
    }

    final_state = await compiled_graph.ainvoke(initial_state)
    return final_state
