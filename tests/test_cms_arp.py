"""Tests for CMS ARP model and CRUD functions.

Covers:
- ArpEntrySummary.from_nautobot() field extraction
- list_arp_entries() with device, interface, and MAC filters
- get_arp_entry() by UUID
"""

from unittest.mock import MagicMock, patch

import pytest

from nautobot_mcp.cms.arp import get_arp_entry, list_arp_entries
from nautobot_mcp.models.cms.arp import ArpEntrySummary
from nautobot_mcp.models.base import ListResponse


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_arp_record():
    """Mock pynautobot record mimicking a JuniperArpEntry."""
    record = MagicMock()
    record.id = "arp-aaaa-bbbb-cccc-dddd"
    record.display = "10.0.0.1 (aa:bb:cc:dd:ee:ff)"
    record.url = "http://test/api/plugins/cms/arp-aaaa/"

    # Device FK
    record.device.id = "dev-1111-2222-3333-4444"
    record.device.name = "core-rtr-01"
    record.device.display = "core-rtr-01"

    # Interface FK
    record.interface.id = "iface-5555-6666-7777-8888"
    record.interface.display = "ge-0/0/0.100"
    record.interface.name = "ge-0/0/0.100"
    record.interface.device = None  # already set at top level

    # IP address nested FK
    record.ip_address.display = "10.0.0.1/24"
    record.ip_address.address = "10.0.0.1/24"

    # Scalar fields
    record.mac_address = "aa:bb:cc:dd:ee:ff"
    record.hostname = "host-a.example.com"

    return record


@pytest.fixture
def mock_client():
    """Mock NautobotClient."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


def test_arp_entry_from_nautobot(mock_arp_record):
    """from_nautobot() should extract all fields correctly."""
    entry = ArpEntrySummary.from_nautobot(mock_arp_record)

    assert entry.id == "arp-aaaa-bbbb-cccc-dddd"
    assert entry.mac_address == "aa:bb:cc:dd:ee:ff"
    assert entry.hostname == "host-a.example.com"
    assert entry.ip_address == "10.0.0.1/24"
    assert entry.interface_id == "iface-5555-6666-7777-8888"
    assert entry.interface_name == "ge-0/0/0.100"
    assert entry.device_id == "dev-1111-2222-3333-4444"
    assert entry.device_name == "core-rtr-01"


def test_arp_entry_defaults():
    """hostname should default to empty string, optional fields should be None."""
    entry = ArpEntrySummary(
        id="arp-test",
        display="10.0.0.2",
        device_id="dev-001",
        interface_id="iface-001",
        ip_address="10.0.0.2/32",
        mac_address="00:11:22:33:44:55",
    )
    assert entry.hostname == ""
    assert entry.device_name is None
    assert entry.interface_name is None


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------


def test_list_arp_entries_by_device(mock_client):
    """list_arp_entries() with device= should resolve device ID and filter by it."""
    mock_entry = ArpEntrySummary(
        id="arp-001", display="10.0.0.1", device_id="dev-resolved",
        interface_id="iface-001", ip_address="10.0.0.1/24", mac_address="aa:bb:cc:dd:ee:ff",
    )
    expected = ListResponse(count=1, results=[mock_entry])

    with patch("nautobot_mcp.cms.arp.resolve_device_id", return_value="dev-resolved-uuid") as mock_resolve, \
         patch("nautobot_mcp.cms.arp.cms_list", return_value=expected) as mock_list:
        result = list_arp_entries(mock_client, device="core-rtr-01")

    mock_resolve.assert_called_once_with(mock_client, "core-rtr-01")
    mock_list.assert_called_once_with(
        mock_client, "juniper_arp_entries", ArpEntrySummary,
        limit=0, device="dev-resolved-uuid",
    )
    assert result.count == 1
    assert result.results[0].id == "arp-001"


def test_list_arp_entries_by_interface(mock_client):
    """list_arp_entries() with interface= should filter by interface."""
    expected = ListResponse(count=0, results=[])

    with patch("nautobot_mcp.cms.arp.resolve_device_id", return_value="dev-x") as mock_resolve, \
         patch("nautobot_mcp.cms.arp.cms_list", return_value=expected) as mock_list:
        result = list_arp_entries(mock_client, device="rtr-01", interface="ge-0/0/0.0")

    mock_list.assert_called_once_with(
        mock_client, "juniper_arp_entries", ArpEntrySummary,
        limit=0, device="dev-x", interface="ge-0/0/0.0",
    )
    assert result.count == 0


def test_list_arp_entries_by_mac(mock_client):
    """list_arp_entries() with mac_address= should add mac_address filter."""
    expected = ListResponse(count=0, results=[])

    with patch("nautobot_mcp.cms.arp.resolve_device_id", return_value="dev-y"), \
         patch("nautobot_mcp.cms.arp.cms_list", return_value=expected) as mock_list:
        list_arp_entries(mock_client, device="rtr-02", mac_address="00:11:22:33:44:55")

    call_kwargs = mock_list.call_args.kwargs
    assert call_kwargs.get("mac_address") == "00:11:22:33:44:55"


def test_list_arp_entries_combined_filters(mock_client):
    """list_arp_entries() combining device + interface filters should pass both."""
    expected = ListResponse(count=0, results=[])

    with patch("nautobot_mcp.cms.arp.resolve_device_id", return_value="dev-z"), \
         patch("nautobot_mcp.cms.arp.cms_list", return_value=expected) as mock_list:
        list_arp_entries(mock_client, device="rtr-03", interface="ge-0/0/1.200", limit=5)

    mock_list.assert_called_once_with(
        mock_client, "juniper_arp_entries", ArpEntrySummary,
        limit=5, device="dev-z", interface="ge-0/0/1.200",
    )


def test_list_arp_entries_no_filters(mock_client):
    """list_arp_entries() with no device should call cms_list without device filter."""
    expected = ListResponse(count=0, results=[])

    with patch("nautobot_mcp.cms.arp.resolve_device_id") as mock_resolve, \
         patch("nautobot_mcp.cms.arp.cms_list", return_value=expected) as mock_list:
        list_arp_entries(mock_client)

    mock_resolve.assert_not_called()
    mock_list.assert_called_once_with(
        mock_client, "juniper_arp_entries", ArpEntrySummary, limit=0
    )


def test_get_arp_entry(mock_client):
    """get_arp_entry() should delegate to cms_get with the correct id."""
    mock_entry = ArpEntrySummary(
        id="arp-xyz", display="10.1.1.1", device_id="dev-001",
        interface_id="iface-001", ip_address="10.1.1.1/32", mac_address="cc:dd:ee:ff:00:11",
    )

    with patch("nautobot_mcp.cms.arp.cms_get", return_value=mock_entry) as mock_get:
        result = get_arp_entry(mock_client, id="arp-xyz")

    mock_get.assert_called_once_with(
        mock_client, "juniper_arp_entries", ArpEntrySummary, id="arp-xyz"
    )
    assert result.id == "arp-xyz"
    assert result.mac_address == "cc:dd:ee:ff:00:11"
