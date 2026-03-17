"""Unit tests for the verification engine."""

from unittest.mock import MagicMock, patch

import pytest

from nautobot_mcp.models.parser import (
    ParsedConfig,
    ParsedIPAddress,
    ParsedInterface,
    ParsedInterfaceUnit,
    ParsedVLAN,
)
from nautobot_mcp.models.verification import DriftItem, DriftReport, DriftSection
from nautobot_mcp.verification import (
    NautobotLiveAdapter,
    ParsedConfigAdapter,
    SyncIPAddress,
    SyncInterface,
    SyncVLAN,
    verify_data_model,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_parsed_config() -> ParsedConfig:
    """Return a minimal parsed config for verification testing."""
    return ParsedConfig(
        hostname="core-rtr-01",
        platform="MX",
        interfaces=[
            ParsedInterface(
                name="ge-0/0/0",
                description="Uplink to core",
                enabled=True,
                units=[
                    ParsedInterfaceUnit(
                        unit=0,
                        ip_addresses=[
                            ParsedIPAddress(address="10.0.0.1/30", family="inet"),
                        ],
                    ),
                ],
            ),
            ParsedInterface(
                name="ge-0/0/1",
                description="Downlink to access",
                enabled=True,
                units=[],
            ),
        ],
        vlans=[
            ParsedVLAN(name="MGMT", vlan_id=100, description="Management"),
        ],
    )


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


def test_drift_item_model():
    """Verify DriftItem fields."""
    item = DriftItem(
        name="ge-0/0/0",
        status="missing_in_nautobot",
        device_value={"description": "Uplink"},
    )
    assert item.name == "ge-0/0/0"
    assert item.status == "missing_in_nautobot"
    assert item.device_value == {"description": "Uplink"}
    assert item.nautobot_value is None
    assert item.changed_fields == {}


def test_drift_section_model():
    """Verify DriftSection with missing/extra/changed."""
    section = DriftSection(
        missing=[DriftItem(name="ge-0/0/0", status="missing_in_nautobot")],
        extra=[DriftItem(name="ge-0/0/2", status="missing_on_device")],
        changed=[DriftItem(name="ge-0/0/1", status="changed",
                          changed_fields={"description": {"device": "A", "nautobot": "B"}})],
    )
    assert len(section.missing) == 1
    assert len(section.extra) == 1
    assert len(section.changed) == 1


def test_drift_report_model():
    """Verify DriftReport grouping."""
    report = DriftReport(
        device="core-rtr-01",
        source="provided",
        interfaces=DriftSection(
            missing=[DriftItem(name="ge-0/0/0", status="missing_in_nautobot")],
        ),
    )
    assert report.device == "core-rtr-01"
    assert len(report.interfaces.missing) == 1
    assert len(report.ip_addresses.missing) == 0
    assert len(report.vlans.missing) == 0


# ---------------------------------------------------------------------------
# DiffSync model tests
# ---------------------------------------------------------------------------


def test_sync_interface_model():
    """Verify DiffSync model identifiers."""
    iface = SyncInterface(
        device_name="core-rtr-01",
        name="ge-0/0/0",
        description="Test",
        enabled=True,
    )
    assert iface.device_name == "core-rtr-01"
    assert iface.name == "ge-0/0/0"


# ---------------------------------------------------------------------------
# Adapter tests
# ---------------------------------------------------------------------------


def test_parsed_config_adapter_load(sample_parsed_config):
    """Load ParsedConfig into adapter."""
    adapter = ParsedConfigAdapter()
    adapter.parsed_config = sample_parsed_config
    adapter.device_name = "core-rtr-01"
    adapter.load()

    # Should have 2 interfaces
    interfaces = adapter.get_all("interface")
    assert len(interfaces) == 2

    # Should have 1 IP
    ips = adapter.get_all("ipaddress")
    assert len(ips) == 1

    # Should have 1 VLAN
    vlans = adapter.get_all("vlan")
    assert len(vlans) == 1


def test_nautobot_adapter_load():
    """Load from mocked client."""
    mock_client = MagicMock()

    # Mock interface response
    mock_iface = MagicMock()
    mock_iface.name = "ge-0/0/0"
    mock_iface.description = "Test"
    mock_iface.enabled = True

    mock_iface_response = MagicMock()
    mock_iface_response.results = [mock_iface]

    # Mock empty IP and VLAN responses
    mock_ip_response = MagicMock()
    mock_ip_response.results = []
    mock_vlan_response = MagicMock()
    mock_vlan_response.results = []

    with patch("nautobot_mcp.verification.list_interfaces", return_value=mock_iface_response), \
         patch("nautobot_mcp.verification.list_ip_addresses", return_value=mock_ip_response), \
         patch("nautobot_mcp.verification.list_vlans", return_value=mock_vlan_response):

        adapter = NautobotLiveAdapter()
        adapter.client = mock_client
        adapter.device_name = "core-rtr-01"
        adapter.load()

        interfaces = adapter.get_all("interface")
        assert len(interfaces) == 1
        assert interfaces[0].name == "ge-0/0/0"


# ---------------------------------------------------------------------------
# Verification function tests
# ---------------------------------------------------------------------------


@patch("nautobot_mcp.verification.list_interfaces")
@patch("nautobot_mcp.verification.list_ip_addresses")
@patch("nautobot_mcp.verification.list_vlans")
def test_verify_data_model_no_drift(
    mock_vlans, mock_ips, mock_ifaces, sample_parsed_config,
):
    """Matching data returns empty drifts."""
    mock_client = MagicMock()

    # Mock Nautobot responses that match parsed config exactly
    iface1 = MagicMock()
    iface1.name = "ge-0/0/0"
    iface1.description = "Uplink to core"
    iface1.enabled = True

    iface2 = MagicMock()
    iface2.name = "ge-0/0/1"
    iface2.description = "Downlink to access"
    iface2.enabled = True

    mock_ifaces.return_value = MagicMock(results=[iface1, iface2])

    ip1 = MagicMock()
    ip1.address = "10.0.0.1/30"
    ip1.interface = "ge-0/0/0.0"
    mock_ips.return_value = MagicMock(results=[ip1])

    vlan1 = MagicMock()
    vlan1.vid = 100
    vlan1.name = "MGMT"
    vlan1.description = "Management"
    mock_vlans.return_value = MagicMock(results=[vlan1])

    result = verify_data_model(mock_client, "core-rtr-01", sample_parsed_config)

    assert result.device == "core-rtr-01"
    assert result.summary["total_drifts"] == 0


@patch("nautobot_mcp.verification.list_interfaces")
@patch("nautobot_mcp.verification.list_ip_addresses")
@patch("nautobot_mcp.verification.list_vlans")
def test_verify_data_model_missing_interface(
    mock_vlans, mock_ips, mock_ifaces, sample_parsed_config,
):
    """Interface on device but not in Nautobot detected."""
    mock_client = MagicMock()

    # Only return one interface from Nautobot (missing ge-0/0/1)
    iface1 = MagicMock()
    iface1.name = "ge-0/0/0"
    iface1.description = "Uplink to core"
    iface1.enabled = True
    mock_ifaces.return_value = MagicMock(results=[iface1])

    ip1 = MagicMock()
    ip1.address = "10.0.0.1/30"
    ip1.interface = "ge-0/0/0.0"
    mock_ips.return_value = MagicMock(results=[ip1])

    vlan1 = MagicMock()
    vlan1.vid = 100
    vlan1.name = "MGMT"
    vlan1.description = "Management"
    mock_vlans.return_value = MagicMock(results=[vlan1])

    result = verify_data_model(mock_client, "core-rtr-01", sample_parsed_config)

    # ge-0/0/1 should be detected as missing in nautobot
    assert result.summary["total_drifts"] > 0


@patch("nautobot_mcp.verification.list_interfaces")
@patch("nautobot_mcp.verification.list_ip_addresses")
@patch("nautobot_mcp.verification.list_vlans")
def test_verify_data_model_extra_interface(
    mock_vlans, mock_ips, mock_ifaces, sample_parsed_config,
):
    """Interface in Nautobot but not on device detected."""
    mock_client = MagicMock()

    # Return 3 interfaces (one extra not in parsed config)
    iface1 = MagicMock()
    iface1.name = "ge-0/0/0"
    iface1.description = "Uplink to core"
    iface1.enabled = True
    iface2 = MagicMock()
    iface2.name = "ge-0/0/1"
    iface2.description = "Downlink to access"
    iface2.enabled = True
    iface3 = MagicMock()
    iface3.name = "ge-0/0/9"
    iface3.description = "Extra interface"
    iface3.enabled = True
    mock_ifaces.return_value = MagicMock(results=[iface1, iface2, iface3])

    ip1 = MagicMock()
    ip1.address = "10.0.0.1/30"
    ip1.interface = "ge-0/0/0.0"
    mock_ips.return_value = MagicMock(results=[ip1])

    vlan1 = MagicMock()
    vlan1.vid = 100
    vlan1.name = "MGMT"
    vlan1.description = "Management"
    mock_vlans.return_value = MagicMock(results=[vlan1])

    result = verify_data_model(mock_client, "core-rtr-01", sample_parsed_config)

    # Extra interface should show up in summary
    assert result.summary["total_drifts"] > 0


@patch("nautobot_mcp.verification.list_interfaces")
@patch("nautobot_mcp.verification.list_ip_addresses")
@patch("nautobot_mcp.verification.list_vlans")
def test_verify_data_model_changed_description(
    mock_vlans, mock_ips, mock_ifaces, sample_parsed_config,
):
    """Different description detected as changed."""
    mock_client = MagicMock()

    # Return interface with different description
    iface1 = MagicMock()
    iface1.name = "ge-0/0/0"
    iface1.description = "OLD description"  # Different from "Uplink to core"
    iface1.enabled = True
    iface2 = MagicMock()
    iface2.name = "ge-0/0/1"
    iface2.description = "Downlink to access"
    iface2.enabled = True
    mock_ifaces.return_value = MagicMock(results=[iface1, iface2])

    ip1 = MagicMock()
    ip1.address = "10.0.0.1/30"
    ip1.interface = "ge-0/0/0.0"
    mock_ips.return_value = MagicMock(results=[ip1])

    vlan1 = MagicMock()
    vlan1.vid = 100
    vlan1.name = "MGMT"
    vlan1.description = "Management"
    mock_vlans.return_value = MagicMock(results=[vlan1])

    result = verify_data_model(mock_client, "core-rtr-01", sample_parsed_config)

    # Description change should be detected
    assert result.summary["total_drifts"] > 0
    assert result.summary["by_type"]["interfaces"]["changed"] > 0
