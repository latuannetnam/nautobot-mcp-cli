"""Tests for NautobotClient error handling (ERR-01, ERR-02, ERR-04)."""

from __future__ import annotations

from unittest.mock import MagicMock
import json
import requests  # needed for HTTPError in test_count_vlans_500_raises_nautobot_api_error

import pytest

import pynautobot
from nautobot_mcp.client import (
    NautobotClient,
    _get_hint_for_request,
    ERROR_HINTS,
    STATUS_CODE_HINTS,
)
from nautobot_mcp.exceptions import NautobotValidationError, NautobotAPIError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_fake_response(status_code: int, text: str, url: str) -> MagicMock:
    """Build a fake requests.Response-like object for mocking pynautobot RequestError."""
    fake = MagicMock()
    fake.status_code = status_code
    fake.text = text
    fake.url = url
    fake.json = lambda: json.loads(text) if text else {}
    return fake


class FakeRequestError(pynautobot.core.query.RequestError):
    """Fake pynautobot RequestError for testing — inherits from the real class for isinstance() check."""

    def __init__(self, status_code: int, text: str, url: str) -> None:
        # Build the fake response first
        fake_resp = make_fake_response(status_code, text, url)
        # Pass the response object to parent __init__ (it stores and checks it)
        super().__init__(fake_resp)

    def __str__(self) -> str:
        if self.req is not None:
            return f"{self.req.status_code} error"
        return "RequestError"


def make_request_error(status_code: int, text: str, url: str) -> FakeRequestError:
    """Build a fake pynautobot RequestError with a nested fake response."""
    return FakeRequestError(status_code, text, url)


# ---------------------------------------------------------------------------
# _get_hint_for_request
# ---------------------------------------------------------------------------


class TestGetHintForRequest:
    """Test hint resolution in _get_hint_for_request (ERR-02 + ERR-04)."""

    def test_endpoint_hint_returns_device_hint(self):
        """Device endpoint should return the device-specific hint."""
        fake_req = make_fake_response(400, "{}", "/api/dcim/devices/")
        hint = _get_hint_for_request(fake_req, "list", "Device", 400)
        assert "name" in hint.lower() or "uuid" in hint.lower()
        assert "Check Nautobot server logs" not in hint

    def test_interface_endpoint_hint(self):
        """Interface endpoint should return interface-specific hint."""
        fake_req = make_fake_response(400, "{}", "/api/dcim/interfaces/")
        hint = _get_hint_for_request(fake_req, "filter", "Interface", 400)
        assert "UUID" in hint or "device" in hint.lower()

    def test_ip_address_endpoint_hint(self):
        """IP addresses endpoint should return IP-specific hint."""
        fake_req = make_fake_response(400, "{}", "/api/ipam/ip-addresses/")
        hint = _get_hint_for_request(fake_req, "list", "IPAddress", 400)
        assert "address" in hint.lower() or "family" in hint.lower()

    def test_longest_match_wins(self):
        """A more specific path should override a less specific one."""
        # /api/dcim/devices/<uuid>/interfaces/ is more specific than /api/dcim/interfaces/
        fake_req = make_fake_response(400, "{}", "/api/dcim/devices/abc-123/interfaces/")
        hint = _get_hint_for_request(fake_req, "list", "Interface", 400)
        # Should match the device-specific interfaces hint, not the generic interfaces hint
        assert "UUID" in hint

    def test_status_code_fallback_500(self):
        """Unknown endpoint with 500 should return 500 hint."""
        fake_req = make_fake_response(500, "Server Error", "/api/unknown/endpoint/")
        hint = _get_hint_for_request(fake_req, "list", "Unknown", 500)
        assert "500" not in hint  # hint should be human-readable, not just the code
        assert "health" in hint.lower() or "server" in hint.lower()

    def test_status_code_fallback_429(self):
        """Unknown endpoint with 429 should return rate-limit hint."""
        fake_req = make_fake_response(429, "Rate Limited", "/api/unknown/")
        hint = _get_hint_for_request(fake_req, "list", "Resource", 429)
        assert "rate" in hint.lower() or "retry" in hint.lower()

    def test_no_response_returns_fallback(self):
        """No response object should fall back to operation-specific generic hint."""
        hint = _get_hint_for_request(None, "list", "Device", 500)
        assert len(hint) > 0
        assert "check" in hint.lower()

    def test_unknown_operation_returns_generic_hint(self):
        """Unknown operation should return generic fallback."""
        fake_req = make_fake_response(404, "Not Found", "/api/dcim/devices/")
        hint = _get_hint_for_request(fake_req, "unknown_op", "Device", 404)
        assert len(hint) > 0


# ---------------------------------------------------------------------------
# ERR-01: 400 body parsing -> NautobotValidationError.errors
# ---------------------------------------------------------------------------


