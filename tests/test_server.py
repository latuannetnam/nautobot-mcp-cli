"""Tests for the FastMCP server module."""

from unittest.mock import MagicMock, patch

import pytest
from fastmcp.exceptions import ToolError

from nautobot_mcp.exceptions import NautobotNotFoundError
from nautobot_mcp.models.base import ListResponse
from nautobot_mcp.models.device import DeviceSummary


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client(mock_device_record):
    """Return a mock NautobotClient with device endpoints wired."""
    client = MagicMock()
    client.api.dcim.devices.all.return_value = [mock_device_record]
    client.api.dcim.devices.filter.return_value = [mock_device_record]
    client.api.dcim.devices.get.return_value = mock_device_record
    return client


@pytest.fixture(autouse=True)
def reset_server_client():
    """Reset the server-level _client singleton between tests."""
    import nautobot_mcp.server as srv
    srv._client = None
    yield
    srv._client = None


# ---------------------------------------------------------------------------
# Tool registration tests
# ---------------------------------------------------------------------------


class TestMCPToolRegistration:
    """Verify MCP tool registration metadata."""

    def test_mcp_server_has_tools(self):
        """Server instance should have registered tools."""
        from nautobot_mcp.server import mcp
        # FastMCP stores tools internally — verify we can list them
        assert mcp is not None

    def test_tool_names_have_nautobot_prefix(self):
        """All registered tool names should start with nautobot_."""
        import asyncio
        from nautobot_mcp.server import mcp
        tools = asyncio.run(mcp.list_tools())
        assert len(tools) > 0, "No tools registered"
        for tool in tools:
            assert tool.name.startswith("nautobot_"), f"Tool '{tool.name}' missing nautobot_ prefix"

    def test_expected_tool_count(self):
        """Should have ~28 tools registered."""
        import asyncio
        from nautobot_mcp.server import mcp
        tools = asyncio.run(mcp.list_tools())
        tool_count = len(tools)
        assert tool_count >= 25, f"Expected ≥25 tools, got {tool_count}"


# ---------------------------------------------------------------------------
# Tool output tests
# ---------------------------------------------------------------------------


class TestDeviceTools:
    """Test device tool functions directly."""

    @patch("nautobot_mcp.server.get_client")
    def test_list_devices_tool_returns_dict(self, mock_get_client, mock_client, mock_device_record):
        """list_devices tool should return a dict with count and results."""
        mock_get_client.return_value = mock_client

        from nautobot_mcp.server import nautobot_list_devices
        result = nautobot_list_devices()

        assert isinstance(result, dict)
        assert "count" in result
        assert "results" in result
        assert result["count"] == 1

    @patch("nautobot_mcp.server.get_client")
    def test_get_device_tool_returns_dict(self, mock_get_client, mock_client):
        """get_device tool should return a dict with device fields."""
        mock_get_client.return_value = mock_client

        from nautobot_mcp.server import nautobot_get_device
        result = nautobot_get_device(name="core-rtr-01")

        assert isinstance(result, dict)
        assert result["name"] == "core-rtr-01"

    @patch("nautobot_mcp.server.get_client")
    def test_get_device_tool_not_found_raises_tool_error(self, mock_get_client):
        """Should raise ToolError when device is not found."""
        mock_client = MagicMock()
        mock_client.api.dcim.devices.get.return_value = None
        mock_get_client.return_value = mock_client

        from nautobot_mcp.server import nautobot_get_device

        with pytest.raises(ToolError):
            nautobot_get_device(name="nonexistent")


# ---------------------------------------------------------------------------
# Client factory tests
# ---------------------------------------------------------------------------


