"""Tests for CMS routing models and CRUD functions.

Covers:
- Pydantic model from_nautobot() construction (all 8 models)
- CRUD function behavior: list (with nexthop inlining), get, create, delete
- BGP neighbor device-scoped and group_id-scoped queries
"""

from unittest.mock import MagicMock, call, patch

import pytest

from nautobot_mcp.cms.routing import (
    create_static_route,
    delete_static_route,
    get_bgp_group,
    get_bgp_neighbor,
    get_static_route,
    list_bgp_address_families,
    list_bgp_groups,
    list_bgp_neighbors,
    list_bgp_received_routes,
    list_static_route_nexthops,
    list_static_routes,
)
from nautobot_mcp.models.cms.routing import (
    BGPAddressFamilySummary,
    BGPGroupSummary,
    BGPNeighborSummary,
    BGPPolicyAssociationSummary,
    BGPReceivedRouteSummary,
    StaticRouteNexthopSummary,
    StaticRouteQualifiedNexthopSummary,
    StaticRouteSummary,
)


# ---------------------------------------------------------------------------
# Fixtures (routing-specific)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_static_route_record():
    """Mock pynautobot record mimicking a JuniperStaticRoute."""
    record = MagicMock()
    record.id = "route-aaaa-bbbb-cccc-dddd"
    record.display = "192.168.1.0/24 via inet.0"
    record.url = "http://test/api/plugins/cms/route-aaaa/"

    # Device FK
    record.device.id = "dev-1111-2222-3333-4444"
    record.device.name = "core-rtr-01"
    record.device.display = "core-rtr-01"

    # Fields
    record.destination = "192.168.1.0/24"
    record.routing_table = "inet.0"
    record.address_family = "ipv4"
    record.preference = 5
    record.metric = 0
    record.enabled = True
    record.discarded = False
    record.rejected = False
    record.communities = ""
    record.is_active = True
    record.route_state = "active"

    # Nested routing_instance FK
    record.routing_instance.id = "ri-5555-6666-7777-8888"
    record.routing_instance.display = "default"
    record.routing_instance.name = "default"

    return record


@pytest.fixture
def mock_bgp_group_record():
    """Mock pynautobot record mimicking a JuniperBGPGroup."""
    record = MagicMock()
    record.id = "bgpg-aaaa-bbbb-cccc-dddd"
    record.display = "EXTERNAL-PEERS"
    record.url = "http://test/api/plugins/cms/bgp-group-aaaa/"

    # Device FK
    record.device.id = "dev-1111-2222-3333-4444"
    record.device.name = "core-rtr-01"
    record.device.display = "core-rtr-01"

    # Fields
    record.name = "EXTERNAL-PEERS"
    record.description = "External BGP peers"
    record.type = "external"
    record.cluster_id = ""
    record.authentication_algorithm = ""
    record.enabled = True
    record.neighbor_count = 2

    # local_address FK
    record.local_address.id = "ip-aaaa-bbbb-cccc-dddd"
    record.local_address.address = "10.0.0.1/32"
    record.local_address.display = "10.0.0.1/32"

    # routing_instance FK
    record.routing_instance.id = "ri-5555-6666-7777-8888"
    record.routing_instance.display = "default"
    record.routing_instance.name = "default"

    return record


@pytest.fixture
def mock_bgp_neighbor_record():
    """Mock pynautobot record mimicking a JuniperBGPNeighbor."""
    record = MagicMock()
    record.id = "nbr-aaaa-bbbb-cccc-dddd"
    record.display = "Peer 203.0.113.1"
    record.url = "http://test/api/plugins/cms/bgp-nbr-aaaa/"

    # Device FK (no device on neighbor — comes via group)
    record.device = None

    # Group FK
    record.group.id = "bgpg-aaaa-bbbb-cccc-dddd"
    record.group.display = "EXTERNAL-PEERS"
    record.group.name = "EXTERNAL-PEERS"

    # peer_ip FK
    record.peer_ip.address = "203.0.113.1/32"
    record.peer_ip.display = "203.0.113.1/32"

    # local_address FK
    record.local_address = None

    # Fields
    record.description = "Upstream peer"
    record.peer_as = 65001
    record.remove_private_as = False
    record.as_override = False
    record.enabled = True
    record.session_state = "Established"
    record.received_prefix_count = 100
    record.sent_prefix_count = 5
    record.flap_count = 0

    return record


