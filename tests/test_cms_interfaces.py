"""Unit tests for CMS interface models, CRUD functions, and CLI commands.

Tests:
1. Pydantic model instantiation and from_nautobot() parsing
2. CRUD function delegation with mocked cms_list/cms_get/cms_create/cms_delete/cms_update
3. CLI command registration and --help output
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from nautobot_mcp.cli.app import app
from nautobot_mcp.models.cms.interfaces import (
    InterfaceFamilyFilterSummary,
    InterfaceFamilyPolicerSummary,
    InterfaceFamilySummary,
    InterfaceUnitSummary,
    VRRPGroupSummary,
    VRRPTrackInterfaceSummary,
    VRRPTrackRouteSummary,
)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def mock_client():
    """Minimal NautobotClient mock with _handle_api_error."""
    client = MagicMock()
    client._handle_api_error = MagicMock(side_effect=lambda e, op, model: None)
    return client


def _make_record(**kwargs):
    """Create a MagicMock record with the given attribute kwargs."""
    record = MagicMock()
    record.id = kwargs.get("id", "aaaaaaaa-0000-0000-0000-000000000001")
    for key, value in kwargs.items():
        setattr(record, key, value)
    return record


# ===========================================================================
# Model: InterfaceUnitSummary
# ===========================================================================


class TestInterfaceUnitSummary:
    def test_default_instantiation(self):
        unit = InterfaceUnitSummary(
            id="unit-1",
            display="ge-0/0/0.0",
            unit_id="unit-1",
        )
        assert unit.id == "unit-1"
        assert unit.family_count == 0
        assert unit.outer_vlan_ids == []
        assert unit.inner_vlan_ids == []
        assert unit.vlan_mode == ""

    def test_from_nautobot_minimal(self):
        record = _make_record(
            id="unit-1",
            display="ge-0/0/0.0",
            url=None,
            unit_number=0,
            vlan_mode="access",
            encapsulation="",
            is_qinq_enabled=False,
            outer_vlans=[],
            inner_vlans=[],
            router_tagged_vlan=None,
            gigether_speed="",
            lacp_active=False,
            description="Test unit",
        )
        record.device = MagicMock()
        record.device.id = "device-1"
        record.device.configure_mock(name="router1")
        record.interface = MagicMock()
        record.interface.id = "iface-1"
        record.interface.display = "ge-0/0/0"
        record.interface.configure_mock(name="ge-0/0/0")

        unit = InterfaceUnitSummary.from_nautobot(record)
        assert unit.id == "unit-1"
        assert unit.interface_id == "iface-1"
        # _extract_nested_id_name uses display first, then name
        assert unit.interface_name in ("ge-0/0/0",)
        assert unit.device_name == "router1"
        assert unit.description == "Test unit"
        assert unit.family_count == 0  # populated by CRUD layer

    def test_from_nautobot_with_vlans(self):
        vlan1 = MagicMock()
        vlan1.id = "vlan-uuid-1"
        vlan1.get = lambda k, default=None: str(vlan1.id) if k == "id" else default

        record = _make_record(
            id="unit-2",
            display="ae0.100",
            url=None,
            unit_number=100,
            vlan_mode="trunk",
            encapsulation="",
            is_qinq_enabled=False,
            outer_vlans=[vlan1],
            inner_vlans=[],
            router_tagged_vlan=None,
            gigether_speed="",
            lacp_active=False,
            description="",
        )
        record.device = MagicMock()
        record.device.id = "device-1"
        record.device.name = "router1"
        record.interface = None

        unit = InterfaceUnitSummary.from_nautobot(record)
        assert unit.outer_vlan_ids == ["vlan-uuid-1"]


# ===========================================================================
# Model: InterfaceFamilySummary
# ===========================================================================


class TestInterfaceFamilySummary:
    def test_default_instantiation(self):
        fam = InterfaceFamilySummary(id="fam-1", display="inet", unit_id="unit-1")
        assert fam.family_type == ""
        assert fam.filter_count == 0
        assert fam.policer_count == 0

    def test_from_nautobot_minimal(self):
        record = _make_record(
            id="fam-1",
            display="inet",
            url=None,
            family_type="inet",
            mtu=None,
        )
        record.device = MagicMock()
        record.device.id = "device-1"
        record.device.name = "router1"
        unit_obj = MagicMock()
        unit_obj.id = "unit-1"
        unit_obj.name = "unit1-display"
        record.interface_unit = unit_obj

        fam = InterfaceFamilySummary.from_nautobot(record)
        assert fam.unit_id == "unit-1"
        assert fam.family_type == "inet"


# ===========================================================================
# Model: InterfaceFamilyFilterSummary
# ===========================================================================


class TestInterfaceFamilyFilterSummary:
    def test_default_instantiation(self):
        f = InterfaceFamilyFilterSummary(
            id="f-1", display="f1", family_id="fam-1", filter_id="filter-1"
        )
        assert f.enabled is True
        assert f.filter_type == ""

    def test_from_nautobot_minimal(self):
        record = _make_record(
            id="filter-assoc-1",
            display="filter-assoc",
            url=None,
            filter_type="input",
            enabled=True,
        )
        record.device = MagicMock()
        record.device.id = "device-1"
        record.device.configure_mock(name="router1")
        family_obj = MagicMock()
        family_obj.id = "fam-1"
        family_obj.configure_mock(name="fam1")
        record.interface_family = family_obj
        filter_obj = MagicMock()
        filter_obj.id = "filter-1"
        filter_obj.display = "my-filter"
        filter_obj.configure_mock(name="my-filter")
        record.filter = filter_obj

        fa = InterfaceFamilyFilterSummary.from_nautobot(record)
        assert fa.family_id == "fam-1"
        assert fa.filter_id == "filter-1"
        assert fa.filter_name == "my-filter"  # from display attribute
        assert fa.filter_type == "input"


# ===========================================================================
# Model: VRRPGroupSummary
# ===========================================================================


class TestVRRPGroupSummary:
    def test_default_instantiation(self):
        grp = VRRPGroupSummary(
            id="g-1", display="VRRP 1", family_id="fam-1", group_number=1,
        )
        assert grp.priority == 100
        assert grp.accept_data is False
        assert grp.track_route_count == 0
        assert grp.track_interface_count == 0

    def test_from_nautobot_minimal(self):
        record = _make_record(
            id="grp-1",
            display="VRRP 1",
            url=None,
            group_number=1,
            priority=150,
            accept_data=True,
            preempt_hold_time=None,
            fast_interval=None,
            authentication_type="",
            authentication_key_chain="",
        )
        record.device = MagicMock()
        record.device.id = "device-1"
        record.device.name = "router1"
        family_obj = MagicMock()
        family_obj.id = "fam-1"
        family_obj.name = "inet"
        record.interface_family = family_obj
        record.virtual_address = None
        record.interface_address = None

        grp = VRRPGroupSummary.from_nautobot(record)
        assert grp.family_id == "fam-1"
        assert grp.group_number == 1
        assert grp.priority == 150
        assert grp.accept_data is True


# ===========================================================================
# Model: VRRPTrackRouteSummary
# ===========================================================================


class TestVRRPTrackRouteSummary:
    def test_from_nautobot_minimal(self):
        record = _make_record(
            id="tr-1",
            display="track-route-1",
            url=None,
            priority_cost=10,
            routing_instance="mgmt",
        )
        record.device = MagicMock()
        record.device.id = "device-1"
        record.device.name = "router1"
        grp_obj = MagicMock()
        grp_obj.id = "grp-1"
        grp_obj.name = "grp1"
        record.vrrp_group = grp_obj
        record.route_address = None

        tr = VRRPTrackRouteSummary.from_nautobot(record)
        assert tr.vrrp_group_id == "grp-1"
        assert tr.priority_cost == 10
        assert tr.routing_instance == "mgmt"


# ===========================================================================
# CRUD Functions
# ===========================================================================


class TestInterfaceUnitCRUD:
    @patch("nautobot_mcp.cms.interfaces.cms_list")
    @patch("nautobot_mcp.cms.interfaces.resolve_device_id")
    def test_list_interface_units_returns_listresponse(self, mock_resolve, mock_list, mock_client):
        from nautobot_mcp.cms.interfaces import list_interface_units
        from nautobot_mcp.models.base import ListResponse

        mock_resolve.return_value = "device-uuid-1"
        unit = InterfaceUnitSummary(id="u1", display="ge-0/0/0.0", unit_id="u1")
        # First call = units, second call = all families
        mock_list.side_effect = [
            ListResponse(count=1, results=[unit]),
            ListResponse(count=0, results=[]),
        ]

        result = list_interface_units(mock_client, device="router1", limit=50)
        assert result.count == 1
        assert result.results[0].id == "u1"
        mock_resolve.assert_called_once_with(mock_client, "router1")

    @patch("nautobot_mcp.cms.interfaces.cms_get")
    def test_get_interface_unit(self, mock_get, mock_client):
        from nautobot_mcp.cms.interfaces import get_interface_unit

        unit = InterfaceUnitSummary(id="u1", display="ge-0/0/0.0", unit_id="u1")

        # Mock cms_list for families (called inside get_interface_unit)
        with patch("nautobot_mcp.cms.interfaces.cms_list") as mock_list:
            from nautobot_mcp.models.base import ListResponse
            mock_get.return_value = unit
            mock_list.return_value = ListResponse(count=0, results=[])

            result = get_interface_unit(mock_client, id="u1")
            assert result.id == "u1"
            assert result.family_count == 0
            mock_get.assert_called_once()

    @patch("nautobot_mcp.cms.interfaces.cms_create")
    def test_create_interface_unit(self, mock_create, mock_client):
        from nautobot_mcp.cms.interfaces import create_interface_unit

        unit = InterfaceUnitSummary(id="u1", display="ge-0/0/0.0", unit_id="u1")
        mock_create.return_value = unit

        result = create_interface_unit(mock_client, interface_id="iface-1", description="Test")
        assert result.id == "u1"
        mock_create.assert_called_once()

    @patch("nautobot_mcp.cms.interfaces.cms_delete")
    def test_delete_interface_unit(self, mock_delete, mock_client):
        from nautobot_mcp.cms.interfaces import delete_interface_unit

        mock_delete.return_value = {"success": True, "message": "Deleted."}
        result = delete_interface_unit(mock_client, id="u1")
        assert result["success"] is True


class TestVRRPGroupCRUD:
    @patch("nautobot_mcp.cms.interfaces.cms_list")
    def test_list_vrrp_groups(self, mock_list, mock_client):
        from nautobot_mcp.cms.interfaces import list_vrrp_groups
        from nautobot_mcp.models.base import ListResponse

        grp = VRRPGroupSummary(id="g1", display="VRRP 1", family_id="fam-1", group_number=1)
        mock_list.return_value = ListResponse(count=1, results=[grp])

        result = list_vrrp_groups(mock_client, family_id="fam-1", limit=50)
        assert result.count == 1
        assert result.results[0].group_number == 1

    @patch("nautobot_mcp.cms.interfaces.cms_list")
    def test_list_vrrp_track_routes(self, mock_list, mock_client):
        from nautobot_mcp.cms.interfaces import list_vrrp_track_routes
        from nautobot_mcp.models.base import ListResponse

        tr = VRRPTrackRouteSummary(id="tr1", display="track-1", vrrp_group_id="grp-1")
        mock_list.return_value = ListResponse(count=1, results=[tr])

        result = list_vrrp_track_routes(mock_client, vrrp_group_id="grp-1", limit=50)
        assert result.count == 1
        assert result.results[0].vrrp_group_id == "grp-1"


class TestFilterPolicerCRUD:
    @patch("nautobot_mcp.cms.interfaces.cms_list")
    def test_list_filters(self, mock_list, mock_client):
        from nautobot_mcp.cms.interfaces import list_interface_family_filters
        from nautobot_mcp.models.base import ListResponse

        fa = InterfaceFamilyFilterSummary(
            id="fa1", display="fa1", family_id="fam-1", filter_id="filter-1"
        )
        mock_list.return_value = ListResponse(count=1, results=[fa])

        result = list_interface_family_filters(mock_client, family_id="fam-1", limit=50)
        assert result.count == 1

    @patch("nautobot_mcp.cms.interfaces.cms_delete")
    def test_delete_filter(self, mock_delete, mock_client):
        from nautobot_mcp.cms.interfaces import delete_interface_family_filter

        mock_delete.return_value = {"success": True, "message": "Deleted."}
        result = delete_interface_family_filter(mock_client, id="fa1")
        assert result["success"] is True


# ===========================================================================
# CLI Commands
# ===========================================================================


class TestInterfacesCLI:
    """Test CLI commands register correctly and show help."""

    runner = CliRunner()

    def test_cms_interfaces_help(self):
        result = self.runner.invoke(app, ["cms", "interfaces", "--help"])
        assert result.exit_code == 0
        assert "list-units" in result.output or "Juniper interface" in result.output.lower()

    def test_list_units_help(self):
        result = self.runner.invoke(app, ["cms", "interfaces", "list-units", "--help"])
        assert result.exit_code == 0
        assert "--device" in result.output

    def test_list_families_help(self):
        result = self.runner.invoke(app, ["cms", "interfaces", "list-families", "--help"])
        assert result.exit_code == 0

    def test_list_vrrp_groups_help(self):
        result = self.runner.invoke(app, ["cms", "interfaces", "list-vrrp-groups", "--help"])
        assert result.exit_code == 0

    def test_list_units_requires_device(self):
        result = self.runner.invoke(app, ["cms", "interfaces", "list-units"])
        assert result.exit_code != 0

    def test_list_filters_help(self):
        result = self.runner.invoke(app, ["cms", "interfaces", "list-filters", "--help"])
        assert result.exit_code == 0
        assert "--family-id" in result.output

    def test_create_vrrp_group_help(self):
        result = self.runner.invoke(app, ["cms", "interfaces", "create-vrrp-group", "--help"])
        assert result.exit_code == 0
        assert "--group-number" in result.output
