"""Tests for the 3-tool Nautobot API Bridge MCP Server.

Validates:
- 3 expected tools registered (nautobot_api_catalog, nautobot_call_nautobot, nautobot_run_workflow)
- All tool names have nautobot_ prefix
- get_client() singleton pattern
- handle_error() translates NautobotMCPError -> ToolError
- Each tool function delegates to the correct underlying module
- Error propagation via handle_error for each tool
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastmcp.exceptions import ToolError

from nautobot_mcp.exceptions import NautobotNotFoundError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_server_client():
    """Reset the server-level _client singleton between tests."""
    import nautobot_mcp.server as srv
    srv._client = None
    yield
    srv._client = None


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


class TestMCPToolRegistration:
    """Verify the 3-tool MCP interface is properly registered."""

    def test_mcp_server_exists(self):
        """Server FastMCP instance should be accessible."""
        from nautobot_mcp.server import mcp
        assert mcp is not None

    def test_exactly_three_tools_registered(self):
        """Server should expose exactly 3 tools."""
        import asyncio
        from nautobot_mcp.server import mcp
        tools = asyncio.run(mcp.list_tools())
        assert len(tools) == 3, (
            f"Expected 3 tools, got {len(tools)}: {[t.name for t in tools]}"
        )

    def test_all_tool_names_have_nautobot_prefix(self):
        """All tool names must start with nautobot_."""
        import asyncio
        from nautobot_mcp.server import mcp
        tools = asyncio.run(mcp.list_tools())
        for tool in tools:
            assert tool.name.startswith("nautobot_"), (
                f"Tool '{tool.name}' missing nautobot_ prefix"
            )

    def test_api_catalog_tool_registered(self):
        """nautobot_api_catalog must be registered."""
        import asyncio
        from nautobot_mcp.server import mcp
        tools = asyncio.run(mcp.list_tools())
        names = [t.name for t in tools]
        assert "nautobot_api_catalog" in names, f"Not found. Tools: {names}"

    def test_call_nautobot_tool_registered(self):
        """nautobot_call_nautobot must be registered."""
        import asyncio
        from nautobot_mcp.server import mcp
        tools = asyncio.run(mcp.list_tools())
        names = [t.name for t in tools]
        assert "nautobot_call_nautobot" in names, f"Not found. Tools: {names}"

    def test_run_workflow_tool_registered(self):
        """nautobot_run_workflow must be registered."""
        import asyncio
        from nautobot_mcp.server import mcp
        tools = asyncio.run(mcp.list_tools())
        names = [t.name for t in tools]
        assert "nautobot_run_workflow" in names, f"Not found. Tools: {names}"


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------


class TestClientFactory:
    """Test server client factory singleton behavior."""

    @patch("nautobot_mcp.server.NautobotSettings")
    @patch("nautobot_mcp.server.NautobotClient")
    def test_client_factory_creates_client(self, mock_client_cls, mock_settings_cls):
        """get_client should create and return a NautobotClient via NautobotSettings.discover()."""
        from nautobot_mcp.server import get_client
        client = get_client()
        mock_settings_cls.discover.assert_called_once()
        mock_client_cls.assert_called_once()
        assert client is not None

    @patch("nautobot_mcp.server.NautobotSettings")
    @patch("nautobot_mcp.server.NautobotClient")
    def test_client_factory_is_singleton(self, mock_client_cls, mock_settings_cls):
        """Successive calls to get_client() should return the same instance."""
        from nautobot_mcp.server import get_client
        c1 = get_client()
        c2 = get_client()
        assert c1 is c2
        assert mock_client_cls.call_count == 1


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Test error translation in handle_error()."""

    def test_handle_error_nautobot_not_found_with_hint(self):
        """NautobotNotFoundError with hint should include hint in ToolError."""
        from nautobot_mcp.server import handle_error
        error = NautobotNotFoundError(
            message="Device not found",
            hint="Check device name spelling",
        )
        with pytest.raises(ToolError, match="Device not found.*Hint: Check device name spelling"):
            handle_error(error)

    def test_handle_error_nautobot_not_found_without_hint(self):
        """NautobotNotFoundError without hint should produce clean ToolError."""
        from nautobot_mcp.server import handle_error
        error = NautobotNotFoundError(message="Not found")
        with pytest.raises(ToolError, match="Not found"):
            handle_error(error)

    def test_handle_error_unexpected_exception(self):
        """Non-NautobotMCPError should become ToolError with 'Unexpected error'."""
        from nautobot_mcp.server import handle_error
        with pytest.raises(ToolError, match="Unexpected error"):
            handle_error(RuntimeError("something broke"))