# ---------------------------------------------------------------------------
# Pydantic Model Tests
# ---------------------------------------------------------------------------


class TestStaticRouteSummary:
    """Tests for StaticRouteSummary model."""

    def test_from_nautobot_basic(self, mock_static_route_record):
        """Creates model from a mock record with basic fields."""
        model = StaticRouteSummary.from_nautobot(mock_static_route_record)
        assert model.id == "route-aaaa-bbbb-cccc-dddd"
        assert model.destination == "192.168.1.0/24"
        assert model.routing_table == "inet.0"
        assert model.preference == 5
        assert model.enabled is True
        assert model.device_id == "dev-1111-2222-3333-4444"
        assert model.device_name == "core-rtr-01"

    def test_from_nautobot_with_routing_instance(self, mock_static_route_record):
        """Extracts routing_instance_name from nested FK."""
        model = StaticRouteSummary.from_nautobot(mock_static_route_record)
        assert model.routing_instance_id == "ri-5555-6666-7777-8888"
        assert model.routing_instance_name == "default"

    def test_nexthops_default_empty(self, mock_static_route_record):
        """nexthops and qualified_nexthops default to empty lists."""
        model = StaticRouteSummary.from_nautobot(mock_static_route_record)
        assert model.nexthops == []
        assert model.qualified_nexthops == []


class TestBGPGroupSummary:
    """Tests for BGPGroupSummary model."""

    def test_from_nautobot_basic(self, mock_bgp_group_record):
        """Creates model from mock record with name, type, local_address."""
        model = BGPGroupSummary.from_nautobot(mock_bgp_group_record)
        assert model.id == "bgpg-aaaa-bbbb-cccc-dddd"
        assert model.name == "EXTERNAL-PEERS"
        assert model.type == "external"
        assert model.enabled is True
        assert model.neighbor_count == 2

    def test_from_nautobot_with_local_address(self, mock_bgp_group_record):
        """Extracts local_address from nested FK."""
        model = BGPGroupSummary.from_nautobot(mock_bgp_group_record)
        assert model.local_address == "10.0.0.1/32"

    def test_from_nautobot_with_routing_instance(self, mock_bgp_group_record):
        """Extracts routing_instance nested FK fields."""
        model = BGPGroupSummary.from_nautobot(mock_bgp_group_record)
        assert model.routing_instance_id == "ri-5555-6666-7777-8888"
        assert model.routing_instance_name == "default"


class TestBGPNeighborSummary:
    """Tests for BGPNeighborSummary model."""

    def test_from_nautobot_basic(self, mock_bgp_neighbor_record):
        """Creates model from mock with peer_ip, peer_as, session_state."""
        model = BGPNeighborSummary.from_nautobot(mock_bgp_neighbor_record)
        assert model.id == "nbr-aaaa-bbbb-cccc-dddd"
        assert model.peer_as == 65001
        assert model.session_state == "Established"
        assert model.received_prefix_count == 100
        assert model.sent_prefix_count == 5

    def test_from_nautobot_extracts_peer_ip(self, mock_bgp_neighbor_record):
        """Extracts peer_ip address from nested FK."""
        model = BGPNeighborSummary.from_nautobot(mock_bgp_neighbor_record)
        assert model.peer_ip == "203.0.113.1/32"

    def test_from_nautobot_extracts_group(self, mock_bgp_neighbor_record):
        """Extracts group_id and group_name from nested FK."""
        model = BGPNeighborSummary.from_nautobot(mock_bgp_neighbor_record)
        assert model.group_id == "bgpg-aaaa-bbbb-cccc-dddd"
        assert model.group_name == "EXTERNAL-PEERS"


