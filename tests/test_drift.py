"""Unit tests for file-free drift comparison engine."""

from unittest.mock import MagicMock, patch

import pytest

from nautobot_mcp.drift import _normalize_input, _validate_ips, compare_device
from nautobot_mcp.models.drift import DriftSummary, InterfaceDrift, QuickDriftReport


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestDriftModels:
    """Test drift Pydantic models."""

    def test_interface_drift_defaults(self):
        d = InterfaceDrift(interface="ae0.0")
        assert d.interface == "ae0.0"
        assert d.missing_ips == []
        assert d.extra_ips == []
        assert d.missing_vlans == []
        assert d.extra_vlans == []
        assert d.has_drift is False

    def test_drift_summary_defaults(self):
        s = DriftSummary()
        assert s.total_drifts == 0
        assert s.by_type["ips"]["missing"] == 0

    def test_quick_drift_report_structure(self):
        r = QuickDriftReport(device="test-device")
        assert r.device == "test-device"
        assert r.interface_drifts == []
        assert r.warnings == []


# ---------------------------------------------------------------------------
# Input normalization tests
# ---------------------------------------------------------------------------


class TestNormalizeInput:
    """Test _normalize_input auto-detection."""

    def test_flat_map_with_ips_and_vlans(self):
        data = {"ae0.0": {"ips": ["10.1.1.1/30"], "vlans": [100, 200]}}
        result, warnings = _normalize_input(data)
        assert result["ae0.0"]["ips"] == ["10.1.1.1/30"]
        assert result["ae0.0"]["vlans"] == [100, 200]
        assert warnings == []

    def test_flat_map_legacy_ip_list(self):
        """Legacy format: {"ae0.0": ["10.1.1.1/30"]}."""
        data = {"ae0.0": ["10.1.1.1/30"]}
        result, warnings = _normalize_input(data)
        assert result["ae0.0"]["ips"] == ["10.1.1.1/30"]
        assert result["ae0.0"]["vlans"] == []

    def test_device_ip_entry_list(self):
        data = [
            {"interface": "ae0.0", "address": "10.1.1.1/30"},
            {"interface": "ae0.0", "address": "10.1.1.2/30"},
            {"interface": "ge-0/0/0.0", "address": "192.168.1.1/24"},
        ]
        result, warnings = _normalize_input(data)
        assert len(result["ae0.0"]["ips"]) == 2
        assert "192.168.1.1/24" in result["ge-0/0/0.0"]["ips"]

    def test_device_ip_entry_with_interface_name_key(self):
        """Accept 'interface_name' as alternative to 'interface'."""
        data = [{"interface_name": "ae0.0", "address": "10.1.1.1/30"}]
        result, warnings = _normalize_input(data)
        assert "ae0.0" in result

    def test_vlan_id_string_normalization(self):
        data = {"ae0.0": {"ips": [], "vlans": ["100", "200"]}}
        result, warnings = _normalize_input(data)
        assert result["ae0.0"]["vlans"] == [100, 200]

    def test_invalid_vlan_id_warns(self):
        data = {"ae0.0": {"ips": [], "vlans": ["abc"]}}
        result, warnings = _normalize_input(data)
        assert result["ae0.0"]["vlans"] == []
        assert any("Invalid VLAN ID" in w for w in warnings)


# ---------------------------------------------------------------------------
# IP validation tests
# ---------------------------------------------------------------------------


class TestValidateIPs:
    """Test _validate_ips lenient validation."""

    def test_ip_with_prefix_no_warning(self):
        ips, warnings = _validate_ips(["10.1.1.1/30"], "ae0.0")
        assert ips == ["10.1.1.1/30"]
        assert warnings == []

    def test_ip_without_prefix_warns(self):
        ips, warnings = _validate_ips(["10.1.1.1"], "ae0.0")
        assert ips == ["10.1.1.1"]
        assert any("no prefix length" in w for w in warnings)


# ---------------------------------------------------------------------------
# compare_device integration tests
# ---------------------------------------------------------------------------