# ---------------------------------------------------------------------------
# nautobot_api_catalog tool
# ---------------------------------------------------------------------------


class TestApiCatalogTool:
    """Test nautobot_api_catalog tool function."""

    @patch("nautobot_mcp.server.get_client")
    @patch("nautobot_mcp.server.get_catalog")
    def test_catalog_tool_returns_dict(self, mock_get_catalog, mock_get_client):
        """nautobot_api_catalog should return the catalog as a dict."""
        mock_catalogue = MagicMock()
        mock_catalogue.model_dump.return_value = {
            "endpoints": [],
            "workflows": {},
            "summary": {},
        }
        mock_get_catalog.return_value = mock_catalogue
        mock_get_client.return_value = MagicMock()

        from nautobot_mcp.server import nautobot_api_catalog
        result = nautobot_api_catalog()

        assert isinstance(result, dict)
        assert "endpoints" in result
        assert "workflows" in result

    @patch("nautobot_mcp.server.get_client")
    @patch("nautobot_mcp.server.get_catalog")
    def test_catalog_tool_passes_domain_filter(self, mock_get_catalog, mock_get_client):
        """nautobot_api_catalog should pass domain filter to get_catalog."""
        mock_get_catalog.return_value = MagicMock(model_dump=lambda: {"endpoints": [], "workflows": {}, "summary": {}})
        mock_get_client.return_value = MagicMock()

        from nautobot_mcp.server import nautobot_api_catalog
        nautobot_api_catalog(domain="dcim")

        mock_get_catalog.assert_called_once()
        call_kwargs = mock_get_catalog.call_args
        assert call_kwargs.kwargs.get("domain") == "dcim" or call_kwargs.args[1] == "dcim"

    @patch("nautobot_mcp.server.get_client")
    @patch("nautobot_mcp.server.get_catalog")
    def test_catalog_tool_error_raises_tool_error(self, mock_get_catalog, mock_get_client):
        """catalog tool should raise ToolError on unexpected exceptions."""
        mock_get_client.return_value = MagicMock()
        mock_get_catalog.side_effect = RuntimeError("catalog failure")

        from nautobot_mcp.server import nautobot_api_catalog
        with pytest.raises(ToolError, match="Unexpected error"):
            nautobot_api_catalog()


# ---------------------------------------------------------------------------
# nautobot_call_nautobot tool
# ---------------------------------------------------------------------------


