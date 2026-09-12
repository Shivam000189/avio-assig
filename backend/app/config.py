"""Application configuration via pydantic-settings.

Loads settings from environment variables and a .env file. A single `settings`
instance is exported for use across the entire application.
"""

from pydantic_settings import BaseSettings


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

    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
