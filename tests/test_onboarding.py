"""Unit tests for the config onboarding engine."""

from unittest.mock import MagicMock, patch

import pytest

from nautobot_mcp.exceptions import NautobotNotFoundError
from nautobot_mcp.models.onboarding import OnboardAction, OnboardResult, OnboardSummary
from nautobot_mcp.models.parser import (
    ParsedConfig,
    ParsedIPAddress,
    ParsedInterface,
    ParsedInterfaceUnit,
    ParsedSystemSettings,
    ParsedVLAN,
)
from nautobot_mcp.onboarding import map_interface_type, onboard_config


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_parsed_config() -> ParsedConfig:
    """Return a minimal parsed config for testing."""
    return ParsedConfig(
        hostname="core-rtr-01",
        platform="MX",
        network_os="juniper_junos",
        interfaces=[
            ParsedInterface(
                name="ge-0/0/0",
                description="Uplink to core",
                enabled=True,
                units=[
                    ParsedInterfaceUnit(
                        unit=0,
                        description="Primary",
                        ip_addresses=[
                            ParsedIPAddress(address="10.0.0.1/30", family="inet"),
                        ],
                    ),
                ],
            ),
            ParsedInterface(
                name="lo0",
                description="Loopback",
                enabled=True,
                units=[
                    ParsedInterfaceUnit(
                        unit=0,
                        description="",
                        ip_addresses=[
                            ParsedIPAddress(address="192.168.1.1/32", family="inet"),
                        ],
                    ),
                ],
            ),
        ],
        vlans=[
            ParsedVLAN(name="MGMT", vlan_id=100, description="Management VLAN"),
        ],
        system=ParsedSystemSettings(hostname="core-rtr-01"),
    )


@pytest.fixture
def mock_client() -> MagicMock:
    """Return a mocked NautobotClient."""
    client = MagicMock()
    client.api.ipam.ip_addresses.get.return_value = None
    client.api.ipam.vlans.get.return_value = None
    return client


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


def test_onboard_action_model():
    """Verify OnboardAction pydantic model fields."""
    action = OnboardAction(
        action="create",
        object_type="interface",
        name="ge-0/0/0",
        details={"type": "1000base-t"},
        reason="Not found in Nautobot",
    )
    assert action.action == "create"
    assert action.object_type == "interface"
    assert action.name == "ge-0/0/0"
    assert action.details == {"type": "1000base-t"}
    assert action.reason == "Not found in Nautobot"


def test_onboard_result_model():
    """Verify OnboardResult with summary counts."""
    summary = OnboardSummary(total=3, created=1, updated=1, skipped=1, failed=0)
    result = OnboardResult(
        device="test-device",
        dry_run=True,
        summary=summary,
        actions=[
            OnboardAction(action="create", object_type="interface", name="ge-0/0/0"),
            OnboardAction(action="update", object_type="interface", name="ge-0/0/1"),
            OnboardAction(action="skip", object_type="interface", name="ge-0/0/2"),
        ],
        warnings=["test warning"],
    )
    assert result.device == "test-device"
    assert result.dry_run is True
    assert result.summary.total == 3
    assert result.summary.created == 1
    assert len(result.actions) == 3
    assert len(result.warnings) == 1


# ---------------------------------------------------------------------------
# Interface type mapping tests
# ---------------------------------------------------------------------------


def test_map_interface_type_ge():
    """ge- maps to 1000base-t."""
    assert map_interface_type("ge-0/0/0") == "1000base-t"


def test_map_interface_type_xe():
    """xe- maps to 10gbase-x-sfpp."""
    assert map_interface_type("xe-0/0/0") == "10gbase-x-sfpp"


def test_map_interface_type_lo():
    """lo maps to virtual."""
    assert map_interface_type("lo0") == "virtual"


def test_map_interface_type_unknown():
    """Unknown prefix maps to 'other'."""
    assert map_interface_type("zzz-0/0/0") == "other"


# ---------------------------------------------------------------------------
# Onboarding engine tests
# ---------------------------------------------------------------------------


