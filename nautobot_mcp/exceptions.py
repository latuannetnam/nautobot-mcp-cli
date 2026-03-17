"""Custom exception hierarchy for structured error handling.

All exceptions extend NautobotMCPError and provide structured error info
with actionable hints for troubleshooting.
"""

from __future__ import annotations

from typing import Optional


class NautobotMCPError(Exception):
    """Base exception for all nautobot-mcp errors.

    Provides structured error information with machine-readable code
    and human-readable hint for troubleshooting.
    """

    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        hint: str = "",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.hint = hint

    def to_dict(self) -> dict[str, str]:
        """Return structured error info for API/MCP responses."""
        return {
            "error": self.message,
            "code": self.code,
            "hint": self.hint,
        }

    def __str__(self) -> str:
        parts = [self.message]
        if self.hint:
            parts.append(f"Hint: {self.hint}")
        return " | ".join(parts)


class NautobotConnectionError(NautobotMCPError):
    """Raised when the Nautobot server is unreachable."""

    def __init__(
        self,
        message: str = "Cannot connect to Nautobot server",
        hint: str = "Check NAUTOBOT_URL setting and network connectivity",
    ) -> None:
        super().__init__(message=message, code="CONNECTION_ERROR", hint=hint)


class NautobotAuthenticationError(NautobotMCPError):
    """Raised when API authentication fails (invalid or expired token)."""

    def __init__(
        self,
        message: str = "Authentication failed",
        hint: str = "Check NAUTOBOT_TOKEN — generate a new token in Nautobot Admin → API Tokens",
    ) -> None:
        super().__init__(message=message, code="AUTH_ERROR", hint=hint)


class NautobotNotFoundError(NautobotMCPError):
    """Raised when a requested object is not found."""

    def __init__(
        self,
        message: str = "Object not found",
        hint: str = "Verify the name or ID exists in Nautobot",
    ) -> None:
        super().__init__(message=message, code="NOT_FOUND", hint=hint)


class NautobotValidationError(NautobotMCPError):
    """Raised when input data fails validation."""

    def __init__(
        self,
        message: str = "Validation failed",
        hint: str = "Check required fields and data formats",
        errors: Optional[list[dict]] = None,
    ) -> None:
        super().__init__(message=message, code="VALIDATION_ERROR", hint=hint)
        self.errors = errors or []

    def to_dict(self) -> dict:
        """Return structured error info including validation details."""
        result = super().to_dict()
        if self.errors:
            result["validation_errors"] = self.errors
        return result


class NautobotAPIError(NautobotMCPError):
    """Raised for generic Nautobot API errors with HTTP status codes."""

    def __init__(
        self,
        message: str = "Nautobot API error",
        status_code: int = 0,
        hint: str = "Check Nautobot server logs for details",
    ) -> None:
        super().__init__(message=message, code="API_ERROR", hint=hint)
        self.status_code = status_code

    def to_dict(self) -> dict:
        """Return structured error info including HTTP status."""
        result = super().to_dict()
        result["status_code"] = self.status_code
        return result