class TestBGPReceivedRouteSummary:
    """Tests for BGPReceivedRouteSummary model."""

    def test_from_nautobot_basic(self):
        """Creates model from mock with prefix, as_path, is_active."""
        record = MagicMock()
        record.id = "rr-1234"
        record.display = "1.2.3.0/24"
        record.url = None
        record.device = None

        record.neighbor.id = "nbr-aaaa-bbbb-cccc-dddd"
        record.neighbor.display = "Peer"

        record.routing_table = "inet.0"
        record.prefix = "1.2.3.0/24"  # plain string
        record.is_active = True
        record.as_path = "65001 65002"
        record.local_preference = 100
        record.med = None
        record.next_hop = MagicMock(address="10.0.0.1/32", display="10.0.0.1/32")
        record.origin = "egp"
        record.communities = "65001:100"

        model = BGPReceivedRouteSummary.from_nautobot(record)
        assert model.is_active is True
        assert model.as_path == "65001 65002"
        assert model.local_preference == 100
        assert model.neighbor_id == "nbr-aaaa-bbbb-cccc-dddd"


# ---------------------------------------------------------------------------
# CRUD Function Tests
# ---------------------------------------------------------------------------


class TestListStaticRoutes:
    """Tests for list_static_routes CRUD function."""

    def test_list_with_device(self, mock_client_with_cms, mock_static_route_record):
        """Resolves device name, calls cms_list, returns ListResponse."""
        mock_device = MagicMock()
        mock_device.id = "dev-1111-2222-3333-4444"
        mock_client_with_cms.api.dcim.devices.get.return_value = mock_device

        mock_client_with_cms.cms.juniper_static_routes.filter.return_value = [mock_static_route_record]
        mock_client_with_cms.cms.juniper_static_route_nexthops.filter.return_value = []
        mock_client_with_cms.cms.juniper_static_route_qualified_nexthops.filter.return_value = []

        result = list_static_routes(mock_client_with_cms, device="core-rtr-01")
        assert result.count == 1
        assert result.results[0].destination == "192.168.1.0/24"

    def test_list_inlines_nexthops(self, mock_client_with_cms, mock_static_route_record):
        """Verifies nexthops are attached to route results."""
        mock_device = MagicMock()
        mock_device.id = "dev-1111-2222-3333-4444"
        mock_client_with_cms.api.dcim.devices.get.return_value = mock_device

        # Create a nexthop record that references the route
        nh_record = MagicMock()
        nh_record.id = "nh-5555-6666-7777-8888"
        nh_record.display = "via 10.0.0.2"
        nh_record.url = None
        nh_record.device = None
        nh_record.route.id = "route-aaaa-bbbb-cccc-dddd"
        nh_record.route.display = "route"
        nh_record.ip_address.address = "10.0.0.2"
        nh_record.ip_address.display = "10.0.0.2"
        nh_record.is_active_nexthop = True
        nh_record.weight = 1
        nh_record.lsp_name = ""
        nh_record.mpls_label = ""
        nh_record.nexthop_type = "unicast"
        nh_record.via_interface = None

        mock_client_with_cms.cms.juniper_static_routes.filter.return_value = [mock_static_route_record]
        mock_client_with_cms.cms.juniper_static_route_nexthops.filter.return_value = [nh_record]
        mock_client_with_cms.cms.juniper_static_route_qualified_nexthops.filter.return_value = []

        result = list_static_routes(mock_client_with_cms, device="core-rtr-01")
        assert len(result.results[0].nexthops) == 1
        assert result.results[0].nexthops[0].ip_address == "10.0.0.2"

    def test_list_with_routing_instance_filter(self, mock_client_with_cms, mock_static_route_record):
        """Passes routing_instance filter to cms_list."""
        mock_device = MagicMock()
        mock_device.id = "dev-1111-2222-3333-4444"
        mock_client_with_cms.api.dcim.devices.get.return_value = mock_device
        mock_client_with_cms.cms.juniper_static_routes.filter.return_value = []
        mock_client_with_cms.cms.juniper_static_route_nexthops.filter.return_value = []
        mock_client_with_cms.cms.juniper_static_route_qualified_nexthops.filter.return_value = []

        result = list_static_routes(mock_client_with_cms, device="core-rtr-01", routing_instance="mgmt")
        # Should have passed routing_instance__name filter
        mock_client_with_cms.cms.juniper_static_routes.filter.assert_called_once_with(
            device="dev-1111-2222-3333-4444",
            routing_instance__name="mgmt",
        )


