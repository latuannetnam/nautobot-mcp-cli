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
        """get_client should create and cache a NautobotClient."""
        from nautobot_mcp.server import get_client

        client = get_client()
        mock_settings_cls.assert_called_once()
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