class TestCallNautobotTool:
    """Test nautobot_call_nautobot tool function."""

    @patch("nautobot_mcp.server.get_client")
    @patch("nautobot_mcp.server.call_nautobot")
    def test_call_nautobot_get_returns_dict(self, mock_bridge, mock_get_client):
        """call_nautobot tool should return bridge result dict for GET."""
        mock_get_client.return_value = MagicMock()
        mock_bridge.return_value = {
            "status": "ok",
            "method": "GET",
            "endpoint": "/api/dcim/devices/",
            "data": [{"id": "uuid-1", "name": "rtr-01"}],
            "count": 1,
        }

        from nautobot_mcp.server import nautobot_call_nautobot
        result = nautobot_call_nautobot(
            method="GET",
            endpoint="/api/dcim/devices/",
            params={"limit": 10},
        )

        assert isinstance(result, dict)
        assert result["status"] == "ok"
        assert result["method"] == "GET"
        mock_bridge.assert_called_once()

    @patch("nautobot_mcp.server.get_client")
    @patch("nautobot_mcp.server.call_nautobot")
    def test_call_nautobot_post_passes_body(self, mock_bridge, mock_get_client):
        """call_nautobot tool should pass body to bridge for POST."""
        mock_get_client.return_value = MagicMock()
        mock_bridge.return_value = {"status": "ok", "data": {"id": "new-uuid"}}

        from nautobot_mcp.server import nautobot_call_nautobot
        body = {"name": "test-rtr", "device_type": "MX204"}
        nautobot_call_nautobot(method="POST", endpoint="/api/dcim/devices/", body=body)

        call_kwargs = mock_bridge.call_args.kwargs
        assert call_kwargs.get("body") == body or mock_bridge.call_args.args[3] == body

    @patch("nautobot_mcp.server.get_client")
    @patch("nautobot_mcp.server.call_nautobot")
    def test_call_nautobot_error_raises_tool_error(self, mock_bridge, mock_get_client):
        """call_nautobot tool should raise ToolError on exceptions."""
        mock_get_client.return_value = MagicMock()
        mock_bridge.side_effect = RuntimeError("connection error")

        from nautobot_mcp.server import nautobot_call_nautobot
        with pytest.raises(ToolError, match="Unexpected error"):
            nautobot_call_nautobot(method="GET", endpoint="/api/dcim/devices/")


# ---------------------------------------------------------------------------
# nautobot_run_workflow tool
# ---------------------------------------------------------------------------


class TestRunWorkflowTool:
    """Test nautobot_run_workflow tool function."""

    @patch("nautobot_mcp.server.get_client")
    @patch("nautobot_mcp.server.run_workflow")
    def test_run_workflow_returns_envelope(self, mock_run, mock_get_client):
        """run_workflow tool should return the envelope from run_workflow()."""
        mock_get_client.return_value = MagicMock()
        mock_run.return_value = {
            "workflow": "bgp_summary",
            "device": "core-rtr-01",
            "status": "ok",
            "data": {"groups": [], "neighbors": []},
            "error": None,
            "timestamp": "2026-03-24T13:00:00Z",
        }

        from nautobot_mcp.server import nautobot_run_workflow
        result = nautobot_run_workflow(
            workflow_id="bgp_summary",
            params={"device": "core-rtr-01"},
        )

        assert result["status"] == "ok"
        assert result["workflow"] == "bgp_summary"
        mock_run.assert_called_once()

    @patch("nautobot_mcp.server.get_client")
    @patch("nautobot_mcp.server.run_workflow")
    def test_run_workflow_passes_correct_args(self, mock_run, mock_get_client):
        """run_workflow tool should pass client, workflow_id, and params."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_run.return_value = {"status": "ok", "data": {}}

        from nautobot_mcp.server import nautobot_run_workflow
        nautobot_run_workflow(
            workflow_id="compare_device",
            params={"device_name": "rtr-01", "live_data": {}},
        )

        mock_run.assert_called_once_with(
            mock_client,
            workflow_id="compare_device",
            params={"device_name": "rtr-01", "live_data": {}},
        )

    @patch("nautobot_mcp.server.get_client")
    @patch("nautobot_mcp.server.run_workflow")
    def test_run_workflow_error_raises_tool_error(self, mock_run, mock_get_client):
        """run_workflow tool should raise ToolError on exceptions not handled by workflow."""
        mock_get_client.return_value = MagicMock()
        mock_run.side_effect = RuntimeError("dispatch failed")

        from nautobot_mcp.server import nautobot_run_workflow
        with pytest.raises(ToolError, match="Unexpected error"):
            nautobot_run_workflow(workflow_id="bad_wf", params={})