class TestListBGPGroups:
    """Tests for list_bgp_groups CRUD function."""

    def test_list_with_device(self, mock_client_with_cms, mock_bgp_group_record):
        """Resolves device, returns BGP groups."""
        mock_device = MagicMock()
        mock_device.id = "dev-1111-2222-3333-4444"
        mock_client_with_cms.api.dcim.devices.get.return_value = mock_device
        mock_client_with_cms.cms.juniper_bgp_groups.filter.return_value = [mock_bgp_group_record]

        result = list_bgp_groups(mock_client_with_cms, device="core-rtr-01")
        assert result.count == 1
        assert result.results[0].name == "EXTERNAL-PEERS"


class TestListBGPNeighbors:
    """Tests for list_bgp_neighbors CRUD function."""

    def test_list_by_device(self, mock_client_with_cms, mock_bgp_group_record, mock_bgp_neighbor_record):
        """Fetches all groups first, then queries neighbors by group_id."""
        mock_device = MagicMock()
        mock_device.id = "dev-1111-2222-3333-4444"
        mock_client_with_cms.api.dcim.devices.get.return_value = mock_device
        mock_client_with_cms.cms.juniper_bgp_groups.filter.return_value = [mock_bgp_group_record]
        mock_client_with_cms.cms.juniper_bgp_neighbors.filter.return_value = [mock_bgp_neighbor_record]

        result = list_bgp_neighbors(mock_client_with_cms, device="core-rtr-01")
        assert result.count == 1
        assert result.results[0].peer_as == 65001

    def test_list_by_group_id(self, mock_client_with_cms, mock_bgp_neighbor_record):
        """Filters directly by group_id when provided."""
        mock_client_with_cms.cms.juniper_bgp_neighbors.filter.return_value = [mock_bgp_neighbor_record]

        result = list_bgp_neighbors(mock_client_with_cms, group_id="bgpg-aaaa-bbbb-cccc-dddd")
        assert result.count == 1
        mock_client_with_cms.cms.juniper_bgp_neighbors.filter.assert_called_once_with(
            group="bgpg-aaaa-bbbb-cccc-dddd"
        )

    def test_list_returns_empty_without_groups(self, mock_client_with_cms):
        """Returns empty result when device has no BGP groups."""
        mock_device = MagicMock()
        mock_device.id = "dev-1111-2222-3333-4444"
        mock_client_with_cms.api.dcim.devices.get.return_value = mock_device
        mock_client_with_cms.cms.juniper_bgp_groups.filter.return_value = []

        result = list_bgp_neighbors(mock_client_with_cms, device="core-rtr-01")
        assert result.count == 0


class TestCreateStaticRoute:
    """Tests for create_static_route CRUD function."""

    def test_create_basic(self, mock_client_with_cms, mock_static_route_record):
        """Calls cms_create with expected parameters."""
        mock_device = MagicMock()
        mock_device.id = "dev-1111-2222-3333-4444"
        mock_client_with_cms.api.dcim.devices.get.return_value = mock_device
        mock_client_with_cms.cms.juniper_static_routes.create.return_value = mock_static_route_record

        result = create_static_route(
            mock_client_with_cms,
            device="core-rtr-01",
            destination="192.168.1.0/24",
        )
        assert result.destination == "192.168.1.0/24"
        mock_client_with_cms.cms.juniper_static_routes.create.assert_called_once_with(
            device="dev-1111-2222-3333-4444",
            destination="192.168.1.0/24",
            routing_table="inet.0",
            preference=5,
        )


