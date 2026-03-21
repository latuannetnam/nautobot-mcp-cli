"""Shared test fixtures for nautobot-mcp tests."""

from unittest.mock import MagicMock

import pytest

from nautobot_mcp.config import NautobotProfile, NautobotSettings


@pytest.fixture
def mock_nautobot_profile() -> NautobotProfile:
    """Returns a test NautobotProfile for unit testing."""
    return NautobotProfile(
        url="https://test.nautobot.local",
        token="test-token-123",
        verify_ssl=True,
    )


@pytest.fixture
def mock_settings(mock_nautobot_profile) -> NautobotSettings:
    """Returns NautobotSettings with test profiles."""
    return NautobotSettings(
        profiles={
            "default": mock_nautobot_profile,
            "staging": NautobotProfile(
                url="https://staging.nautobot.local",
                token="staging-token-456",
                verify_ssl=False,
            ),
        },
        active_profile="default",
    )


@pytest.fixture
def mock_device_record() -> MagicMock:
    """Returns a mock object mimicking a pynautobot Device Record."""
    device = MagicMock()
    device.id = "aaaa-bbbb-cccc-dddd"
    device.name = "core-rtr-01"

    # Status
    device.status.display = "Active"

    # DeviceType (RelatedObject)
    device.device_type.id = "1111-2222-3333-4444"
    device.device_type.name = "MX204"
    device.device_type.display = "Juniper MX204"

    # Location (RelatedObject)
    device.location.id = "5555-6666-7777-8888"
    device.location.name = "SGN-DC1"
    device.location.display = "SGN-DC1"

    # Tenant (optional)
    device.tenant.id = "9999-aaaa-bbbb-cccc"
    device.tenant.name = "NetNam"
    device.tenant.display = "NetNam"

    # Role (optional)
    device.role.id = "dddd-eeee-ffff-0000"
    device.role.name = "Router"
    device.role.display = "Router"

    # Platform
    device.platform.name = "junos"

    # Serial
    device.serial = "ABC123"

    # Primary IP
    device.primary_ip = None

    return device


@pytest.fixture
def mock_interface_record() -> MagicMock:
    """Returns a mock object mimicking a pynautobot Interface Record."""
    iface = MagicMock()
    iface.id = "iiii-jjjj-kkkk-llll"
    iface.name = "ge-0/0/0"

    # Type
    iface.type.display = "1000BASE-T"

    # Device (RelatedObject)
    iface.device.id = "aaaa-bbbb-cccc-dddd"
    iface.device.name = "core-rtr-01"
    iface.device.display = "core-rtr-01"

    # Other fields
    iface.enabled = True
    iface.description = "Uplink to core"
    iface.mac_address = "00:11:22:33:44:55"
    iface.mtu = 9000
    iface.ip_addresses = []

    return iface


@pytest.fixture
def mock_cms_plugin():
    """Returns a mock CMS plugin accessor mimicking api.plugins.netnam_cms_core."""
    cms = MagicMock()
    # Each endpoint is a mock that supports .all(), .filter(), .get(), .create()
    return cms


@pytest.fixture
def mock_client_with_cms(mock_nautobot_profile, mock_cms_plugin):
    """Returns a NautobotClient with mocked CMS plugin accessor."""
    from nautobot_mcp.client import NautobotClient

    client = NautobotClient(profile=mock_nautobot_profile)
    # Mock the api property to return a mock with plugins.netnam_cms_core
    mock_api = MagicMock()
    mock_api.plugins.netnam_cms_core = mock_cms_plugin
    mock_api.dcim.devices = MagicMock()
    client._api = mock_api
    return client


@pytest.fixture
def mock_cms_record():
    """Returns a mock CMS record mimicking a pynautobot plugin Record."""
    record = MagicMock()
    record.id = "cms-1111-2222-3333-4444"
    record.display = "test-cms-record"
    record.url = "http://test/api/plugins/netnam-cms-core/juniper-static-routes/cms-1111/"

    # Device reference
    record.device.id = "aaaa-bbbb-cccc-dddd"
    record.device.name = "core-rtr-01"
    record.device.display = "core-rtr-01"

    return record
