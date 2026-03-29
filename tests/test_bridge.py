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
    _strip_uuid_from_endpoint,
    _guard_filter_params,
    _execute_core,
    _execute_cms,
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
        """GET with params calls filter() with limit applied."""
        client, endpoint = self._make_mock_client(records=[])
        call_nautobot(client, "/api/dcim/devices/", "GET", params={"name": "router1"})
        endpoint.filter.assert_called_once_with(name="router1", limit=50)

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
    """Test server-side limit/offset are passed to pynautobot."""

    def _make_record(self):
        """Create a mock record that dict() can serialize."""
        r = MagicMock()
        type(r).__iter__ = lambda self: iter({"id": "x"}.items())
        return r

    def _make_client_with_records(self, records):
        client = MagicMock()
        endpoint = MagicMock()
        endpoint.all.return_value = records
        endpoint.filter.return_value = records
        app = MagicMock()
        setattr(app, "devices", endpoint)
        client.api.dcim = app
        return client

    def test_limit_passed_to_all(self):
        """limit=N is passed through to endpoint_accessor.all() for server-side pagination."""
        records = [self._make_record() for _ in range(10)]
        client = self._make_client_with_records(records)
        result = call_nautobot(client, "/api/dcim/devices/", "GET", limit=10)
        # Verify all() was called with limit=10 (not that it returns all 100)
        endpoint = client.api.dcim.devices
        endpoint.all.assert_called_with(limit=10)
        assert result["count"] == 10
        assert "truncated" not in result

    def test_offset_passed_to_all(self):
        """offset=N is passed through to endpoint_accessor.all() for pagination."""
        records = [self._make_record() for _ in range(5)]
        client = self._make_client_with_records(records)
        result = call_nautobot(client, "/api/dcim/devices/", "GET", limit=5, offset=20)
        endpoint = client.api.dcim.devices
        endpoint.all.assert_called_with(limit=5, offset=20)
        assert result["count"] == 5

    def test_limit_and_offset_passed_to_filter(self):
        """limit and offset are passed through to endpoint_accessor.filter() when params given."""
        records = [self._make_record() for _ in range(3)]
        client = self._make_client_with_records(records)
        result = call_nautobot(
            client, "/api/dcim/devices/", "GET",
            params={"status": "active"}, limit=3, offset=10
        )
        endpoint = client.api.dcim.devices
        endpoint.filter.assert_called_with(status="active", limit=3, offset=10)
        assert result["count"] == 3

    def test_no_truncation_metadata_added(self):
        """Server-side limit means truncation metadata is no longer added."""
        records = [self._make_record() for _ in range(5)]
        client = self._make_client_with_records(records)
        result = call_nautobot(client, "/api/dcim/devices/", "GET", limit=50)
        assert result["count"] == 5
        assert "truncated" not in result
        assert "total_available" not in result


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
        mock_endpoint.filter.assert_called_once_with(device="uuid-123", limit=50)

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


class TestUUIDPathNormalization:
    """Test UUID path segment detection and stripping."""

    def test_no_uuid_returns_unchanged(self):
        """Path without UUID returns unchanged."""
        base, uuid = _strip_uuid_from_endpoint("/api/dcim/devices/")
        assert base == "/api/dcim/devices/"
        assert uuid is None

    def test_uuid_stripped_from_core_path(self):
        """UUID segment stripped from core endpoint path."""
        base, uuid = _strip_uuid_from_endpoint(
            "/api/dcim/device-types/abc12345-def4-5678-9abc-def012345678/"
        )
        assert base == "/api/dcim/device-types/"
        assert uuid == "abc12345-def4-5678-9abc-def012345678"

    def test_uuid_stripped_preserves_app_and_endpoint(self):
        """Stripping UUID preserves app and endpoint names."""
        base, uuid = _strip_uuid_from_endpoint(
            "/api/ipam/ip-addresses/11111111-2222-3333-4444-555555555555/"
        )
        assert base == "/api/ipam/ip-addresses/"
        assert uuid == "11111111-2222-3333-4444-555555555555"

    def test_cms_endpoint_not_affected(self):
        """CMS endpoints (no /api/ prefix) pass through unchanged."""
        base, uuid = _strip_uuid_from_endpoint("cms:juniper_static_routes")
        assert base == "cms:juniper_static_routes"
        assert uuid is None

    def test_nested_uuid_path_raises_error(self):
        """Path with multiple UUIDs raises NautobotValidationError."""
        with pytest.raises(NautobotValidationError, match="Nested UUID paths"):
            _strip_uuid_from_endpoint(
                "/api/dcim/devices/11111111-2222-3333-4444-555555555555/"
                "interfaces/66666666-7777-8888-9999-aaaaaaaaaaaa/"
            )

    def test_uppercase_uuid_stripped(self):
        """UUID with uppercase hex chars is still detected."""
        base, uuid = _strip_uuid_from_endpoint(
            "/api/dcim/devices/ABCDEF12-3456-7890-ABCD-EF1234567890/"
        )
        assert base == "/api/dcim/devices/"
        assert uuid == "ABCDEF12-3456-7890-ABCD-EF1234567890"


