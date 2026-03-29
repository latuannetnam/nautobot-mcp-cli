"""Tests for devices.py — VLAN count error handling and warnings.

Covers VLAN-01, VLAN-02, VLAN-03, VLAN-04 and TEST-01.
D-01: location=<uuid> instead of location=<name>
D-04: NautobotAPIError caught → vlan_count=None + warning appended
D-05/D-06: warnings field with {"section", "message", "recoverable"}
D-07: vlan_count=None → null in JSON
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import json as json_module

import pytest

from nautobot_mcp.devices import get_device_summary, get_device_inventory
from nautobot_mcp.exceptions import NautobotAPIError
from tests.conftest import *  # noqa: F403 — fixtures from conftest.py


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_mock_device_record():
    """Build a fresh mock device record using conftest fixture pattern."""
    device = MagicMock()
    device.id = "aaaa-bbbb-cccc-dddd"
    device.name = "core-rtr-01"
    device.status.display = "Active"
    device.device_type.id = "1111-2222-3333-4444"
    device.device_type.name = "MX204"
    device.device_type.display = "Juniper MX204"
    device.location.id = "5555-6666-7777-8888"  # UUID — D-01
    device.location.name = "SGN-DC1"  # name — should NOT be used for VLAN count
    device.location.display = "SGN-DC1"
    device.tenant = None
    device.role = None
    device.platform = MagicMock()
    device.platform.name = "junos"
    device.serial = "ABC123"
    device.primary_ip = None
    return device


# ---------------------------------------------------------------------------
# TestDeviceVLANCountErrorHandling
# ---------------------------------------------------------------------------


class TestDeviceVLANCountErrorHandling:
    """Test that VLAN count failures are handled gracefully.

    Verifies D-01 (UUID), D-04 (catch), D-05/D-06 (warnings), D-07 (null serialization).
    """

    # ------------------------------------------------------------------
    # get_device_summary
    # ------------------------------------------------------------------

    def test_get_device_summary_catches_vlan_count_500(self):
        """VLAN 500 → vlan_count=None, warning appended, no crash."""
        mock_client = MagicMock()

        # Device fetch succeeds
        mock_client.api.dcim.devices.get.return_value = make_mock_device_record()

        # All count() calls: mock client.count directly (avoids HTTP session chain)
        def count_side_effect(app, endpoint, **kwargs):
            if app == "dcim" and endpoint == "interfaces":
                return 24
            elif app == "ipam" and endpoint == "ip_addresses":
                return 100
            elif app == "ipam" and endpoint == "vlans":
                raise NautobotAPIError("HTTP 500 during VLAN count", status_code=500)
            return 0

        mock_client.count.side_effect = count_side_effect

        result = get_device_summary(mock_client, name="core-rtr-01")

        # D-04: vlan_count is None (not 0, not re-raised)
        assert result.vlan_count is None
        # D-05/D-06: warnings present with correct structure
        assert result.warnings is not None
        assert len(result.warnings) == 1
        w = result.warnings[0]
        assert w["section"] == "vlans"
        assert "recoverable" in w
        assert w["recoverable"] is True
        assert "message" in w

        # Other counts unaffected
        assert result.interface_count == 24
        assert result.ip_count == 100

    def test_get_device_summary_normal_vlan_count(self):
        """Normal VLAN count (no 500) → vlan_count=int, warnings=None."""
        mock_client = MagicMock()
        mock_client.api.dcim.devices.get.return_value = make_mock_device_record()

        def count_side_effect(app, endpoint, **kwargs):
            if app == "dcim" and endpoint == "interfaces":
                return 24
            elif app == "ipam" and endpoint == "ip_addresses":
                return 100
            elif app == "ipam" and endpoint == "vlans":
                return 42
            return 0

        mock_client.count.side_effect = count_side_effect

        result = get_device_summary(mock_client, name="core-rtr-01")

        assert result.vlan_count == 42
        assert result.warnings is None

    def test_vlan_count_by_uuid_not_name(self):
        """count() is called with location=<uuid>, not location=<name>."""
        mock_client = MagicMock()
        mock_client.api.dcim.devices.get.return_value = make_mock_device_record()

        def count_side_effect(app, endpoint, **kwargs):
            if app == "dcim" and endpoint == "interfaces":
                return 24
            elif app == "ipam" and endpoint == "ip_addresses":
                return 100
            elif app == "ipam" and endpoint == "vlans":
                # Verify location kwarg is the UUID, not the name
                loc = kwargs.get("location")
                assert loc == "5555-6666-7777-8888", f"Expected UUID, got {loc!r}"
                assert loc != "SGN-DC1"
                return 5
            return 0

        mock_client.count.side_effect = count_side_effect

        get_device_summary(mock_client, name="core-rtr-01")

        # If we get here without assertion error, the UUID was passed correctly
        assert True

    # ------------------------------------------------------------------
    # get_device_inventory — sequential "vlans" branch
    # ------------------------------------------------------------------

    def test_get_device_inventory_catches_vlan_count_500(self):
        """Sequential 'vlans' branch: 500 → total_vlans=None, warning appended."""
        mock_client = MagicMock()
        mock_client.api.dcim.devices.get.return_value = make_mock_device_record()

        def count_side_effect(app, endpoint, **kwargs):
            if app == "dcim" and endpoint == "interfaces":
                return 10
            elif app == "ipam" and endpoint == "vlans":
                raise NautobotAPIError("HTTP 500", status_code=500)
            return 0

        mock_client.count.side_effect = count_side_effect

        result = get_device_inventory(
            mock_client, name="core-rtr-01", detail="vlans", limit=50
        )

        assert result.total_vlans is None
        assert result.warnings is not None
        assert any(w["section"] == "vlans" for w in result.warnings)

    # ------------------------------------------------------------------
    # get_device_inventory — parallel block (detail="all")
    # ------------------------------------------------------------------

    def test_get_device_inventory_parallel_catches_vlan_count_500(self):
        """Parallel block: _count_vlans_by_loc returns None → warning appended."""
        mock_client = MagicMock()
        mock_client.api.dcim.devices.get.return_value = make_mock_device_record()

        mock_ips_resp = MagicMock()
        mock_ips_resp.total_ips = 50

        def count_side_effect(app, endpoint, **kwargs):
            if app == "dcim" and endpoint == "interfaces":
                return 10
            elif app == "ipam" and endpoint == "vlans":
                raise NautobotAPIError("HTTP 500", status_code=500)
            return 0

        mock_client.count.side_effect = count_side_effect

        with patch("nautobot_mcp.ipam.get_device_ips") as mock_get_ips:
            mock_get_ips.return_value = mock_ips_resp

            result = get_device_inventory(
                mock_client, name="core-rtr-01", detail="all", limit=50
            )

        # Parallel path caught the error → total_vlans=None, warning appended
        assert result.total_vlans is None
        assert result.warnings is not None
        assert any(w["section"] == "vlans" for w in result.warnings)

    # ------------------------------------------------------------------
    # get_device_inventory — sequential fallback
    # ------------------------------------------------------------------

    def test_get_device_inventory_fallback_catches_vlan_count_500(self):
        """Sequential fallback path catches VLAN 500 → total_vlans=None."""
        mock_client = MagicMock()
        mock_client.api.dcim.devices.get.return_value = make_mock_device_record()

        mock_ips_resp = MagicMock()
        mock_ips_resp.total_ips = 50

        # Call tracker: 1=parallel interfaces (raises → fallback), 2=fallback interfaces (ok),
        # 3=fallback VLANs (raises → caught)
        call_num = [0]

        def count_side_effect(app, endpoint, **kwargs):
            call_num[0] += 1
            if app == "dcim" and endpoint == "interfaces":
                if call_num[0] == 1:
                    raise NautobotAPIError("force parallel failure", status_code=500)
                return 10  # fallback call succeeds
            elif app == "ipam" and endpoint == "vlans":
                raise NautobotAPIError("HTTP 500", status_code=500)
            return 0

        mock_client.count.side_effect = count_side_effect

        with patch("nautobot_mcp.ipam.get_device_ips") as mock_get_ips:
            mock_get_ips.return_value = mock_ips_resp
            result = get_device_inventory(
                mock_client, name="core-rtr-01", detail="all", limit=50
            )

        # Fallback caught VLAN 500 → total_vlans=None, warning appended
        assert result.total_vlans is None
        assert result.warnings is not None

    # ------------------------------------------------------------------
    # JSON serialization (D-07)
    # ------------------------------------------------------------------

    def test_null_vlan_count_serializes_to_null_in_json(self):
        """vlan_count=None serializes to JSON null, not a crash."""
        mock_client = MagicMock()
        mock_client.api.dcim.devices.get.return_value = make_mock_device_record()

        def count_side_effect(app, endpoint, **kwargs):
            if app == "dcim" and endpoint == "interfaces":
                return 24
            elif app == "ipam" and endpoint == "ip_addresses":
                return 100
            elif app == "ipam" and endpoint == "vlans":
                raise NautobotAPIError("HTTP 500", status_code=500)
            return 0

        mock_client.count.side_effect = count_side_effect

        result = get_device_summary(mock_client, name="core-rtr-01")

        # model_dump should not raise
        data = result.model_dump()
        assert data["vlan_count"] is None

        # json.dumps should produce "null", not "None"
        json_str = json_module.dumps(data, indent=2)
        assert "null" in json_str
        assert "None" not in json_str

    # ------------------------------------------------------------------
    # Warning dict structure (D-05/D-06)
    # ------------------------------------------------------------------

    def test_warning_dict_structure(self):
        """Warning dict has required fields: section, message, recoverable."""
        mock_client = MagicMock()
        mock_client.api.dcim.devices.get.return_value = make_mock_device_record()

        def count_side_effect(app, endpoint, **kwargs):
            if app == "dcim" and endpoint == "interfaces":
                return 24
            elif app == "ipam" and endpoint == "ip_addresses":
                return 100
            elif app == "ipam" and endpoint == "vlans":
                raise NautobotAPIError("HTTP 500", status_code=500)
            return 0

        mock_client.count.side_effect = count_side_effect

        result = get_device_summary(mock_client, name="core-rtr-01")

        assert result.warnings is not None
        w = result.warnings[0]

        # Required fields per D-06
        assert "section" in w
        assert "message" in w
        assert "recoverable" in w

        # Value types
        assert isinstance(w["section"], str)
        assert isinstance(w["message"], str)
        assert isinstance(w["recoverable"], bool)
        assert w["section"] == "vlans"
        assert w["recoverable"] is True
