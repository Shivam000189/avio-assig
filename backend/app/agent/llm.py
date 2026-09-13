"""Gemini LLM client factory and resilience layer.

Provides centralized access to Gemini generation with exponential backoff
retries and standardized error translation into domain exceptions.
"""

import logging
from typing import Any

import httpx
from langchain_core.messages import AIMessage
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

# Logical model routing constants retained for the graph API. Gemini is used for both tiers.
MODEL_FAST = "gemini-fast"
MODEL_REASONING = "gemini-reasoning"
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)


class GeminiLLM:
    """Small LangChain-compatible Gemini client used by graph nodes."""

    def __init__(self, model: str, temperature: float, max_tokens: int) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def ainvoke(self, messages: list[Any]) -> AIMessage:
        return await _invoke_gemini(
            messages=messages,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )


def get_llm(
    model: str = MODEL_FAST,
    temperature: float = 0.1,
    max_tokens: int = 1024,
) -> GeminiLLM:
    """Instantiate a Gemini-backed LLM client instance.

    Args:
        model: Logical graph tier. Gemini uses settings.gemini_model for the actual API model.
        temperature: Sampling temperature.
        max_tokens: Maximum response tokens allowed.

    Returns:
        Configured Gemini client.
    """
    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY is not configured in settings.")

    logger.debug("Using Gemini model [%s] for logical tier [%s].", settings.gemini_model, model)
    return GeminiLLM(
        model=settings.gemini_model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.2, min=0.1, max=2.0),
    retry=retry_if_not_exception_type(GroqUnavailableError),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def invoke_llm_with_retry(llm: GeminiLLM, messages: list[Any]) -> Any:
    """Execute a Gemini invocation with exponential backoff retry logic.

    Args:
        llm: Configured Gemini client.
        messages: Formatted message payload (system + human prompts).

    Returns:
        AIMessage response from the model.

    Raises:
        GroqUnavailableError: If all retry attempts fail due to auth, rate limit, or API outages.
    """
    try:
        return await llm.ainvoke(messages)
    except GroqUnavailableError:
        raise
    except Exception as exc:
        logger.error("Error communicating with Gemini API: %s", exc)
        raise GroqUnavailableError(f"Gemini API error: {exc}") from exc


def _message_content_text(message: Any) -> str:
    """Extract text from LangChain message content without assuming one shape."""
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content)


def _messages_to_gemini_prompt(messages: list[Any]) -> str:
    """Convert system/human LangChain messages into one Gemini prompt."""
    prompt_parts = []
    for message in messages:
        message_type = getattr(message, "type", "message")
        role = "System" if message_type == "system" else "User"
        prompt_parts.append(f"{role}:\n{_message_content_text(message)}")
    return "\n\n".join(prompt_parts)


def _wants_json(messages: list[Any]) -> bool:
    prompt = _messages_to_gemini_prompt(messages).lower()
    return "required output schema" in prompt or "return only a valid json" in prompt


async def _invoke_gemini(
    messages: list[Any],
    model: str,
    temperature: float,
    max_tokens: int,
) -> AIMessage:
    """Call Gemini and return a LangChain-compatible message."""
    api_key = settings.gemini_api_key
    if not api_key:
        raise GroqUnavailableError("GEMINI_API_KEY is not configured")
    if not api_key.startswith("AIza"):
        raise GroqUnavailableError(
            "GEMINI_API_KEY is not a Google AI Studio API key. "
            "Create a Gemini API key in Google AI Studio; it usually starts with 'AIza'."
        )

    url = GEMINI_API_URL.format(model=model)
    generation_config: dict[str, Any] = {
        "temperature": temperature,
        "maxOutputTokens": max_tokens,
    }
    if _wants_json(messages):
        generation_config["responseMimeType"] = "application/json"

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": _messages_to_gemini_prompt(messages)}],
            }
        ],
        "generationConfig": generation_config,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            response = await client.post(url, params={"key": api_key}, json=payload)
            if response.is_error:
                error_text = response.text[:500]
                raise GroqUnavailableError(
                    f"Gemini failed with HTTP {response.status_code}: {error_text}"
                )
    except Exception as gemini_exc:
        logger.error("Gemini request failed: %s", gemini_exc)
        if isinstance(gemini_exc, GroqUnavailableError):
            raise gemini_exc
        raise GroqUnavailableError(f"Gemini request failed: {gemini_exc}") from gemini_exc

    data = response.json()
    candidates = data.get("candidates") or []
    parts = (
        candidates[0].get("content", {}).get("parts", [])
        if candidates and isinstance(candidates[0], dict)
        else []
    )
    text = "\n".join(
        str(part.get("text", "")).strip()
        for part in parts
        if isinstance(part, dict) and str(part.get("text", "")).strip()
    )
    if not text:
        raise GroqUnavailableError("Gemini returned an empty response")

    logger.info("Used Gemini model [%s].", model)
    return AIMessage(content=text)


async def _invoke_gemini_with_fallback(
    messages: list[Any],
    cause: Exception | None = None,
) -> AIMessage:
    """Backward-compatible helper for tests and older imports."""
    try:
        return await _invoke_gemini(
            messages=messages,
            model=settings.gemini_model,
            temperature=settings.groq_temperature,
            max_tokens=1024,
        )
    except GroqUnavailableError as exc:
        raise exc from cause
