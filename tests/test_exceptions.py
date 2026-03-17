"""Tests for the exception hierarchy."""

from nautobot_mcp.exceptions import (
    NautobotAPIError,
    NautobotAuthenticationError,
    NautobotConnectionError,
    NautobotMCPError,
    NautobotNotFoundError,
    NautobotValidationError,
)


def test_base_exception_to_dict():
    """to_dict() should return structured error info."""
    error = NautobotMCPError(
        message="Something went wrong",
        code="TEST_ERROR",
        hint="Try again",
    )
    result = error.to_dict()
    assert result == {
        "error": "Something went wrong",
        "code": "TEST_ERROR",
        "hint": "Try again",
    }


def test_connection_error_code():
    """NautobotConnectionError should have code CONNECTION_ERROR."""
    error = NautobotConnectionError()
    assert error.code == "CONNECTION_ERROR"
    assert "connect" in error.message.lower()


def test_authentication_error_code():
    """NautobotAuthenticationError should have code AUTH_ERROR."""
    error = NautobotAuthenticationError()
    assert error.code == "AUTH_ERROR"
    assert "NAUTOBOT_TOKEN" in error.hint


def test_not_found_error_hint():
    """NautobotNotFoundError hint should contain actionable guidance."""
    error = NautobotNotFoundError()
    assert error.code == "NOT_FOUND"
    assert error.hint  # not empty


def test_validation_error():
    """NautobotValidationError should work with optional errors list."""
    error = NautobotValidationError(
        message="Invalid data",
        errors=[{"field": "name", "error": "required"}],
    )
    assert error.code == "VALIDATION_ERROR"
    result = error.to_dict()
    assert "validation_errors" in result
    assert len(result["validation_errors"]) == 1


def test_api_error_status_code():
    """NautobotAPIError should include status_code."""
    error = NautobotAPIError(
        message="Server error",
        status_code=500,
    )
    assert error.status_code == 500
    result = error.to_dict()
    assert result["status_code"] == 500


def test_exception_inheritance():
    """All custom exceptions should inherit from NautobotMCPError."""
    assert issubclass(NautobotConnectionError, NautobotMCPError)
    assert issubclass(NautobotAuthenticationError, NautobotMCPError)
    assert issubclass(NautobotNotFoundError, NautobotMCPError)
    assert issubclass(NautobotValidationError, NautobotMCPError)
    assert issubclass(NautobotAPIError, NautobotMCPError)


def test_exception_str_format():
    """Exception __str__ should include message and hint."""
    error = NautobotConnectionError(
        message="Cannot connect",
        hint="Check URL",
    )
    result = str(error)
    assert "Cannot connect" in result
    assert "Check URL" in result