class TestCallNautobotWithUUID:
    """Test call_nautobot transparently handles UUID-embedded paths."""

    def _make_mock_client(self):
        client = MagicMock()
        record = MagicMock()
        type(record).__iter__ = lambda self: iter({"id": "uuid-123"}.items())
        endpoint = MagicMock()
        endpoint.get.return_value = record
        app = MagicMock()
        setattr(app, "devices", endpoint)
        client.api.dcim = app
        return client, endpoint

    def test_uuid_in_path_used_as_id(self):
        """UUID in path is extracted and used as id parameter."""
        client, endpoint = self._make_mock_client()
        result = call_nautobot(
            client,
            "/api/dcim/devices/abc12345-def4-5678-9abc-def012345678/",
            "GET",
        )
        endpoint.get.assert_called_once_with(id="abc12345-def4-5678-9abc-def012345678")
        assert result["count"] == 1

    def test_explicit_id_overrides_path_uuid(self):
        """Explicit id parameter takes precedence over URL-embedded UUID."""
        client, endpoint = self._make_mock_client()
        call_nautobot(
            client,
            "/api/dcim/devices/abc12345-def4-5678-9abc-def012345678/",
            "GET",
            id="explicit-id-11111111-2222-3333-4444",
        )
        endpoint.get.assert_called_once_with(id="explicit-id-11111111-2222-3333-4444")

    def test_response_preserves_original_endpoint(self):
        """Response endpoint field shows the original UUID-embedded path."""
        client, endpoint = self._make_mock_client()
        result = call_nautobot(
            client,
            "/api/dcim/devices/abc12345-def4-5678-9abc-def012345678/",
            "GET",
        )
        assert result["endpoint"] == "/api/dcim/devices/abc12345-def4-5678-9abc-def012345678/"


class TestParamGuard:
    """Test _guard_filter_params() guard logic."""

    def test_none_params_returns_none(self):
        """None input returns None (passthrough)."""
        assert _guard_filter_params(None) is None

    def test_empty_dict_returns_empty_dict(self):
        """Empty dict returns empty dict."""
        assert _guard_filter_params({}) == {}

    # --- Small list (≤ 500): converted to comma-separated string ---

    def test_id_in_small_list_converted_to_string(self):
        """Small __in list is converted to comma-separated string."""
        params = {"id__in": ["uuid1", "uuid2", "uuid3"]}
        guarded = _guard_filter_params(params)
        assert guarded == {"id__in": "uuid1,uuid2,uuid3"}

    def test_interface_in_small_list_converted(self):
        """interface__in list converted."""
        params = {"interface__in": ["iface1", "iface2"]}
        guarded = _guard_filter_params(params)
        assert guarded == {"interface__in": "iface1,iface2"}

    def test_exactly_500_items_converted(self):
        """Exactly 500 items is allowed and converted."""
        items = [f"uuid-{i}" for i in range(500)]
        params = {"id__in": items}
        guarded = _guard_filter_params(params)
        assert len(guarded["id__in"].split(",")) == 500
        assert isinstance(guarded["id__in"], str)

    def test_mixed_in_and_regular_params(self):
        """Mixed __in and non-__in params: __in converted, others passed through."""
        params = {"id__in": ["a", "b"], "status": "active", "name": "router1"}
        guarded = _guard_filter_params(params)
        assert guarded == {"id__in": "a,b", "status": "active", "name": "router1"}

    # --- Large list (> 500): raises NautobotValidationError ---

    def test_id_in_501_items_raises(self):
        """501 items in id__in raises NautobotValidationError."""
        params = {"id__in": [f"uuid-{i}" for i in range(501)]}
        with pytest.raises(NautobotValidationError, match="id__in.*501.*500"):
            _guard_filter_params(params)

    def test_interface_in_600_items_raises(self):
        """600 items in interface__in raises."""
        params = {"interface__in": [f"iface-{i}" for i in range(600)]}
        with pytest.raises(NautobotValidationError, match="interface__in.*600"):
            _guard_filter_params(params)

    def test_error_message_includes_param_key(self):
        """Error message names the offending parameter key."""
        params = {"custom__in": [f"val-{i}" for i in range(600)]}
        with pytest.raises(NautobotValidationError, match="custom__in"):
            _guard_filter_params(params)

    def test_error_message_includes_count(self):
        """Error message includes the actual item count."""
        params = {"id__in": [f"uuid-{i}" for i in range(750)]}
        with pytest.raises(NautobotValidationError, match="750"):
            _guard_filter_params(params)

    # --- Non-__in list params: pass through unchanged ---

    def test_tag_list_passed_through_unchanged(self):
        """Non-__in list params pass through as-is (list objects)."""
        params = {"tag": ["foo", "bar", "baz"]}
        guarded = _guard_filter_params(params)
        assert guarded == {"tag": ["foo", "bar", "baz"]}  # list unchanged

    def test_status_list_passed_through_unchanged(self):
        """status=[active, planned] passed through unchanged."""
        params = {"status": ["active", "planned"]}
        guarded = _guard_filter_params(params)
        assert guarded == {"status": ["active", "planned"]}

    def test_location_list_passed_through_unchanged(self):
        """location=[uuid1, uuid2] passed through unchanged (no __in suffix)."""
        params = {"location": ["loc-uuid-1", "loc-uuid-2"]}
        guarded = _guard_filter_params(params)
        assert guarded == {"location": ["loc-uuid-1", "loc-uuid-2"]}

    def test_non_list_params_passed_through(self):
        """Scalar params pass through unchanged."""
        params = {"name": "router1", "status": "active", "limit": 50}
        guarded = _guard_filter_params(params)
        assert guarded == {"name": "router1", "status": "active", "limit": 50}

    def test_tuple_converted_to_string(self):
        """Tuple __in value is converted to string (same as list)."""
        params = {"id__in": ("uuid-1", "uuid-2")}
        guarded = _guard_filter_params(params)
        assert guarded == {"id__in": "uuid-1,uuid-2"}


