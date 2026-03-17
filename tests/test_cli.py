"""Tests for the CLI application and formatters."""

import json
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from nautobot_mcp.cli.formatters import (
    DEVICE_COLUMNS,
    format_json,
    format_table,
    output,
)
from nautobot_mcp.exceptions import NautobotConnectionError, NautobotNotFoundError
from nautobot_mcp.models.base import ListResponse

runner = CliRunner()


# ---------------------------------------------------------------------------
# Formatter tests
# ---------------------------------------------------------------------------


class TestFormatters:
    """Test output formatting functions."""

    def test_format_table_produces_simple_table(self):
        """format_table should return a tabulate 'simple' format string."""
        data = [
            {"name": "core-rtr-01", "status": "Active"},
            {"name": "core-sw-01", "status": "Planned"},
        ]
        result = format_table(data, ["name", "status"])
        assert "core-rtr-01" in result
        assert "core-sw-01" in result
        assert "name" in result  # header present
        assert "status" in result  # header present

    def test_format_table_handles_missing_keys(self):
        """Missing keys should show empty string."""
        data = [{"name": "test-device"}]
        result = format_table(data, ["name", "status"])
        assert "test-device" in result

    def test_format_json_produces_valid_json(self):
        """format_json should produce valid JSON."""
        data = {"count": 1, "results": [{"name": "test"}]}
        result = format_json(data)
        parsed = json.loads(result)
        assert parsed["count"] == 1

    def test_format_json_handles_non_serializable(self):
        """format_json should use default=str for non-serializable types."""
        from datetime import datetime
        data = {"timestamp": datetime(2026, 1, 1)}
        result = format_json(data)
        parsed = json.loads(result)
        assert "2026" in parsed["timestamp"]

    def test_output_json_mode(self, capsys):
        """output in JSON mode should print JSON."""
        data = {"count": 1, "results": [{"name": "test", "status": "Active"}]}
        output(data, json_mode=True, columns=["name", "status"])
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["count"] == 1

    def test_output_table_mode(self, capsys):
        """output in table mode should print formatted table."""
        data = {"count": 1, "results": [{"name": "core-rtr-01", "status": "Active"}]}
        output(data, json_mode=False, columns=["name", "status"])
        captured = capsys.readouterr()
        assert "core-rtr-01" in captured.out

    def test_output_empty_results(self, capsys):
        """output with empty results should print 'No results found.'"""
        data = {"count": 0, "results": []}
        output(data, json_mode=False, columns=["name"])
        captured = capsys.readouterr()
        assert "No results found" in captured.out


# ---------------------------------------------------------------------------
# CLI structure tests
# ---------------------------------------------------------------------------


class TestCLIStructure:
    """Test CLI app structure and help text."""

    def test_devices_list_help(self):
        """'devices list --help' should show usage info."""
        from nautobot_mcp.cli.app import app
        result = runner.invoke(app, ["devices", "list", "--help"])
        assert result.exit_code == 0
        assert "List devices" in result.output

    def test_interfaces_list_help(self):
        """'interfaces list --help' should show usage info."""
        from nautobot_mcp.cli.app import app
        result = runner.invoke(app, ["interfaces", "list", "--help"])
        assert result.exit_code == 0
        assert "List interfaces" in result.output

    def test_ipam_prefixes_list_help(self):
        """'ipam prefixes list --help' should show nested subcommand."""
        from nautobot_mcp.cli.app import app
        result = runner.invoke(app, ["ipam", "prefixes", "list", "--help"])
        assert result.exit_code == 0
        assert "List IP prefixes" in result.output

    def test_org_tenants_list_help(self):
        """'org tenants list --help' should work."""
        from nautobot_mcp.cli.app import app
        result = runner.invoke(app, ["org", "tenants", "list", "--help"])
        assert result.exit_code == 0

    def test_circuits_list_help(self):
        """'circuits list --help' should work."""
        from nautobot_mcp.cli.app import app
        result = runner.invoke(app, ["circuits", "list", "--help"])
        assert result.exit_code == 0

    def test_root_help_shows_all_groups(self):
        """Root --help should show all command groups."""
        from nautobot_mcp.cli.app import app
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        for group in ["devices", "interfaces", "ipam", "org", "circuits"]:
            assert group in result.output, f"Missing group: {group}"


# ---------------------------------------------------------------------------
# CLI JSON output test
# ---------------------------------------------------------------------------


class TestCLIOutput:
    """Test CLI command output formatting."""

    @patch("nautobot_mcp.cli.devices.get_client_from_ctx")
    @patch("nautobot_mcp.cli.devices.devices")
    def test_devices_list_json_output(self, mock_devices_mod, mock_get_client):
        """--json flag should produce valid JSON output."""
        mock_devices_mod.list_devices.return_value = MagicMock(
            model_dump=MagicMock(return_value={
                "count": 1,
                "results": [{"name": "core-rtr-01", "status": "Active"}],
            })
        )

        from nautobot_mcp.cli.app import app
        result = runner.invoke(app, ["--json", "devices", "list"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["count"] == 1
        assert len(parsed["results"]) == 1


# ---------------------------------------------------------------------------
# CLI exit code tests
# ---------------------------------------------------------------------------


class TestCLIExitCodes:
    """Test error-to-exit-code mapping."""

    @patch("nautobot_mcp.cli.devices.get_client_from_ctx")
    @patch("nautobot_mcp.cli.devices.devices")
    def test_connection_error_exit_code_2(self, mock_devices_mod, mock_get_client):
        """Connection error should exit with code 2."""
        mock_devices_mod.list_devices.side_effect = NautobotConnectionError(
            message="Cannot connect"
        )

        from nautobot_mcp.cli.app import app
        result = runner.invoke(app, ["devices", "list"])
        assert result.exit_code == 2
        assert "Connection error" in result.output

    @patch("nautobot_mcp.cli.devices.get_client_from_ctx")
    @patch("nautobot_mcp.cli.devices.devices")
    def test_not_found_error_exit_code_3(self, mock_devices_mod, mock_get_client):
        """Not found error should exit with code 3."""
        mock_devices_mod.get_device.side_effect = NautobotNotFoundError(
            message="Device not found"
        )

        from nautobot_mcp.cli.app import app
        result = runner.invoke(app, ["devices", "get", "--name", "nonexistent"])
        assert result.exit_code == 3
        assert "Not found" in result.output
