"""LLM Client Factory and Resilience Layer for Groq.

Provides centralized access to ChatGroq instances with exponential backoff
retries and standardized error translation into domain exceptions.
"""

import logging
from typing import Any

from langchain_groq import ChatGroq
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.exceptions import GroqUnavailableError

logger = logging.getLogger(__name__)

# Model Routing Tier Constants
MODEL_FAST = "gemma2-9b-it"  # High-throughput, low-latency (extraction, completeness, summary)
MODEL_REASONING = "llama-3.3-70b-versatile"  # Deep contextual reasoning (risk analysis, CAPA, root cause)


def get_llm(
    model: str = MODEL_FAST,
    temperature: float = 0.1,
    max_tokens: int = 1024,
) -> ChatGroq:
    """Instantiate a ChatGroq LLM client instance.

    Args:
        model: Target Groq model identifier (e.g. gemma2-9b-it or llama-3.3-70b-versatile).
        temperature: Sampling temperature (0.0 for deterministic extraction, 0.2-0.3 for reasoning).
        max_tokens: Maximum response tokens allowed.

    Returns:
        Configured ChatGroq instance.
    """
    api_key = settings.groq_api_key
    if not api_key:
        logger.warning("GROQ_API_KEY is not configured in settings.")

    return ChatGroq(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key or "missing_key",
        max_retries=settings.groq_max_retries,
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.2, min=0.1, max=2.0),
    retry=retry_if_not_exception_type(GroqUnavailableError),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def invoke_llm_with_retry(llm: ChatGroq, messages: list[Any]) -> Any:
    """Execute an LLM invocation with exponential backoff retry logic.

    Args:
        llm: Configured ChatGroq instance.
        messages: Formatted message payload (system + human prompts).

    Returns:
        AIMessage response from the model.

    Raises:
        GroqUnavailableError: If all retry attempts fail due to rate limits or API outages.
    """
    try:
        return await llm.ainvoke(messages)
    except GroqUnavailableError:
        raise
    except Exception as exc:
        err_str = str(exc).lower()
        logger.error("Error communicating with Groq API: %s", exc)
        if (
            "rate_limit" in err_str
            or "429" in err_str
            or "unauthorized" in err_str
            or "invalid_api_key" in err_str
            or "connection" in err_str
            or "refused" in err_str
        ):
            raise GroqUnavailableError(f"Groq API error: {exc}") from exc
        raise