class TestParamGuardIntegration:
    """Test _execute_core() and _execute_cms() raise for oversized __in lists."""

    def _mock_client_core(self):
        """Set up mock for _execute_core path."""
        client = MagicMock()
        endpoint = MagicMock()
        endpoint.filter.return_value = []
        app = MagicMock()
        setattr(app, "devices", endpoint)
        client.api.dcim = app
        return client, endpoint

    def test_execute_core_large_id_in_raises(self):
        """_execute_core raises when params contains id__in > 500 items."""
        client, _ = self._mock_client_core()
        params = {"id__in": [f"uuid-{i}" for i in range(600)]}
        with pytest.raises(NautobotValidationError, match="id__in.*600.*500"):
            _execute_core(client, "dcim", "devices", "GET", params, None, None, 50)

    def test_execute_core_small_id_in_works(self):
        """_execute_core works when id__in ≤ 500 (converted to string)."""
        client, endpoint = self._mock_client_core()
        params = {"id__in": ["uuid-1", "uuid-2", "uuid-3"]}
        _execute_core(client, "dcim", "devices", "GET", params, None, None, 50)
        # pynautobot accepts string for __in — verify filter called with CSV string
        call_kwargs = endpoint.filter.call_args
        assert call_kwargs[1]["id__in"] == "uuid-1,uuid-2,uuid-3"

    def test_execute_core_non_in_list_unchanged(self):
        """_execute_core passes non-__in list params through unchanged."""
        client, endpoint = self._mock_client_core()
        params = {"tag": ["foo", "bar"]}
        _execute_core(client, "dcim", "devices", "GET", params, None, None, 50)
        # tag=[...] stays as a list; filter call does not crash
        call_kwargs = endpoint.filter.call_args
        assert call_kwargs[1]["tag"] == ["foo", "bar"]

    def test_execute_cms_large_interface_in_raises(self):
        """_execute_cms raises when params contains interface__in > 500 items."""
        client = MagicMock()
        mock_endpoint = MagicMock()
        mock_endpoint.filter.return_value = []
        with patch("nautobot_mcp.bridge.get_cms_endpoint", return_value=mock_endpoint):
            params = {"interface__in": [f"iface-{i}" for i in range(501)]}
            with pytest.raises(NautobotValidationError, match="interface__in.*501.*500"):
                _execute_cms(client, "juniper_static_routes", "GET", params, None, None, 50)

    def test_execute_cms_small_in_works(self):
        """_execute_cms works when __in ≤ 500 (converted to string)."""
        client = MagicMock()
        mock_endpoint = MagicMock()
        mock_endpoint.filter.return_value = []
        with patch("nautobot_mcp.bridge.get_cms_endpoint", return_value=mock_endpoint):
            params = {"id__in": ["uuid-1", "uuid-2"]}
            _execute_cms(client, "juniper_static_routes", "GET", params, None, None, 50)
            call_kwargs = mock_endpoint.filter.call_args
            assert call_kwargs[1]["id__in"] == "uuid-1,uuid-2"
