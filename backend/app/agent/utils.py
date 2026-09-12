"""Utility functions for LLM interaction, robust JSON extraction, and self-healing node execution.

================================================================================
SELF-HEALING NODE EXECUTION DESIGN DECISION:
In mission-critical QMS pipelines, an LLM formatting error in one downstream node
(such as root cause or summarization) must NEVER crash the entire intake workflow.

`run_json_node()` implements a two-stage fault-tolerant recovery loop:
1. Primary invocation with strict schema hints.
2. If invalid JSON is returned, a targeted healing retry prompt is sent with the
   formatting correction.
3. If the second attempt still fails, `run_json_node` catches the exception and
   returns a structured `{"__error__": message}` payload.

This allows the graph to log the specific failure into `state["llm_errors"]`, gracefully
set the affected node fields to `None`, and continue execution so subsequent nodes
and the final API response still deliver partial value to the user.
================================================================================
"""

import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.llm import invoke_llm_with_retry
from app.exceptions import LLMJsonParseError

logger = logging.getLogger(__name__)


def parse_llm_json(text: str) -> dict[str, Any]:
    """Parse structured JSON from raw LLM output with fence and regex stripping.

    Args:
        text: Raw text response from the language model.

    Returns:
        Parsed Python dictionary.

    Raises:
        LLMJsonParseError: If no valid JSON dictionary structure can be decoded.
    """
    if not text:
        raise LLMJsonParseError("Empty response received from LLM.")

    cleaned = text.strip()

    # Strip markdown code blocks (e.g. ```json ... ``` or ``` ...)
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    # First attempt: direct json.loads on cleaned text
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # Second attempt: extract the first outermost {...} block via regex
    match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict):
                return data
        except Exception as exc:
            raise LLMJsonParseError(f"Failed to parse extracted JSON block: {exc}") from exc

    raise LLMJsonParseError(f"Could not extract a valid JSON object from LLM response: {text[:200]}...")


async def run_json_node(
    node_name: str,
    llm: Any,
    system_prompt: str,
    user_content: str,
    schema_hint: str,
) -> dict[str, Any]:
    """Execute an LLM node with automatic JSON parsing and single-retry self-healing.

    Args:
        node_name: Identifying label of the pipeline node (for logging and errors).
        llm: Configured ChatGroq client.
        system_prompt: Base persona and instructions for the task.
        user_content: Context/state payload to be processed.
        schema_hint: Explicit JSON schema string demonstrating target output format.

    Returns:
        A valid parsed dictionary, or `{"__error__": "<description>"}` if all attempts fail.
    """
    full_system = f"{system_prompt}\n\nREQUIRED OUTPUT SCHEMA:\n{schema_hint}"
    messages = [
        SystemMessage(content=full_system),
        HumanMessage(content=user_content),
    ]

    # Attempt 1: Standard invocation
    try:
        response = await invoke_llm_with_retry(llm, messages)
        raw_text = response.content if hasattr(response, "content") else str(response)
        return parse_llm_json(raw_text)
    except LLMJsonParseError as parse_err:
        logger.warning(
            "Node '%s': First JSON parsing attempt failed (%s). Retrying with healing prompt...",
            node_name,
            parse_err,
        )
    except Exception as exc:
        logger.error("Node '%s': Error during primary invocation: %s", node_name, exc)
        return {"__error__": f"{node_name} invocation failed: {exc}"}

    # Attempt 2: Self-healing retry
    healing_messages = [
        SystemMessage(content=full_system),
        HumanMessage(content=user_content),
        HumanMessage(
            content="Your previous response was not valid JSON. Return ONLY a valid, raw JSON object matching the schema with no extra commentary or markdown."
        ),
    ]

    try:
        retry_response = await invoke_llm_with_retry(llm, healing_messages)
        raw_retry_text = retry_response.content if hasattr(retry_response, "content") else str(retry_response)
        return parse_llm_json(raw_retry_text)
    except Exception as exc:
        logger.error("Node '%s': Healing retry failed to produce valid JSON: %s", node_name, exc)
        return {"__error__": f"{node_name} produced malformed JSON after retry: {exc}"}