class TestClientFactory:
    """Test server client factory."""

    @patch("nautobot_mcp.server.NautobotSettings")
    @patch("nautobot_mcp.server.NautobotClient")
    def test_client_factory_creates_client(self, mock_client_cls, mock_settings_cls):
        """get_client should create and cache a NautobotClient via NautobotSettings.discover()."""
        from nautobot_mcp.server import get_client

        client = get_client()
        mock_settings_cls.discover.assert_called_once()
        mock_client_cls.assert_called_once()
        assert client is not None


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Test error translation."""

    def test_handle_error_nautobot_not_found(self):
        """NautobotNotFoundError should become ToolError with hint."""
        from nautobot_mcp.server import handle_error

        error = NautobotNotFoundError(
            message="Device not found",
            hint="Check device name",
        )
        with pytest.raises(ToolError, match="Device not found.*Hint: Check device name"):
            handle_error(error)

    def test_handle_error_unexpected(self):
        """Non-Nautobot errors should become ToolError with generic message."""
        from nautobot_mcp.server import handle_error

        with pytest.raises(ToolError, match="Unexpected error"):
            handle_error(RuntimeError("something broke"))


# ---------------------------------------------------------------------------
# Plan 05-01: Device-Scoped IP Query Tool tests
# ---------------------------------------------------------------------------


class TestGetDeviceIPs:
    """Test nautobot_get_device_ips MCP tool."""

    @patch("nautobot_mcp.server.get_client")
    def test_get_device_ips_returns_dict(self, mock_get_client):
        """get_device_ips should return dict with interface_ips."""
        mock_client = MagicMock()

        # Mock interface with IP assignment
        mock_iface = MagicMock()
        mock_iface.id = "iface-uuid-1"
        mock_iface.name = "ae0.0"
        mock_client.api.dcim.interfaces.filter.return_value = [mock_iface]

        # Mock M2M record
        mock_m2m = MagicMock()
        mock_m2m.ip_address.id = "ip-uuid-1"
        mock_client.api.ipam.ip_address_to_interface.filter.return_value = [mock_m2m]

        # Mock IP address
        mock_ip = MagicMock()
        mock_ip.id = "ip-uuid-1"
        mock_ip.address = "10.0.0.1/30"
        mock_ip.status.display = "Active"
        mock_client.api.ipam.ip_addresses.get.return_value = mock_ip

        mock_get_client.return_value = mock_client

        from nautobot_mcp.server import nautobot_get_device_ips
        result = nautobot_get_device_ips(device_name="test-device")

        assert isinstance(result, dict)
        assert result["device_name"] == "test-device"
        assert result["total_ips"] == 1
        assert len(result["interface_ips"]) == 1
        assert result["interface_ips"][0]["interface_name"] == "ae0.0"
        assert result["interface_ips"][0]["address"] == "10.0.0.1/30"

    @patch("nautobot_mcp.server.get_client")
    def test_get_device_ips_no_interfaces(self, mock_get_client):
        """get_device_ips returns empty when device has no interfaces."""
        mock_client = MagicMock()
        mock_client.api.dcim.interfaces.filter.return_value = []
        mock_get_client.return_value = mock_client

        from nautobot_mcp.server import nautobot_get_device_ips
        result = nautobot_get_device_ips(device_name="empty-device")

        assert result["total_ips"] == 0
        assert result["interface_ips"] == []

    @patch("nautobot_mcp.server.get_client")
    def test_get_device_ips_tool_registered(self, mock_get_client):
        """nautobot_get_device_ips should be registered as an MCP tool."""
        import asyncio
        from nautobot_mcp.server import mcp
        tools = asyncio.run(mcp.list_tools())
        names = [t.name for t in tools]
        assert "nautobot_get_device_ips" in names, f"Tool not found. Tools: {names}"


# ---------------------------------------------------------------------------
# Plan 05-02: Cross-Entity Device Filters tests
# ---------------------------------------------------------------------------


class TestVLANDeviceFilter:
    """Test nautobot_list_vlans with device filter."""

    @patch("nautobot_mcp.server.get_client")
    def test_list_vlans_with_device_filter(self, mock_get_client):
        """list_vlans with device_name uses interface-based VLAN lookup."""
        mock_client = MagicMock()

        # Mock interface with untagged VLAN
        mock_iface = MagicMock()
        mock_iface.id = "iface-uuid-1"
        mock_iface.untagged_vlan = MagicMock()
        mock_iface.untagged_vlan.id = "vlan-uuid-1"
        mock_iface.tagged_vlans = []
        mock_client.api.dcim.interfaces.filter.return_value = [mock_iface]

        # Mock VLAN record
        mock_vlan = MagicMock()
        mock_vlan.id = "vlan-uuid-1"
        mock_vlan.vid = 100
        mock_vlan.name = "MGMT"
        mock_vlan.status.display = "Active"
        mock_vlan.location = None
        mock_vlan.tenant = None
        mock_vlan.vlan_group = None
        mock_client.api.ipam.vlans.get.return_value = mock_vlan

        mock_get_client.return_value = mock_client

        from nautobot_mcp.server import nautobot_list_vlans
        result = nautobot_list_vlans(device_name="test-device")

        assert isinstance(result, dict)
        assert result["count"] == 1
        mock_client.api.dcim.interfaces.filter.assert_called_once_with(device="test-device")

    @patch("nautobot_mcp.server.get_client")
    def test_list_vlans_no_device_filter(self, mock_get_client):
        """list_vlans without device_name uses standard filter path."""
        mock_client = MagicMock()
        mock_client.api.ipam.vlans.all.return_value = []
        mock_get_client.return_value = mock_client

        from nautobot_mcp.server import nautobot_list_vlans
        result = nautobot_list_vlans()

        assert isinstance(result, dict)
        assert result["count"] == 0
        # Should NOT call dcim.interfaces.filter when no device filter
        mock_client.api.dcim.interfaces.filter.assert_not_called()


# ---------------------------------------------------------------------------
# Plan 06-01: Device Summary Composite Tool tests
# ---------------------------------------------------------------------------


class TestDeviceSummary:
    """Test nautobot_device_summary MCP tool."""

    @patch("nautobot_mcp.server.get_client")
    def test_device_summary_returns_dict(self, mock_get_client):
        """device_summary returns aggregated dict with counts."""
        mock_client = MagicMock()

        # Mock device
        mock_device = MagicMock()
        mock_device.id = "dev-uuid"
        mock_device.name = "test-device"
        mock_device.status.display = "Active"
        mock_device.device_type = MagicMock(id="dt-1", name="MX204", display="MX204")
        mock_device.location = MagicMock(id="loc-1", name="DC1", display="DC1")
        mock_device.tenant = None
        mock_device.role = None
        mock_device.platform = None
        mock_device.serial = None
        mock_device.primary_ip = None
        mock_client.api.dcim.devices.get.return_value = mock_device

        # Mock interfaces
        mock_iface = MagicMock()
        mock_iface.id = "iface-uuid-1"
        mock_iface.name = "ae0.0"
        mock_iface.type.display = "Virtual"
        mock_iface.device = MagicMock(id="dev-uuid", name="test-device", display="test-device")
        mock_iface.enabled = True
        mock_iface.description = None
        mock_iface.mac_address = None
        mock_iface.mtu = None
        mock_iface.ip_addresses = []
        mock_client.api.dcim.interfaces.filter.return_value = [mock_iface]

        # Mock M2M (no IPs)
        mock_client.api.ipam.ip_address_to_interface.filter.return_value = []

        # Mock VLANs (none via interface)
        mock_iface.untagged_vlan = None
        mock_iface.tagged_vlans = []

        mock_get_client.return_value = mock_client

        from nautobot_mcp.server import nautobot_device_summary
        result = nautobot_device_summary(device_name="test-device")

        assert isinstance(result, dict)
        assert result["device"]["name"] == "test-device"
        assert result["interface_count"] == 1
        assert result["ip_count"] == 0
        assert result["vlan_count"] == 0
        assert result["enabled_count"] == 1
        assert result["disabled_count"] == 0

    @patch("nautobot_mcp.server.get_client")
    def test_device_summary_tool_registered(self, mock_get_client):
        """nautobot_device_summary should be registered as an MCP tool."""
        import asyncio
        from nautobot_mcp.server import mcp
        tools = asyncio.run(mcp.list_tools())
        names = [t.name for t in tools]
        assert "nautobot_device_summary" in names


# ---------------------------------------------------------------------------
# Plan 06-02: Enriched Interface Data tests
# ---------------------------------------------------------------------------


class TestInterfaceIPEnrichment:
    """Test nautobot_list_interfaces with include_ips=True."""

    @patch("nautobot_mcp.server.get_client")
    def test_list_interfaces_with_ips(self, mock_get_client):
        """list_interfaces with include_ips=True populates ip_addresses."""
        mock_client = MagicMock()

        # Mock interface
        mock_iface = MagicMock()
        mock_iface.id = "iface-uuid-1"
        mock_iface.name = "ae0.0"
        mock_iface.type.display = "Virtual"
        mock_iface.device = MagicMock(id="dev-1", name="test-dev", display="test-dev")
        mock_iface.enabled = True
        mock_iface.description = None
        mock_iface.mac_address = None
        mock_iface.mtu = None
        mock_iface.ip_addresses = []
        mock_client.api.dcim.interfaces.filter.return_value = [mock_iface]

        # Mock M2M
        mock_m2m = MagicMock()
        mock_m2m.ip_address.id = "ip-uuid-1"
        mock_client.api.ipam.ip_address_to_interface.filter.return_value = [mock_m2m]

        # Mock IP
        mock_ip = MagicMock()
        mock_ip.id = "ip-uuid-1"
        mock_ip.address = "10.0.0.1/30"
        mock_ip.status.display = "Active"
        mock_client.api.ipam.ip_addresses.get.return_value = mock_ip

        mock_get_client.return_value = mock_client

        from nautobot_mcp.server import nautobot_list_interfaces
        result = nautobot_list_interfaces(device="test-dev", include_ips=True)

        assert isinstance(result, dict)
        assert result["count"] == 1
        iface = result["results"][0]
        assert len(iface["ip_addresses"]) == 1
        assert iface["ip_addresses"][0]["address"] == "10.0.0.1/30"

    @patch("nautobot_mcp.server.get_client")
    def test_list_interfaces_without_ips(self, mock_get_client):
        """list_interfaces without include_ips leaves ip_addresses as-is."""
        mock_client = MagicMock()
        mock_iface = MagicMock()
        mock_iface.id = "iface-uuid-1"
        mock_iface.name = "ge-0/0/0"
        mock_iface.type.display = "1000base-t"
        mock_iface.device = MagicMock(id="dev-1", name="test-dev", display="test-dev")
        mock_iface.enabled = True
        mock_iface.description = None
        mock_iface.mac_address = None
        mock_iface.mtu = None
        mock_iface.ip_addresses = []
        mock_client.api.dcim.interfaces.filter.return_value = [mock_iface]
        mock_get_client.return_value = mock_client

        from nautobot_mcp.server import nautobot_list_interfaces
        result = nautobot_list_interfaces(device="test-dev", include_ips=False)

        assert result["results"][0]["ip_addresses"] == []
        # Should NOT call M2M endpoint
        mock_client.api.ipam.ip_address_to_interface.filter.assert_not_called()


class TestCompareDevice:
    """Test nautobot_compare_device MCP tool."""

    @patch("nautobot_mcp.server.get_client")
    @patch("nautobot_mcp.drift.get_device_ips")
    @patch("nautobot_mcp.drift.list_interfaces")
    def test_compare_device_returns_dict(
        self, mock_list_ifaces, mock_get_ips, mock_get_client,
    ):
        """compare_device returns QuickDriftReport dict."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock Nautobot side: one interface with one IP
        ip_entry = MagicMock()
        ip_entry.interface_name = "ae0.0"
        ip_entry.address = "10.1.1.1/30"
        mock_get_ips.return_value = MagicMock(interface_ips=[ip_entry])

        iface_record = MagicMock()
        iface_record.name = "ae0.0"
        iface_record.untagged_vlan = None
        iface_record.tagged_vlans = []
        mock_list_ifaces.return_value = MagicMock(results=[iface_record])

        from nautobot_mcp.server import nautobot_compare_device
        result = nautobot_compare_device(
            device_name="test-device",
            interfaces_data={"ae0.0": {"ips": ["10.1.1.1/30"]}},
        )

        assert isinstance(result, dict)
        assert result["device"] == "test-device"
        assert result["summary"]["total_drifts"] == 0

    def test_compare_device_tool_registered(self):
        """nautobot_compare_device should be registered as an MCP tool."""
        import asyncio
        from nautobot_mcp.server import mcp
        tools = asyncio.run(mcp.list_tools())
        names = [t.name for t in tools]
        assert "nautobot_compare_device" in names