class TestCompareDevice:
    """Test compare_device with mocked Nautobot client."""

    def _mock_nautobot(self, nb_ips, nb_ifaces, nb_vlans_per_iface=None):
        """Helper: build mocked client with given Nautobot state."""
        mock_client = MagicMock()

        # Mock get_device_ips response
        ip_entries = []
        for iface, addr in nb_ips:
            entry = MagicMock()
            entry.interface_name = iface
            entry.address = addr
            ip_entries.append(entry)
        ip_response = MagicMock()
        ip_response.interface_ips = ip_entries

        # Mock list_interfaces response
        iface_records = []
        for name in nb_ifaces:
            iface = MagicMock()
            iface.name = name
            iface.untagged_vlan = None
            iface.tagged_vlans = []
            if nb_vlans_per_iface and name in nb_vlans_per_iface:
                for vid in nb_vlans_per_iface[name]:
                    vlan_mock = MagicMock()
                    vlan_mock.vid = vid
                    iface.tagged_vlans.append(vlan_mock)
            iface_records.append(iface)
        iface_response = MagicMock()
        iface_response.results = iface_records

        return mock_client, ip_response, iface_response

    @patch("nautobot_mcp.drift.list_interfaces")
    @patch("nautobot_mcp.drift.get_device_ips")
    def test_no_drift(self, mock_get_ips, mock_list_ifaces):
        mock_client, ip_resp, iface_resp = self._mock_nautobot(
            nb_ips=[("ae0.0", "10.1.1.1/30")],
            nb_ifaces=["ae0.0"],
        )
        mock_get_ips.return_value = ip_resp
        mock_list_ifaces.return_value = iface_resp

        result = compare_device(
            mock_client, "test-device",
            {"ae0.0": {"ips": ["10.1.1.1/30"]}},
        )
        assert result.summary.total_drifts == 0
        assert result.interface_drifts[0].has_drift is False

    @patch("nautobot_mcp.drift.list_interfaces")
    @patch("nautobot_mcp.drift.get_device_ips")
    def test_missing_ip_detected(self, mock_get_ips, mock_list_ifaces):
        mock_client, ip_resp, iface_resp = self._mock_nautobot(
            nb_ips=[],
            nb_ifaces=["ae0.0"],
        )
        mock_get_ips.return_value = ip_resp
        mock_list_ifaces.return_value = iface_resp

        result = compare_device(
            mock_client, "test-device",
            {"ae0.0": {"ips": ["10.1.1.1/30"]}},
        )
        assert result.summary.total_drifts > 0
        assert "10.1.1.1/30" in result.interface_drifts[0].missing_ips

    @patch("nautobot_mcp.drift.list_interfaces")
    @patch("nautobot_mcp.drift.get_device_ips")
    def test_extra_ip_detected(self, mock_get_ips, mock_list_ifaces):
        mock_client, ip_resp, iface_resp = self._mock_nautobot(
            nb_ips=[("ae0.0", "10.1.1.1/30"), ("ae0.0", "10.1.1.2/30")],
            nb_ifaces=["ae0.0"],
        )
        mock_get_ips.return_value = ip_resp
        mock_list_ifaces.return_value = iface_resp

        result = compare_device(
            mock_client, "test-device",
            {"ae0.0": {"ips": ["10.1.1.1/30"]}},
        )
        assert "10.1.1.2/30" in result.interface_drifts[0].extra_ips

    @patch("nautobot_mcp.drift.list_interfaces")
    @patch("nautobot_mcp.drift.get_device_ips")
    def test_missing_vlan_detected(self, mock_get_ips, mock_list_ifaces):
        mock_client, ip_resp, iface_resp = self._mock_nautobot(
            nb_ips=[],
            nb_ifaces=["ae0.0"],
            nb_vlans_per_iface={"ae0.0": []},
        )
        mock_get_ips.return_value = ip_resp
        mock_list_ifaces.return_value = iface_resp

        result = compare_device(
            mock_client, "test-device",
            {"ae0.0": {"ips": [], "vlans": [100]}},
        )
        assert 100 in result.interface_drifts[0].missing_vlans

    @patch("nautobot_mcp.drift.list_interfaces")
    @patch("nautobot_mcp.drift.get_device_ips")
    def test_missing_interface_detected(self, mock_get_ips, mock_list_ifaces):
        mock_client, ip_resp, iface_resp = self._mock_nautobot(
            nb_ips=[],
            nb_ifaces=[],  # no interfaces in Nautobot
        )
        mock_get_ips.return_value = ip_resp
        mock_list_ifaces.return_value = iface_resp

        result = compare_device(
            mock_client, "test-device",
            {"ae0.0": {"ips": ["10.1.1.1/30"]}},
        )
        assert "ae0.0" in result.summary.missing_interfaces

    @patch("nautobot_mcp.drift.list_interfaces")
    @patch("nautobot_mcp.drift.get_device_ips")
    def test_device_ip_entry_input_shape(self, mock_get_ips, mock_list_ifaces):
        """DeviceIPEntry list input auto-detected and compared correctly."""
        mock_client, ip_resp, iface_resp = self._mock_nautobot(
            nb_ips=[("ae0.0", "10.1.1.1/30")],
            nb_ifaces=["ae0.0"],
        )
        mock_get_ips.return_value = ip_resp
        mock_list_ifaces.return_value = iface_resp

        result = compare_device(
            mock_client, "test-device",
            [{"interface": "ae0.0", "address": "10.1.1.1/30"}],
        )
        assert result.summary.total_drifts == 0

    @patch("nautobot_mcp.drift.list_interfaces")
    @patch("nautobot_mcp.drift.get_device_ips")
    def test_bare_ip_host_matching(self, mock_get_ips, mock_list_ifaces):
        """IPs without prefix match by host part."""
        mock_client, ip_resp, iface_resp = self._mock_nautobot(
            nb_ips=[("ae0.0", "10.1.1.1/30")],
            nb_ifaces=["ae0.0"],
        )
        mock_get_ips.return_value = ip_resp
        mock_list_ifaces.return_value = iface_resp

        result = compare_device(
            mock_client, "test-device",
            {"ae0.0": {"ips": ["10.1.1.1"]}},
        )
        assert result.summary.total_drifts == 0
        assert any("no prefix length" in w for w in result.warnings)