class TestHandleApiError400:
    """Test 400 error body parsing in _handle_api_error (ERR-01)."""

    def test_400_with_field_errors_parsed(self):
        """DRF 400 body with field errors should populate NautobotValidationError.errors."""
        drf_body = {
            "name": ["This field is required."],
            "device": ["Invalid pk 'abc' — object does not exist."],
        }
        fake_error = make_request_error(400, json.dumps(drf_body), "/api/dcim/devices/")

        client = NautobotClient.__new__(NautobotClient)
        client._profile = MagicMock()
        client._api = MagicMock()

        with pytest.raises(NautobotValidationError) as exc_info:
            client._handle_api_error(fake_error, operation="create", model_name="Device")

        assert exc_info.value.errors is not None
        assert len(exc_info.value.errors) == 2

        # Find errors by field name
        errors_by_field = {e["field"]: e["error"] for e in exc_info.value.errors}
        assert "name" in errors_by_field
        assert "This field is required" in errors_by_field["name"]
        assert "device" in errors_by_field
        assert "Invalid pk" in errors_by_field["device"]

        # to_dict() should include validation_errors
        err_dict = exc_info.value.to_dict()
        assert "validation_errors" in err_dict
        assert len(err_dict["validation_errors"]) == 2

    def test_400_with_non_field_errors(self):
        """DRF 400 body with non_field_errors should be included as field="_detail"."""
        drf_body = {"non_field_errors": ["Object with name='foo' already exists."]}
        fake_error = make_request_error(400, json.dumps(drf_body), "/api/dcim/devices/")

        client = NautobotClient.__new__(NautobotClient)
        client._profile = MagicMock()
        client._api = MagicMock()

        with pytest.raises(NautobotValidationError) as exc_info:
            client._handle_api_error(fake_error, operation="create", model_name="Device")

        assert exc_info.value.errors is not None
        errors_by_field = {e["field"]: e["error"] for e in exc_info.value.errors}
        assert "_detail" in errors_by_field
        assert "already exists" in errors_by_field["_detail"]

    def test_400_with_detail_string(self):
        """DRF 400 body with plain string detail should be treated as _detail error."""
        drf_body = {"detail": "Invalid filter parameter"}
        fake_error = make_request_error(400, json.dumps(drf_body), "/api/dcim/devices/")

        client = NautobotClient.__new__(NautobotClient)
        client._profile = MagicMock()
        client._api = MagicMock()

        with pytest.raises(NautobotValidationError) as exc_info:
            client._handle_api_error(fake_error, operation="list", model_name="Device")

        assert exc_info.value.errors is not None
        assert any(e["field"] == "_detail" for e in exc_info.value.errors)

    def test_400_with_non_json_body(self):
        """400 with non-JSON body should not crash — fall back gracefully."""
        # "Internal Server Error" is not valid JSON, so _json.loads raises ValueError
        fake_error = FakeRequestError(400, "Internal Server Error", "/api/dcim/devices/")

        client = NautobotClient.__new__(NautobotClient)
        client._profile = MagicMock()
        client._api = MagicMock()

        with pytest.raises(NautobotValidationError) as exc_info:
            client._handle_api_error(fake_error, operation="list", model_name="Device")

        # Should still raise but with empty/missing errors (fallback behavior)
        assert exc_info.value.errors == [] or exc_info.value.errors is None

    def test_400_with_none_req(self):
        """400 where error.req is None should not crash."""
        fake_error = FakeRequestError.__new__(FakeRequestError)
        # Bypass the req property by setting in __dict__ directly
        object.__setattr__(fake_error, "req", None)
        fake_error.args = (None,)

        client = NautobotClient.__new__(NautobotClient)
        client._profile = MagicMock()
        client._api = MagicMock()

        # With effective_status=400 (preserved), raises NautobotValidationError
        with pytest.raises(NautobotValidationError):
            client._handle_api_error(fake_error, operation="list", model_name="Device")


# ---------------------------------------------------------------------------
# ERR-02 + ERR-04: NautobotAPIError hint enrichment
# ---------------------------------------------------------------------------


class TestHandleApiErrorHintMap:
    """Test that NautobotAPIError uses endpoint-specific or status-code hints (ERR-02, ERR-04)."""

    def test_500_error_uses_status_code_hint(self):
        """500 error should include status-code-based hint, not generic message."""
        # Use unknown endpoint URL so ERROR_HINTS doesn't match (status-code hint should win)
        fake_error = make_request_error(500, "Internal Server Error", "/api/unknown/endpoint/")

        client = NautobotClient.__new__(NautobotClient)
        client._profile = MagicMock()
        client._api = MagicMock()

        with pytest.raises(NautobotAPIError) as exc_info:
            client._handle_api_error(fake_error, operation="list", model_name="Device")

        assert exc_info.value.status_code == 500
        assert exc_info.value.hint != "Check Nautobot server logs for details"
        assert len(exc_info.value.hint) > 0
        assert "health" in exc_info.value.hint.lower() or "server" in exc_info.value.hint.lower()

    def test_429_error_uses_rate_limit_hint(self):
        """429 error should include rate-limit specific hint."""
        # Use unknown endpoint URL so ERROR_HINTS doesn't match (status-code hint should win)
        fake_error = make_request_error(429, "Rate Limited", "/api/unknown/endpoint/")

        client = NautobotClient.__new__(NautobotClient)
        client._profile = MagicMock()
        client._api = MagicMock()

        with pytest.raises(NautobotAPIError) as exc_info:
            client._handle_api_error(fake_error, operation="list", model_name="Device")

        assert exc_info.value.status_code == 429
        assert "rate" in exc_info.value.hint.lower() or "retry" in exc_info.value.hint.lower()

    def test_known_endpoint_gets_specific_hint(self):
        """Known endpoint should get endpoint-specific hint, not generic fallback."""
        fake_error = make_request_error(400, "Bad Request", "/api/dcim/interfaces/")

        client = NautobotClient.__new__(NautobotClient)
        client._profile = MagicMock()
        client._api = MagicMock()

        # 400 raises NautobotValidationError, not NautobotAPIError
        with pytest.raises(NautobotValidationError) as exc_info:
            client._handle_api_error(fake_error, operation="filter", model_name="Interface")

        # Hint should be interface-specific, not generic
        assert "UUID" in exc_info.value.hint or "device" in exc_info.value.hint.lower()
        assert exc_info.value.hint != "Check required fields and data formats"

    def test_api_error_to_dict_includes_hint(self):
        """NautobotAPIError.to_dict() should include the hint field."""
        from nautobot_mcp.exceptions import NautobotAPIError
        err = NautobotAPIError(
            message="Server error",
            status_code=500,
            hint="Check Nautobot health",
        )
        d = err.to_dict()
        assert "hint" in d
        assert d["hint"] == "Check Nautobot health"

    def test_validation_error_to_dict_includes_validation_errors(self):
        """NautobotValidationError.to_dict() should include validation_errors when set."""
        from nautobot_mcp.exceptions import NautobotValidationError
        err = NautobotValidationError(
            message="Bad data",
            errors=[{"field": "name", "error": "required"}],
        )
        d = err.to_dict()
        assert "validation_errors" in d
        assert d["validation_errors"][0]["field"] == "name"


# ---------------------------------------------------------------------------
# VLAN-01 + VLAN-02: count() with UUID location filter
# ---------------------------------------------------------------------------


class TestVLANCount500:
    """Test count() behavior with UUID location filter and 500 error path.

    Covers:
    - D-01: location=<uuid> succeeds with 200
    - D-03: 500 propagates as NautobotAPIError
    - D-04: caller catches NautobotAPIError
    """

    def _make_client(self, mock_nautobot_profile) -> NautobotClient:
        client = NautobotClient(profile=mock_nautobot_profile)
        client._api = MagicMock()
        client.api.http_session = MagicMock()
        return client

    def test_count_vlans_by_uuid_returns_int(self, mock_nautobot_profile):
        """location=<uuid> produces a valid count integer (200 OK)."""
        client = self._make_client(mock_nautobot_profile)

        fake_resp = MagicMock()
        fake_resp.ok = True
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"count": 42}
        client.api.http_session.get.return_value = fake_resp

        result = client.count("ipam", "vlans", location="5555-6666-7777-8888")
        assert result == 42
        # Verify UUID was passed, not name
        call_args = client.api.http_session.get.call_args
        assert "5555-6666-7777-8888" in str(call_args)

    def test_count_vlans_500_raises_nautobot_api_error(self, mock_nautobot_profile):
        """500 from /count/ propagates as NautobotAPIError (D-03)."""
        client = self._make_client(mock_nautobot_profile)

        # Direct HTTP returns 500
        fake_resp_500 = MagicMock()
        fake_resp_500.ok = False
        fake_resp_500.status_code = 500
        fake_resp_500.text = "Internal Server Error"
        fake_resp_500.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=fake_resp_500
        )

        # pynautobot fallback also raises 500 (e.g. RequestError)
        fallback_error = make_request_error(500, "Internal Server Error", "/api/ipam/vlans/")
        client.api.http_session.get.return_value = fake_resp_500

        # Set up pynautobot endpoint to also raise
        mock_vlans = MagicMock()
        mock_vlans.count.side_effect = fallback_error
        client.api.ipam.vlans = mock_vlans

        with pytest.raises(NautobotAPIError) as exc_info:
            client.count("ipam", "vlans", location="5555-6666-7777-8888")

        assert exc_info.value.status_code == 500

    def test_count_vlans_fallback_404_returns_pynautobot_count(
        self, mock_nautobot_profile
    ):
        """404 from /count/ falls back to pynautobot .count() (D-03 path: 404 → pass)."""
        client = self._make_client(mock_nautobot_profile)

        # Direct HTTP returns 404 (endpoint not supported)
        fake_resp_404 = MagicMock()
        fake_resp_404.ok = False
        fake_resp_404.status_code = 404
        fake_resp_404.text = "Not Found"
        fake_resp_404.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=fake_resp_404
        )
        client.api.http_session.get.return_value = fake_resp_404

        # pynautobot fallback succeeds
        mock_vlans = MagicMock()
        mock_vlans.count.return_value = 17
        client.api.ipam.vlans = mock_vlans

        result = client.count("ipam", "vlans", location="5555-6666-7777-8888")
        assert result == 17
        mock_vlans.count.assert_called_once_with(location="5555-6666-7777-8888")

