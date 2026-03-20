"""Tests for CMS plugin client foundation.

Covers:
- NautobotClient.cms property
- resolve_device_id helper
- CMS endpoint registry
- Generic CRUD helpers (cms_list, cms_get, cms_create, cms_update, cms_delete)
- Error handling paths
"""

from unittest.mock import MagicMock, patch

import pytest

from nautobot_mcp.client import NautobotClient
from nautobot_mcp.cms.client import (
    CMS_ENDPOINTS,
    cms_create,
    cms_delete,
    cms_get,
    cms_list,
    cms_update,
    get_cms_endpoint,
    resolve_device_id,
)
from nautobot_mcp.exceptions import NautobotAPIError, NautobotNotFoundError
from nautobot_mcp.models.cms.base import CMSBaseSummary


# ---------------------------------------------------------------------------
# CMS Property Tests
# ---------------------------------------------------------------------------


class TestCMSProperty:
    """Tests for NautobotClient.cms property."""

    def test_cms_property_returns_plugin_accessor(self, mock_client_with_cms, mock_cms_plugin):
        """cms property returns the netnam_cms_core plugin accessor."""
        result = mock_client_with_cms.cms
        assert result is mock_cms_plugin

    def test_cms_property_raises_on_missing_plugin(self, mock_nautobot_profile):
        """cms property raises NautobotAPIError if plugin not installed."""
        from unittest.mock import PropertyMock

        client = NautobotClient(profile=mock_nautobot_profile)
        mock_api = MagicMock()
        # Make accessing netnam_cms_core attribute raise AttributeError
        mock_plugins = MagicMock(spec=[])  # spec=[] means no attributes allowed
        mock_api.plugins = mock_plugins
        client._api = mock_api
        with pytest.raises(NautobotAPIError, match="NetNam CMS Core plugin not available"):
            _ = client.cms



# ---------------------------------------------------------------------------
# Endpoint Registry Tests
# ---------------------------------------------------------------------------


class TestCMSEndpoints:
    """Tests for CMS endpoint registry."""

    def test_endpoint_count(self):
        """Registry contains all expected CMS endpoints."""
        # At least 38 endpoints from netnam-cms-core urls.py
        assert len(CMS_ENDPOINTS) >= 38

    def test_routing_endpoints_present(self):
        """Registry includes routing domain endpoints."""
        assert "juniper_static_routes" in CMS_ENDPOINTS
        assert "juniper_bgp_groups" in CMS_ENDPOINTS
        assert "juniper_bgp_neighbors" in CMS_ENDPOINTS

    def test_interface_endpoints_present(self):
        """Registry includes interface domain endpoints."""
        assert "juniper_interface_units" in CMS_ENDPOINTS
        assert "juniper_interface_families" in CMS_ENDPOINTS
        assert "juniper_interface_vrrp_groups" in CMS_ENDPOINTS

    def test_firewall_endpoints_present(self):
        """Registry includes firewall domain endpoints."""
        assert "juniper_firewall_filters" in CMS_ENDPOINTS
        assert "juniper_firewall_terms" in CMS_ENDPOINTS
        assert "juniper_firewall_policers" in CMS_ENDPOINTS

    def test_policy_endpoints_present(self):
        """Registry includes policy domain endpoints."""
        assert "juniper_policy_statements" in CMS_ENDPOINTS
        assert "jps_terms" in CMS_ENDPOINTS
        assert "jps_actions" in CMS_ENDPOINTS

    def test_arp_endpoints_present(self):
        """Registry includes ARP domain endpoints."""
        assert "juniper_arp_entries" in CMS_ENDPOINTS

    def test_get_cms_endpoint_valid(self, mock_client_with_cms):
        """get_cms_endpoint returns accessor for valid endpoint names."""
        endpoint = get_cms_endpoint(mock_client_with_cms, "juniper_static_routes")
        assert endpoint is not None

    def test_get_cms_endpoint_invalid(self, mock_client_with_cms):
        """get_cms_endpoint raises ValueError for unknown endpoint names."""
        with pytest.raises(ValueError, match="Unknown CMS endpoint"):
            get_cms_endpoint(mock_client_with_cms, "nonexistent_endpoint")