@patch("nautobot_mcp.onboarding.get_device")
@patch("nautobot_mcp.onboarding.get_interface")
def test_onboard_config_dry_run(
    mock_get_interface, mock_get_device, mock_client, sample_parsed_config,
):
    """Dry-run returns actions without executing."""
    # Device not found → will create
    mock_get_device.side_effect = NautobotNotFoundError("Not found")
    # Interfaces not found → will create
    mock_get_interface.side_effect = NautobotNotFoundError("Not found")

    result = onboard_config(
        mock_client, sample_parsed_config, "core-rtr-01", dry_run=True,
    )

    assert result.dry_run is True
    assert result.device == "core-rtr-01"
    assert result.summary.total > 0
    # Should have create actions for device, interfaces, IPs, prefixes, VLANs
    create_actions = [a for a in result.actions if a.action == "create"]
    assert len(create_actions) > 0


@patch("nautobot_mcp.onboarding.get_device")
@patch("nautobot_mcp.onboarding.get_interface")
def test_onboard_config_new_device(
    mock_get_interface, mock_get_device, mock_client, sample_parsed_config,
):
    """When device not found, action='create'."""
    mock_get_device.side_effect = NautobotNotFoundError("Not found")
    mock_get_interface.side_effect = NautobotNotFoundError("Not found")

    result = onboard_config(
        mock_client, sample_parsed_config, "core-rtr-01", dry_run=True,
    )

    device_actions = [a for a in result.actions if a.object_type == "device"]
    assert len(device_actions) == 1
    assert device_actions[0].action == "create"


@patch("nautobot_mcp.onboarding.get_device")
@patch("nautobot_mcp.onboarding.get_interface")
def test_onboard_config_existing_device_skip(
    mock_get_interface, mock_get_device, mock_client, sample_parsed_config,
):
    """When device found, action='skip'."""
    mock_existing_device = MagicMock()
    mock_existing_device.id = "existing-device-id"
    mock_get_device.return_value = mock_existing_device
    mock_get_interface.side_effect = NautobotNotFoundError("Not found")

    result = onboard_config(
        mock_client, sample_parsed_config, "core-rtr-01", dry_run=True,
    )

    device_actions = [a for a in result.actions if a.object_type == "device"]
    assert len(device_actions) == 1
    assert device_actions[0].action == "skip"


@patch("nautobot_mcp.onboarding.get_device")
@patch("nautobot_mcp.onboarding.get_interface")
def test_onboard_config_idempotent(
    mock_get_interface, mock_get_device, mock_client, sample_parsed_config,
):
    """Running twice produces same skip results when everything exists."""
    mock_existing_device = MagicMock()
    mock_existing_device.id = "existing-device-id"
    mock_get_device.return_value = mock_existing_device

    mock_existing_iface = MagicMock()
    mock_existing_iface.id = "existing-iface-id"
    mock_existing_iface.description = "Uplink to core"
    mock_get_interface.return_value = mock_existing_iface

    # First run — mark existing IPs and VLANs
    mock_existing_ip = MagicMock()
    mock_existing_ip.id = "existing-ip-id"
    mock_client.api.ipam.ip_addresses.get.return_value = mock_existing_ip

    mock_existing_vlan = MagicMock()
    mock_existing_vlan.id = "existing-vlan-id"
    mock_client.api.ipam.vlans.get.return_value = mock_existing_vlan

    result1 = onboard_config(
        mock_client, sample_parsed_config, "core-rtr-01", dry_run=True,
    )
    result2 = onboard_config(
        mock_client, sample_parsed_config, "core-rtr-01", dry_run=True,
    )

    # Both should be identical
    assert result1.summary.total == result2.summary.total
    assert result1.summary.skipped == result2.summary.skipped
    # All non-prefix actions should be skips (device, interfaces, IPs, VLANs)
    skip_actions = [a for a in result1.actions if a.action == "skip"]
    # Prefix actions are always "create" for auto-prefix, so exclude them
    non_prefix_actions = [a for a in result1.actions if a.object_type != "prefix"]
    non_prefix_skips = [a for a in non_prefix_actions if a.action == "skip"]
    assert len(non_prefix_skips) == len(non_prefix_actions)
