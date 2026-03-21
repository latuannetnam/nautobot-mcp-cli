"""Unit tests for CMS drift CLI module (Phase 14-01).

Covers:
- drift bgp command: --from-file, --json, stdin fallback, table output
- drift routes command: --from-file, --json, table output
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from nautobot_mcp.cli.app import app
from nautobot_mcp.models.cms.cms_drift import CMSDriftReport
from nautobot_mcp.models.verification import DriftSection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

runner = CliRunner()


def _make_empty_report(device: str = "test-device") -> CMSDriftReport:
    """Build a CMSDriftReport with no drifts."""
    report = CMSDriftReport(device=device)
    report.summary = {
        "total_drifts": 0,
        "by_type": {
            "bgp_neighbors": {"missing": 0, "extra": 0, "changed": 0, "total": 0},
            "static_routes": {"missing": 0, "extra": 0, "changed": 0, "total": 0},
        },
    }
    return report


def _bgp_json_file(tmp_path: Path) -> Path:
    """Write a minimal live BGP JSON file and return its path."""
    data = [{"peer_ip": "10.0.0.1", "peer_as": 65001, "local_address": "10.0.0.2", "group_name": "EXTERNAL"}]
    p = tmp_path / "live_bgp.json"
    p.write_text(json.dumps(data))
    return p


def _routes_json_file(tmp_path: Path) -> Path:
    """Write a minimal live routes JSON file and return its path."""
    data = [{"destination": "192.168.1.0/24", "nexthops": ["10.0.0.1"], "preference": 5, "metric": 0}]
    p = tmp_path / "live_routes.json"
    p.write_text(json.dumps(data))
    return p


# ---------------------------------------------------------------------------
# Tests: drift bgp
# ---------------------------------------------------------------------------


class TestDriftBgpFromFile:
    """Test 'nautobot-mcp cms drift bgp' with --from-file."""

    @patch("nautobot_mcp.cli.cms_drift.compare_bgp_neighbors")
    @patch("nautobot_mcp.cli.cms_drift.get_client_from_ctx")
    def test_exit_code_zero(self, mock_client, mock_compare, tmp_path):
        """Command exits 0 with valid --from-file input."""
        mock_client.return_value = MagicMock()
        mock_compare.return_value = _make_empty_report()
        json_file = _bgp_json_file(tmp_path)

        result = runner.invoke(app, ["cms", "drift", "bgp", "--device", "test-device", "--from-file", str(json_file)])
        assert result.exit_code == 0, result.output

    @patch("nautobot_mcp.cli.cms_drift.compare_bgp_neighbors")
    @patch("nautobot_mcp.cli.cms_drift.get_client_from_ctx")
    def test_table_output_contains_device_name(self, mock_client, mock_compare, tmp_path):
        """Table output includes the device name."""
        mock_client.return_value = MagicMock()
        mock_compare.return_value = _make_empty_report(device="core-rtr-01")
        json_file = _bgp_json_file(tmp_path)

        result = runner.invoke(app, ["cms", "drift", "bgp", "--device", "core-rtr-01", "--from-file", str(json_file)])
        assert "core-rtr-01" in result.output

    @patch("nautobot_mcp.cli.cms_drift.compare_bgp_neighbors")
    @patch("nautobot_mcp.cli.cms_drift.get_client_from_ctx")
    def test_json_output_flag(self, mock_client, mock_compare, tmp_path):
        """--json flag produces valid JSON output."""
        mock_client.return_value = MagicMock()
        mock_compare.return_value = _make_empty_report()
        json_file = _bgp_json_file(tmp_path)

        result = runner.invoke(app, ["--json", "cms", "drift", "bgp", "--device", "test-device", "--from-file", str(json_file)])
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.output)
        assert "device" in parsed
        assert parsed["device"] == "test-device"

    @patch("nautobot_mcp.cli.cms_drift.compare_bgp_neighbors")
    @patch("nautobot_mcp.cli.cms_drift.get_client_from_ctx")
    def test_compare_called_with_correct_args(self, mock_client, mock_compare, tmp_path):
        """compare_bgp_neighbors is called with device_name and parsed live_neighbors."""
        mock_client.return_value = MagicMock()
        mock_compare.return_value = _make_empty_report()
        json_file = _bgp_json_file(tmp_path)

        runner.invoke(app, ["cms", "drift", "bgp", "--device", "rtr-01", "--from-file", str(json_file)])
        mock_compare.assert_called_once()
        call_kwargs = mock_compare.call_args
        assert call_kwargs.kwargs["device_name"] == "rtr-01"
        assert isinstance(call_kwargs.kwargs["live_neighbors"], list)


# ---------------------------------------------------------------------------
# Tests: drift routes
# ---------------------------------------------------------------------------


class TestDriftRoutesFromFile:
    """Test 'nautobot-mcp cms drift routes' with --from-file."""

    @patch("nautobot_mcp.cli.cms_drift.compare_static_routes")
    @patch("nautobot_mcp.cli.cms_drift.get_client_from_ctx")
    def test_exit_code_zero(self, mock_client, mock_compare, tmp_path):
        """Command exits 0 with valid --from-file input."""
        mock_client.return_value = MagicMock()
        mock_compare.return_value = _make_empty_report()
        json_file = _routes_json_file(tmp_path)

        result = runner.invoke(app, ["cms", "drift", "routes", "--device", "test-device", "--from-file", str(json_file)])
        assert result.exit_code == 0, result.output

    @patch("nautobot_mcp.cli.cms_drift.compare_static_routes")
    @patch("nautobot_mcp.cli.cms_drift.get_client_from_ctx")
    def test_table_output_contains_device_name(self, mock_client, mock_compare, tmp_path):
        """Table output includes the device name."""
        mock_client.return_value = MagicMock()
        mock_compare.return_value = _make_empty_report(device="edge-rtr-01")
        json_file = _routes_json_file(tmp_path)

        result = runner.invoke(app, ["cms", "drift", "routes", "--device", "edge-rtr-01", "--from-file", str(json_file)])
        assert "edge-rtr-01" in result.output

    @patch("nautobot_mcp.cli.cms_drift.compare_static_routes")
    @patch("nautobot_mcp.cli.cms_drift.get_client_from_ctx")
    def test_json_output_flag(self, mock_client, mock_compare, tmp_path):
        """--json flag produces valid JSON output."""
        mock_client.return_value = MagicMock()
        mock_compare.return_value = _make_empty_report()
        json_file = _routes_json_file(tmp_path)

        result = runner.invoke(app, ["--json", "cms", "drift", "routes", "--device", "test-device", "--from-file", str(json_file)])
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.output)
        assert "device" in parsed

    @patch("nautobot_mcp.cli.cms_drift.compare_static_routes")
    @patch("nautobot_mcp.cli.cms_drift.get_client_from_ctx")
    def test_compare_called_with_correct_args(self, mock_client, mock_compare, tmp_path):
        """compare_static_routes is called with device_name and parsed live_routes."""
        mock_client.return_value = MagicMock()
        mock_compare.return_value = _make_empty_report()
        json_file = _routes_json_file(tmp_path)

        runner.invoke(app, ["cms", "drift", "routes", "--device", "rtr-01", "--from-file", str(json_file)])
        mock_compare.assert_called_once()
        call_kwargs = mock_compare.call_args
        assert call_kwargs.kwargs["device_name"] == "rtr-01"
        assert isinstance(call_kwargs.kwargs["live_routes"], list)