# ---------------------------------------------------------------------------
# Device Resolution Tests
# ---------------------------------------------------------------------------


class TestResolveDeviceId:
    """Tests for resolve_device_id helper."""

    def test_uuid_passthrough(self, mock_client_with_cms):
        """UUID-formatted strings are returned as-is without API call."""
        uuid = "12345678-1234-1234-1234-123456789012"
        result = resolve_device_id(mock_client_with_cms, uuid)
        assert result == uuid
        # Should not have called the API
        mock_client_with_cms.api.dcim.devices.get.assert_not_called()

    def test_name_resolution(self, mock_client_with_cms):
        """Device names are resolved to UUIDs via API lookup."""
        mock_device = MagicMock()
        mock_device.id = "resolved-uuid-1234-5678-abcdefgh"
        mock_client_with_cms.api.dcim.devices.get.return_value = mock_device

        result = resolve_device_id(mock_client_with_cms, "core-rtr-01")
        assert result == "resolved-uuid-1234-5678-abcdefgh"
        mock_client_with_cms.api.dcim.devices.get.assert_called_once_with(name="core-rtr-01")

    def test_name_not_found(self, mock_client_with_cms):
        """Raises NautobotNotFoundError when device name doesn't exist."""
        mock_client_with_cms.api.dcim.devices.get.return_value = None

        with pytest.raises(NautobotNotFoundError, match="not found"):
            resolve_device_id(mock_client_with_cms, "nonexistent-device")


# ---------------------------------------------------------------------------
# Generic CRUD Helper Tests
# ---------------------------------------------------------------------------


class TestCMSList:
    """Tests for cms_list helper."""

    def test_list_all(self, mock_client_with_cms, mock_cms_record):
        """cms_list returns all records when no filters."""
        mock_client_with_cms.cms.juniper_static_routes.all.return_value = [mock_cms_record]

        result = cms_list(
            mock_client_with_cms, "juniper_static_routes", CMSBaseSummary
        )
        assert result.count == 1
        assert len(result.results) == 1

    def test_list_with_filters(self, mock_client_with_cms, mock_cms_record):
        """cms_list passes filters to pynautobot."""
        mock_client_with_cms.cms.juniper_static_routes.filter.return_value = [mock_cms_record]

        result = cms_list(
            mock_client_with_cms, "juniper_static_routes", CMSBaseSummary,
            device="core-rtr-01",
        )
        assert result.count == 1
        mock_client_with_cms.cms.juniper_static_routes.filter.assert_called_once_with(
            device="core-rtr-01"
        )

    def test_list_with_limit(self, mock_client_with_cms, mock_cms_record):
        """cms_list respects limit parameter."""
        record2 = MagicMock()
        record2.id = "cms-2222-3333-4444-5555"
        record2.display = "r2"
        record2.url = None
        record2.device = None
        records = [mock_cms_record, record2]
        mock_client_with_cms.cms.juniper_static_routes.all.return_value = records

        result = cms_list(
            mock_client_with_cms, "juniper_static_routes", CMSBaseSummary, limit=1
        )
        assert result.count == 2  # total count is unlimited
        assert len(result.results) == 1  # but only 1 returned


class TestCMSGet:
    """Tests for cms_get helper."""

    def test_get_by_id(self, mock_client_with_cms, mock_cms_record):
        """cms_get retrieves by UUID."""
        mock_client_with_cms.cms.juniper_static_routes.get.return_value = mock_cms_record

        result = cms_get(
            mock_client_with_cms, "juniper_static_routes", CMSBaseSummary,
            id="cms-1111-2222-3333-4444",
        )
        assert result.id == "cms-1111-2222-3333-4444"

    def test_get_not_found(self, mock_client_with_cms):
        """cms_get raises NautobotNotFoundError when record is None."""
        mock_client_with_cms.cms.juniper_static_routes.get.return_value = None

        with pytest.raises(NautobotNotFoundError, match="not found"):
            cms_get(
                mock_client_with_cms, "juniper_static_routes", CMSBaseSummary,
                id="nonexistent",
            )