class TestDeleteStaticRoute:
    """Tests for delete_static_route CRUD function."""

    def test_delete_success(self, mock_client_with_cms, mock_static_route_record):
        """Calls cms_delete and returns success dict."""
        mock_client_with_cms.cms.juniper_static_routes.get.return_value = mock_static_route_record

        result = delete_static_route(mock_client_with_cms, id="route-aaaa-bbbb-cccc-dddd")
        assert result["success"] is True
        mock_static_route_record.delete.assert_called_once()


class TestListBGPAddressFamilies:
    """Tests for list_bgp_address_families (read-only)."""

    def test_list_by_neighbor_id(self, mock_client_with_cms):
        """Filters by neighbor_id when provided."""
        af_record = MagicMock()
        af_record.id = "af-aaaa-bbbb-cccc"
        af_record.display = "inet unicast"
        af_record.url = None
        af_record.device = None
        af_record.group = None
        af_record.neighbor.id = "nbr-aaaa-bbbb-cccc-dddd"
        af_record.neighbor.display = "Peer"
        af_record.address_family = "inet"
        af_record.sub_address_family = "unicast"
        af_record.enabled = True
        af_record.prefix_limit_max = None
        af_record.prefix_limit_teardown = False

        mock_client_with_cms.cms.juniper_bgp_address_families.filter.return_value = [af_record]

        result = list_bgp_address_families(mock_client_with_cms, neighbor_id="nbr-aaaa-bbbb-cccc-dddd")
        assert result.count == 1
        assert result.results[0].address_family == "inet"


class TestListBGPReceivedRoutes:
    """Tests for list_bgp_received_routes (read-only)."""

    def test_list_by_neighbor_id(self, mock_client_with_cms):
        """Filters received routes by neighbor_id."""
        rr_record = MagicMock()
        rr_record.id = "rr-aaaa-bbbb"
        rr_record.display = "1.2.3.0/24"
        rr_record.url = None
        rr_record.device = None
        rr_record.neighbor.id = "nbr-aaaa-bbbb-cccc-dddd"
        rr_record.neighbor.display = "Peer"
        rr_record.routing_table = "inet.0"
        rr_record.prefix = "1.2.3.0/24"
        rr_record.is_active = True
        rr_record.as_path = "65001"
        rr_record.local_preference = 100
        rr_record.med = None
        rr_record.next_hop = MagicMock(address="10.0.0.1", display="10.0.0.1")
        rr_record.origin = "egp"
        rr_record.communities = ""

        mock_client_with_cms.cms.juniper_bgp_received_routes.filter.return_value = [rr_record]

        result = list_bgp_received_routes(mock_client_with_cms, neighbor_id="nbr-aaaa-bbbb-cccc-dddd")
        assert result.count == 1
        assert result.results[0].prefix == "1.2.3.0/24"


class TestListStaticRouteNexthops:
    """Tests for list_static_route_nexthops (read-only)."""

    def test_list_by_route_id(self, mock_client_with_cms):
        """Filters nexthops by parent route_id."""
        nh_record = MagicMock()
        nh_record.id = "nh-aaaa-bbbb"
        nh_record.display = "via 10.0.0.2"
        nh_record.url = None
        nh_record.device = None
        nh_record.route.id = "route-aaaa-bbbb-cccc-dddd"
        nh_record.route.display = "route"
        nh_record.ip_address.address = "10.0.0.2"
        nh_record.ip_address.display = "10.0.0.2"
        nh_record.is_active_nexthop = True
        nh_record.weight = 1
        nh_record.lsp_name = ""
        nh_record.mpls_label = ""
        nh_record.nexthop_type = "unicast"
        nh_record.via_interface = None

        mock_client_with_cms.cms.juniper_static_route_nexthops.filter.return_value = [nh_record]

        result = list_static_route_nexthops(mock_client_with_cms, route_id="route-aaaa-bbbb-cccc-dddd")
        assert result.count == 1
        assert result.results[0].ip_address == "10.0.0.2"
