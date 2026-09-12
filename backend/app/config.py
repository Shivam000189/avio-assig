"""Application configuration via pydantic-settings.

Loads settings from environment variables and a .env file. A single `settings`
instance is exported for use across the entire application.
"""

import json
from typing import Annotated, Any

from pydantic import field_validator
from pydantic_settings import BaseSettings
from pydantic_settings import NoDecode


class Settings(BaseSettings):
    """Central configuration object for the Complaint QMS API.

    Values are read from environment variables (or a .env file in the backend/
    working directory). Defaults are provided for non-secret fields.
    """

    app_name: str = "Complaint QMS API"
    debug: bool = False
    database_url: str = "postgresql://postgres:postgres@localhost:5432/complaint_qms"

    # AI Configuration (Groq + Models)
    groq_api_key: str = ""
    groq_model_fast: str = "gemma2-9b-it"
    groq_model_reasoning: str = "llama-3.3-70b-versatile"
    groq_max_retries: int = 3
    groq_temperature: float = 0.1

    # Gemini Optional Fallback
    gemini_api_key: str = ""

    # Document Upload Limits
    max_upload_mb: int = 10

    # Rate Limiting Configuration
    rate_limit_enabled: bool = True
    rate_limit_default: str = "100/minute"
    rate_limit_ai_analysis: str = "15/minute"
    rate_limit_uploads: str = "20/minute"
    rate_limit_auth: str = "5/minute"

    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "https://complaint-cyan.vercel.app",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        """Accept JSON arrays or comma-separated origins from deployment env vars."""
        if isinstance(value, list):
            return [str(origin).strip() for origin in value if str(origin).strip()]
        if isinstance(value, str):
            raw_value = value.strip()
            if not raw_value:
                return []
            try:
                decoded = json.loads(raw_value)
            except json.JSONDecodeError:
                decoded = raw_value.split(",")
            if isinstance(decoded, list):
                return [str(origin).strip() for origin in decoded if str(origin).strip()]
            if isinstance(decoded, str):
                return [decoded.strip()]
        raise ValueError("CORS_ORIGINS must be a JSON array or comma-separated origins")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