class TestCMSCreate:
    """Tests for cms_create helper."""

    def test_create_success(self, mock_client_with_cms, mock_cms_record):
        """cms_create creates and returns model instance."""
        mock_client_with_cms.cms.juniper_static_routes.create.return_value = mock_cms_record

        result = cms_create(
            mock_client_with_cms, "juniper_static_routes", CMSBaseSummary,
            prefix="10.0.0.0/24", device="aaaa-bbbb-cccc-dddd",
        )
        assert result.id == "cms-1111-2222-3333-4444"
        mock_client_with_cms.cms.juniper_static_routes.create.assert_called_once_with(
            prefix="10.0.0.0/24", device="aaaa-bbbb-cccc-dddd",
        )


class TestCMSUpdate:
    """Tests for cms_update helper."""

    def test_update_success(self, mock_client_with_cms, mock_cms_record):
        """cms_update sets attributes and saves."""
        mock_client_with_cms.cms.juniper_static_routes.get.return_value = mock_cms_record

        result = cms_update(
            mock_client_with_cms, "juniper_static_routes", CMSBaseSummary,
            id="cms-1111-2222-3333-4444", description="updated",
        )
        mock_cms_record.save.assert_called_once()

    def test_update_not_found(self, mock_client_with_cms):
        """cms_update raises NautobotNotFoundError for unknown ID."""
        mock_client_with_cms.cms.juniper_static_routes.get.return_value = None

        with pytest.raises(NautobotNotFoundError, match="not found"):
            cms_update(
                mock_client_with_cms, "juniper_static_routes", CMSBaseSummary,
                id="nonexistent",
            )


class TestCMSDelete:
    """Tests for cms_delete helper."""

    def test_delete_success(self, mock_client_with_cms, mock_cms_record):
        """cms_delete removes record and returns success dict."""
        mock_client_with_cms.cms.juniper_static_routes.get.return_value = mock_cms_record

        result = cms_delete(mock_client_with_cms, "juniper_static_routes", "cms-1111-2222-3333-4444")
        assert result["success"] is True
        mock_cms_record.delete.assert_called_once()

    def test_delete_not_found(self, mock_client_with_cms):
        """cms_delete raises NautobotNotFoundError for unknown ID."""
        mock_client_with_cms.cms.juniper_static_routes.get.return_value = None

        with pytest.raises(NautobotNotFoundError, match="not found"):
            cms_delete(mock_client_with_cms, "juniper_static_routes", "nonexistent")


# ---------------------------------------------------------------------------
# Base Model Tests
# ---------------------------------------------------------------------------


class TestCMSBaseSummary:
    """Tests for CMSBaseSummary base model."""

    def test_extract_device_from_record(self, mock_cms_record):
        """_extract_device gets device info from a pynautobot record."""
        dev_id, dev_name = CMSBaseSummary._extract_device(mock_cms_record)
        assert dev_id == "aaaa-bbbb-cccc-dddd"
        assert dev_name == "core-rtr-01"

    def test_extract_device_none(self):
        """_extract_device returns None, None for records without device."""
        record = MagicMock(spec=[])  # spec=[] means no attributes
        dev_id, dev_name = CMSBaseSummary._extract_device(record)
        assert dev_id is None
        assert dev_name is None

    def test_from_nautobot_creates_instance(self, mock_cms_record):
        """CMSBaseSummary can be constructed with basic fields."""
        # Base class should work with basic fields
        model = CMSBaseSummary(
            id=str(mock_cms_record.id),
            display=str(mock_cms_record.display),
            device_id="aaaa-bbbb-cccc-dddd",
            device_name="core-rtr-01",
        )
        assert model.id == "cms-1111-2222-3333-4444"
        assert model.device_name == "core-rtr-01"
