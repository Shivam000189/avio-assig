"""Custom application exceptions for error handling across services and routers."""


class AppException(Exception):
    """Base exception for domain and application errors."""

    def __init__(self, message: str = "An application error occurred.") -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppException):
    """Raised when a requested resource is not found in the database."""

    def __init__(self, message: str = "Resource not found.") -> None:
        super().__init__(message)


class DatabaseUnavailableError(AppException):
    """Raised when the database connection is offline or unavailable."""

    def __init__(self, message: str = "Database service is unavailable.") -> None:
        super().__init__(message)


class GroqUnavailableError(AppException):
    """Raised when the Groq AI service is offline, credentials are invalid, or rate limits are exhausted."""

    def __init__(self, message: str = "AI analysis service is currently unavailable.") -> None:
        super().__init__(message)


class LLMJsonParseError(AppException):
    """Raised when the LLM output cannot be parsed into a valid JSON dictionary."""

    def __init__(self, message: str = "Failed to parse structured JSON from LLM response.") -> None:
        super().__init__(message)


class FileParseError(AppException):
    """Raised when an uploaded complaint document cannot be parsed or lacks extractable content."""

    def __init__(
        self,
        message: str,
        hint: str = "Upload a text-based PDF or paste the complaint text manually.",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint
