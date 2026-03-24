"""Tests for the REST bridge module.

Validates endpoint routing, validation, fuzzy matching, pagination,
device resolution, error handling, and CRUD operations.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from nautobot_mcp.bridge import (
    call_nautobot,
    _validate_endpoint,
    _suggest_endpoint,
    _parse_core_endpoint,
    _validate_method,
    _build_valid_endpoints,
    MAX_LIMIT,
    DEFAULT_LIMIT,
)
from nautobot_mcp.exceptions import (
    NautobotValidationError,
    NautobotNotFoundError,
)


class TestConstants:
    """Test bridge module constants."""

    def test_max_limit_is_200(self):
        assert MAX_LIMIT == 200

    def test_default_limit_is_50(self):
        assert DEFAULT_LIMIT == 50


class TestEndpointValidation:
    """Test endpoint validation against catalog."""

    def test_valid_core_endpoint(self):
        """Valid core endpoint passes validation."""
        _validate_endpoint("/api/dcim/devices/")  # Should not raise

    def test_valid_cms_endpoint(self):
        """Valid CMS endpoint passes validation."""
        _validate_endpoint("cms:juniper_static_routes")  # Should not raise

    def test_all_core_endpoints_valid(self):
        """Every endpoint in CORE_ENDPOINTS passes validation."""
        from nautobot_mcp.catalog.core_endpoints import CORE_ENDPOINTS
        for domain, entries in CORE_ENDPOINTS.items():
            for name, entry in entries.items():
                _validate_endpoint(entry["endpoint"])

    def test_all_cms_endpoints_valid(self):
        """Every CMS endpoint key passes validation."""
        from nautobot_mcp.cms.client import CMS_ENDPOINTS
        for endpoint_name in CMS_ENDPOINTS:
            _validate_endpoint(f"cms:{endpoint_name}")

    def test_invalid_core_endpoint_raises(self):
        """Invalid core endpoint raises NautobotValidationError."""
        with pytest.raises(NautobotValidationError, match="Unknown endpoint"):
            _validate_endpoint("/api/dcim/invalid_endpoint/")

    def test_invalid_cms_endpoint_raises(self):
        """Invalid CMS endpoint raises NautobotValidationError."""
        with pytest.raises(NautobotValidationError, match="Unknown endpoint"):
            _validate_endpoint("cms:nonexistent_endpoint")

    def test_unsupported_prefix_raises(self):
        """Endpoint with unsupported prefix raises error."""
        with pytest.raises(NautobotValidationError):
            _validate_endpoint("plugins:golden_config")


class TestFuzzyMatching:
    """Test 'did you mean?' suggestions via difflib."""

    def test_typo_in_core_endpoint(self):
        """Typo like 'device' → suggests 'devices'."""
        suggestions = _suggest_endpoint("/api/dcim/device/")
        assert any("devices" in s for s in suggestions)

    def test_typo_in_cms_endpoint(self):
        """Typo in CMS endpoint suggests closest match."""
        suggestions = _suggest_endpoint("cms:juniper_static_route")
        assert len(suggestions) > 0

    def test_invalid_endpoint_error_contains_suggestions(self):
        """Error message includes suggestions when close matches exist."""
        with pytest.raises(NautobotValidationError, match="Did you mean"):
            _validate_endpoint("/api/dcim/device/")

    def test_completely_wrong_endpoint(self):
        """Completely wrong endpoint may not have suggestions."""
        suggestions = _suggest_endpoint("zzz_completely_wrong_zzz")
        assert isinstance(suggestions, list)  # May be empty

    def test_valid_endpoints_list_not_empty(self):
        """Valid endpoints list includes both core and CMS entries."""
        valid = _build_valid_endpoints()
        assert len(valid) > 0
        assert any(ep.startswith("/api/") for ep in valid)
        assert any(ep.startswith("cms:") for ep in valid)


class TestMethodValidation:
    """Test HTTP method validation."""

    @pytest.mark.parametrize("method", ["GET", "POST", "PATCH", "DELETE"])
    def test_valid_methods(self, method):
        """All standard HTTP methods are valid."""
        result = _validate_method(method, "/api/dcim/devices/")
        assert result == method

    def test_case_insensitive(self):
        """Methods are case-insensitive."""
        assert _validate_method("get", "/api/dcim/devices/") == "GET"
        assert _validate_method("Post", "/api/dcim/devices/") == "POST"

    def test_invalid_method_raises(self):
        """Invalid HTTP method raises error."""
        with pytest.raises(NautobotValidationError, match="Invalid method"):
            _validate_method("PUT", "/api/dcim/devices/")


class TestCoreEndpointParsing:
    """Test /api/{app}/{endpoint}/ URL parsing."""

    def test_parse_simple_endpoint(self):
        """Parse simple endpoint: /api/dcim/devices/ → ('dcim', 'devices')."""
        assert _parse_core_endpoint("/api/dcim/devices/") == ("dcim", "devices")

    def test_parse_hyphenated_endpoint(self):
        """Parse hyphenated endpoint: /api/dcim/device-types/ → ('dcim', 'device_types')."""
        assert _parse_core_endpoint("/api/dcim/device-types/") == ("dcim", "device_types")

    def test_parse_ipam_endpoint(self):
        """Parse IPAM endpoint."""
        assert _parse_core_endpoint("/api/ipam/ip-addresses/") == ("ipam", "ip_addresses")

    def test_parse_circuits_endpoint(self):
        """Parse circuits endpoint."""
        assert _parse_core_endpoint("/api/circuits/circuits/") == ("circuits", "circuits")

    def test_invalid_format_raises(self):
        """Too-short endpoint path raises error."""
        with pytest.raises(NautobotValidationError, match="Invalid core endpoint"):
            _parse_core_endpoint("/api/")


class TestCallNautobotCoreGET:
    """Test call_nautobot for core GET operations."""

    def _make_mock_client(self, records=None, single_record=None):
        """Create a mock NautobotClient with pynautobot-like accessors."""
        client = MagicMock()
        endpoint = MagicMock()
        if records is not None:
            endpoint.all.return_value = records
            endpoint.filter.return_value = records
        if single_record is not None:
            endpoint.get.return_value = single_record
        # Wire up: client.api.dcim.devices → endpoint
        app = MagicMock()
        setattr(app, "devices", endpoint)
        client.api.dcim = app
        return client, endpoint

    def test_get_list_returns_wrapped_response(self):
        """GET list returns {count, results, endpoint, method}."""
        client, endpoint = self._make_mock_client(records=[])
        result = call_nautobot(client, "/api/dcim/devices/", "GET")
        assert "count" in result
        assert "results" in result
        assert result["endpoint"] == "/api/dcim/devices/"
        assert result["method"] == "GET"

    def test_get_with_filters(self):
        """GET with params calls filter()."""
        client, endpoint = self._make_mock_client(records=[])
        call_nautobot(client, "/api/dcim/devices/", "GET", params={"name": "router1"})
        endpoint.filter.assert_called_once_with(name="router1")

    def test_get_without_filters(self):
        """GET without params calls all()."""
        client, endpoint = self._make_mock_client(records=[])
        call_nautobot(client, "/api/dcim/devices/", "GET")
        endpoint.all.assert_called_once()

    def test_get_by_id(self):
        """GET with id calls get(id=...)."""
        mock_record = MagicMock()
        type(mock_record).__iter__ = lambda self: iter({"id": "uuid1"}.items())
        client, endpoint = self._make_mock_client(single_record=mock_record)
        result = call_nautobot(client, "/api/dcim/devices/", "GET", id="uuid1")
        endpoint.get.assert_called_once_with(id="uuid1")
        assert result["count"] == 1

    def test_get_by_id_not_found_raises(self):
        """GET by id returns NautobotNotFoundError when not found."""
        client = MagicMock()
        endpoint = MagicMock()
        endpoint.get.return_value = None  # Explicitly return None for not-found
        app = MagicMock()
        setattr(app, "devices", endpoint)
        client.api.dcim = app
        with pytest.raises(NautobotNotFoundError):
            call_nautobot(client, "/api/dcim/devices/", "GET", id="nonexistent")

    def test_unknown_app_raises(self):
        """Unknown app in endpoint raises validation error."""
        client = MagicMock()
        client.api.unknownapp = None  # simulate missing app
        # First mock: api.unknownapp returns None (getattr returns None)
        client.api = MagicMock()
        setattr(client.api, "unknownapp", None)
        with pytest.raises(NautobotValidationError, match="Unknown Nautobot app"):
            # Bypass endpoint catalog validation with a known valid endpoint structure
            # that points to an app that doesn't exist on the mock
            from nautobot_mcp.bridge import _execute_core
            _execute_core(client, "unknownapp", "devices", "GET", None, None, None, 50)

    def test_get_list_returns_method_in_response(self):
        """Response always includes the method used."""
        client, _ = self._make_mock_client(records=[])
        result = call_nautobot(client, "/api/dcim/devices/", "GET")
        assert result["method"] == "GET"


class TestCallNautobotCoreMutations:
    """Test call_nautobot for core POST/PATCH/DELETE operations."""

    def _make_mock_client(self):
        client = MagicMock()
        endpoint = MagicMock()
        record = MagicMock()
        type(record).__iter__ = lambda self: iter({"id": "new-uuid"}.items())
        endpoint.create.return_value = record
        endpoint.get.return_value = record
        app = MagicMock()
        setattr(app, "devices", endpoint)
        client.api.dcim = app
        return client, endpoint, record

    def test_post_creates_object(self):
        """POST calls create() with data."""
        client, endpoint, _ = self._make_mock_client()
        result = call_nautobot(client, "/api/dcim/devices/", "POST",
                               data={"name": "new-device", "role": "router"})
        endpoint.create.assert_called_once_with(name="new-device", role="router")
        assert result["method"] == "POST"

    def test_post_without_data_raises(self):
        """POST without data raises validation error."""
        client, _, _ = self._make_mock_client()
        with pytest.raises(NautobotValidationError, match="POST requires"):
            call_nautobot(client, "/api/dcim/devices/", "POST")

    def test_patch_updates_object(self):
        """PATCH updates object fields and saves."""
        client, endpoint, record = self._make_mock_client()
        call_nautobot(client, "/api/dcim/devices/", "PATCH",
                      id="uuid1", data={"name": "updated"})
        endpoint.get.assert_called_with(id="uuid1")
        record.save.assert_called_once()

    def test_patch_without_id_raises(self):
        """PATCH without id raises validation error."""
        client, _, _ = self._make_mock_client()
        with pytest.raises(NautobotValidationError, match="PATCH requires"):
            call_nautobot(client, "/api/dcim/devices/", "PATCH", data={"name": "x"})

    def test_patch_object_not_found_raises(self):
        """PATCH when object not found raises NautobotNotFoundError."""
        client = MagicMock()
        endpoint = MagicMock()
        endpoint.get.return_value = None
        app = MagicMock()
        setattr(app, "devices", endpoint)
        client.api.dcim = app
        with pytest.raises(NautobotNotFoundError, match="not found for update"):
            call_nautobot(client, "/api/dcim/devices/", "PATCH", id="uuid1", data={"name": "x"})

    def test_delete_removes_object(self):
        """DELETE calls record.delete()."""
        client, endpoint, record = self._make_mock_client()
        result = call_nautobot(client, "/api/dcim/devices/", "DELETE", id="uuid1")
        record.delete.assert_called_once()
        assert result["deleted"] == "uuid1"

    def test_delete_without_id_raises(self):
        """DELETE without id raises validation error."""
        client, _, _ = self._make_mock_client()
        with pytest.raises(NautobotValidationError, match="DELETE requires"):
            call_nautobot(client, "/api/dcim/devices/", "DELETE")

    def test_delete_object_not_found_raises(self):
        """DELETE when object not found raises NautobotNotFoundError."""
        client = MagicMock()
        endpoint = MagicMock()
        endpoint.get.return_value = None
        app = MagicMock()
        setattr(app, "devices", endpoint)
        client.api.dcim = app
        with pytest.raises(NautobotNotFoundError, match="not found for deletion"):
            call_nautobot(client, "/api/dcim/devices/", "DELETE", id="uuid1")


class TestPagination:
    """Test auto-pagination and hard cap behavior."""

    def _make_records(self, n):
        records = [MagicMock() for _ in range(n)]
        for r in records:
            type(r).__iter__ = lambda self: iter({"id": "x"}.items())
        return records

    def _make_client_with_records(self, records):
        client = MagicMock()
        endpoint = MagicMock()
        endpoint.all.return_value = records
        app = MagicMock()
        setattr(app, "devices", endpoint)
        client.api.dcim = app
        return client

    def test_results_capped_at_limit(self):
        """Results truncated when exceeding limit, with truncation metadata."""
        records = self._make_records(100)
        client = self._make_client_with_records(records)
        result = call_nautobot(client, "/api/dcim/devices/", "GET", limit=10)
        assert result["count"] == 10
        assert result["truncated"] is True
        assert result["total_available"] == 100

    def test_hard_cap_at_200(self):
        """Limit above 200 is silently capped."""
        records = self._make_records(300)
        client = self._make_client_with_records(records)
        result = call_nautobot(client, "/api/dcim/devices/", "GET", limit=500)
        assert result["count"] == 200
        assert result["truncated"] is True
        assert result["total_available"] == 300

    def test_no_truncation_when_under_limit(self):
        """No truncation metadata when results fit within limit."""
        records = self._make_records(5)
        client = self._make_client_with_records(records)
        result = call_nautobot(client, "/api/dcim/devices/", "GET", limit=50)
        assert result["count"] == 5
        assert "truncated" not in result

    def test_exact_limit_no_truncation(self):
        """Exactly at limit does not truncate."""
        records = self._make_records(50)
        client = self._make_client_with_records(records)
        result = call_nautobot(client, "/api/dcim/devices/", "GET", limit=50)
        assert result["count"] == 50
        assert "truncated" not in result


class TestCMSRouting:
    """Test CMS endpoint routing and device resolution."""

    def test_cms_endpoint_calls_cms_accessor(self):
        """CMS endpoint routes to CMS plugin accessor."""
        client = MagicMock()
        mock_endpoint = MagicMock()
        mock_endpoint.all.return_value = []
        with patch("nautobot_mcp.bridge.get_cms_endpoint", return_value=mock_endpoint):
            result = call_nautobot(client, "cms:juniper_static_routes", "GET")
        assert result["endpoint"] == "cms:juniper_static_routes"

    def test_cms_device_name_resolved(self):
        """Device name parameter is resolved to UUID for CMS endpoints."""
        client = MagicMock()
        mock_endpoint = MagicMock()
        mock_endpoint.filter.return_value = []
        with patch("nautobot_mcp.bridge.get_cms_endpoint", return_value=mock_endpoint), \
             patch("nautobot_mcp.bridge.resolve_device_id", return_value="uuid-123") as mock_resolve:
            call_nautobot(client, "cms:juniper_static_routes", "GET",
                         params={"device": "router1"})
        mock_resolve.assert_called_once_with(client, "router1")
        mock_endpoint.filter.assert_called_once_with(device="uuid-123")

    def test_cms_get_by_id(self):
        """CMS GET with id retrieves single object."""
        client = MagicMock()
        mock_record = MagicMock()
        type(mock_record).__iter__ = lambda self: iter({"id": "uuid-123"}.items())
        mock_endpoint = MagicMock()
        mock_endpoint.get.return_value = mock_record
        with patch("nautobot_mcp.bridge.get_cms_endpoint", return_value=mock_endpoint):
            result = call_nautobot(client, "cms:juniper_static_routes", "GET", id="uuid-123")
        assert result["count"] == 1
        mock_endpoint.get.assert_called_once_with(id="uuid-123")

    def test_cms_get_not_found_raises(self):
        """CMS GET by id raises NautobotNotFoundError when not found."""
        client = MagicMock()
        mock_endpoint = MagicMock()
        mock_endpoint.get.return_value = None
        with patch("nautobot_mcp.bridge.get_cms_endpoint", return_value=mock_endpoint):
            with pytest.raises(NautobotNotFoundError):
                call_nautobot(client, "cms:juniper_static_routes", "GET", id="nonexistent")

    def test_cms_post_resolves_device_in_data(self):
        """CMS POST resolves device name in data dict."""
        client = MagicMock()
        mock_record = MagicMock()
        type(mock_record).__iter__ = lambda self: iter({"id": "new"}.items())
        mock_endpoint = MagicMock()
        mock_endpoint.create.return_value = mock_record
        with patch("nautobot_mcp.bridge.get_cms_endpoint", return_value=mock_endpoint), \
             patch("nautobot_mcp.bridge.resolve_device_id", return_value="uuid-456") as mock_resolve:
            call_nautobot(client, "cms:juniper_static_routes", "POST",
                         data={"device": "router1", "destination": "0.0.0.0/0"})
        mock_resolve.assert_called_once_with(client, "router1")
        mock_endpoint.create.assert_called_once_with(device="uuid-456", destination="0.0.0.0/0")

    def test_cms_delete_object(self):
        """CMS DELETE removes object."""
        client = MagicMock()
        mock_record = MagicMock()
        mock_endpoint = MagicMock()
        mock_endpoint.get.return_value = mock_record
        with patch("nautobot_mcp.bridge.get_cms_endpoint", return_value=mock_endpoint):
            result = call_nautobot(client, "cms:juniper_static_routes", "DELETE", id="uuid-789")
        mock_record.delete.assert_called_once()
        assert result["deleted"] == "uuid-789"


class TestErrorHandling:
    """Test structured error responses."""

    def test_invalid_endpoint_error_has_hint(self):
        """Invalid endpoint error includes hint."""
        try:
            _validate_endpoint("/api/dcim/invalid/")
        except NautobotValidationError as e:
            assert e.hint  # Non-empty hint
            error_dict = e.to_dict()
            assert "error" in error_dict
            assert "hint" in error_dict

    def test_get_not_found_error(self):
        """GET by id returns structured error when object not found."""
        client = MagicMock()
        endpoint = MagicMock()
        endpoint.get.return_value = None  # Not found
        app = MagicMock()
        setattr(app, "devices", endpoint)
        client.api.dcim = app

        with pytest.raises(NautobotNotFoundError):
            call_nautobot(client, "/api/dcim/devices/", "GET", id="nonexistent")

    def test_invalid_method_error_structure(self):
        """Invalid method raises NautobotValidationError with proper message."""
        with pytest.raises(NautobotValidationError) as exc_info:
            _validate_method("PUT", "/api/dcim/devices/")
        e = exc_info.value
        assert "PUT" in str(e)
        error_dict = e.to_dict()
        assert "error" in error_dict
        assert "hint" in error_dict

    def test_invalid_endpoint_has_no_suggestion_catalog_hint(self):
        """Completely foreign endpoint gets catalog usage hint."""
        try:
            _validate_endpoint("zzz:completely_wrong")
        except NautobotValidationError as e:
            # Should have some hint
            assert e.hint

    def test_validation_error_code(self):
        """NautobotValidationError has correct error code."""
        try:
            _validate_endpoint("/api/dcim/invalid/")
        except NautobotValidationError as e:
            assert e.code == "VALIDATION_ERROR"
