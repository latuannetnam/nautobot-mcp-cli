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
