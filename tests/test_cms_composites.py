"""Tests for Phase 12 composite summary functions and response models.

Covers:
- BGPSummaryResponse, RoutingTableResponse, InterfaceDetailResponse,
  FirewallSummaryResponse model construction
- get_device_bgp_summary() default and detail modes
- get_device_routing_table() default and detail modes
- get_interface_detail() default and include_arp modes
- get_device_firewall_summary() default and detail modes
"""

from unittest.mock import MagicMock, patch

import pytest

from nautobot_mcp.models.cms.composites import (
    BGPSummaryResponse,
    FirewallSummaryResponse,
    InterfaceDetailResponse,
    RoutingTableResponse,
)


# ---------------------------------------------------------------------------
# Fixtures — lightweight mock objects
# ---------------------------------------------------------------------------


def _mock_bgp_group(id_="grp-001", name="IBGP"):
    g = MagicMock()
    g.id = id_
    g.model_dump.return_value = {"id": id_, "name": name, "type": "internal", "local_as": 65001}
    return g


def _mock_bgp_neighbor(id_="nbr-001", group_id="grp-001", peer_ip="10.0.0.1"):
    n = MagicMock()
    n.id = id_
    n.group_id = group_id
    n.model_dump.return_value = {"id": id_, "peer_ip": peer_ip, "peer_as": 65002, "session_state": "established"}
    return n


def _mock_static_route(id_="rt-001", destination="10.0.0.0/8"):
    r = MagicMock()
    r.id = id_
    r.model_dump.return_value = {
        "id": id_, "destination": destination,
        "routing_table": "inet.0", "preference": 5,
        "routing_instance_name": "default",
        "nexthops": [{"ip_address": "192.168.1.1"}],
        "qualified_nexthops": [],
    }
    return r


def _mock_fw_filter(id_="flt-001", name="FILTER-IN"):
    f = MagicMock()
    f.id = id_
    f.model_dump.return_value = {"id": id_, "name": name, "family": "inet", "term_count": 0}
    return f


def _mock_fw_policer(id_="pol-001", name="POLICER-1"):
    p = MagicMock()
    p.id = id_
    p.model_dump.return_value = {"id": id_, "name": name, "action_count": 0}
    return p


def _mock_list_response(*items):
    """Return a MagicMock ListResponse with items as results."""
    resp = MagicMock()
    resp.results = list(items)
    resp.count = len(items)
    return resp


def _mock_client():
    return MagicMock()


# ---------------------------------------------------------------------------
# Composite model tests
# ---------------------------------------------------------------------------


def test_bgp_summary_response_model():
    """BGPSummaryResponse should expose device_name, groups, total_groups, total_neighbors."""
    r = BGPSummaryResponse(
        device_name="rtr-01",
        groups=[{"name": "IBGP"}],
        total_groups=1,
        total_neighbors=3,
    )
    assert r.device_name == "rtr-01"
    assert r.total_groups == 1
    assert r.total_neighbors == 3
    assert len(r.groups) == 1


def test_routing_table_response_model():
    """RoutingTableResponse should expose device_name, routes, total_routes."""
    r = RoutingTableResponse(
        device_name="rtr-02",
        routes=[{"destination": "0.0.0.0/0"}],
        total_routes=1,
    )
    assert r.device_name == "rtr-02"
    assert r.total_routes == 1
    assert len(r.routes) == 1


def test_interface_detail_response_model():
    """InterfaceDetailResponse should expose device_name, units, total_units, arp_entries."""
    r = InterfaceDetailResponse(
        device_name="edge-01",
        units=[{"interface_name": "ge-0/0/0"}],
        total_units=1,
    )
    assert r.device_name == "edge-01"
    assert r.total_units == 1
    assert r.arp_entries == []


def test_firewall_summary_response_model():
    """FirewallSummaryResponse should expose device_name, filters, policers, totals."""
    r = FirewallSummaryResponse(
        device_name="fw-01",
        filters=[{"name": "FILTER-IN"}],
        policers=[{"name": "POL-1"}],
        total_filters=1,
        total_policers=1,
    )
    assert r.device_name == "fw-01"
    assert r.total_filters == 1
    assert r.total_policers == 1


# ---------------------------------------------------------------------------
# BGP Summary tests
# ---------------------------------------------------------------------------


def test_bgp_summary_default():
    """get_device_bgp_summary() default: groups + neighbor counts."""
    from nautobot_mcp.cms.routing import get_device_bgp_summary

    client = _mock_client()
    grp = _mock_bgp_group()
    nbr = _mock_bgp_neighbor(group_id=grp.id)

    with patch("nautobot_mcp.cms.routing.list_bgp_groups", return_value=_mock_list_response(grp)) as mock_grp, \
         patch("nautobot_mcp.cms.routing.list_bgp_neighbors", return_value=_mock_list_response(nbr)) as mock_nbr:
        result = get_device_bgp_summary(client, device="rtr-01")

    assert isinstance(result, BGPSummaryResponse)
    assert result.device_name == "rtr-01"
    assert result.total_groups == 1
    assert result.total_neighbors == 1
    assert len(result.groups) == 1
    assert result.groups[0]["neighbor_count"] == 1

    mock_grp.assert_called_once_with(client, device="rtr-01", limit=0)
    mock_nbr.assert_called_once_with(client, device="rtr-01", limit=0)


def test_bgp_summary_detail():
    """get_device_bgp_summary(detail=True): neighbors include address families + policies."""
    from nautobot_mcp.cms.routing import get_device_bgp_summary

    client = _mock_client()
    grp = _mock_bgp_group()
    nbr = _mock_bgp_neighbor(group_id=grp.id)
    af = MagicMock()
    af.model_dump.return_value = {"address_family": "ipv4"}
    pol = MagicMock()
    pol.model_dump.return_value = {"policy_name": "EXPORT-POLICY"}

    with patch("nautobot_mcp.cms.routing.list_bgp_groups", return_value=_mock_list_response(grp)), \
         patch("nautobot_mcp.cms.routing.list_bgp_neighbors", return_value=_mock_list_response(nbr)), \
         patch("nautobot_mcp.cms.routing.list_bgp_address_families", return_value=_mock_list_response(af)) as mock_af, \
         patch("nautobot_mcp.cms.routing.list_bgp_policy_associations", return_value=_mock_list_response(pol)) as mock_pol:
        result = get_device_bgp_summary(client, device="rtr-01", detail=True)

    assert result.total_neighbors == 1
    neighbor_data = result.groups[0]["neighbors"][0]
    assert "address_families" in neighbor_data
    assert len(neighbor_data["address_families"]) == 1
    assert "policy_associations" in neighbor_data
    mock_af.assert_called_once()
    mock_pol.assert_called_once()


# ---------------------------------------------------------------------------
# Routing Table tests
# ---------------------------------------------------------------------------


def test_routing_table_default():
    """get_device_routing_table() default: routes with nexthop counts (not lists)."""
    from nautobot_mcp.cms.routing import get_device_routing_table

    client = _mock_client()
    route = _mock_static_route()

    with patch("nautobot_mcp.cms.routing.list_static_routes", return_value=_mock_list_response(route)) as mock_routes:
        result = get_device_routing_table(client, device="rtr-02")

    assert isinstance(result, RoutingTableResponse)
    assert result.device_name == "rtr-02"
    assert result.total_routes == 1
    assert len(result.routes) == 1
    # Default mode strips nexthops list, replaces with count
    assert "nexthop_count" in result.routes[0]
    assert "nexthops" not in result.routes[0]
    mock_routes.assert_called_once_with(client, device="rtr-02", limit=0)


def test_routing_table_detail():
    """get_device_routing_table(detail=True): routes include full nexthop lists."""
    from nautobot_mcp.cms.routing import get_device_routing_table

    client = _mock_client()
    route = _mock_static_route()

    with patch("nautobot_mcp.cms.routing.list_static_routes", return_value=_mock_list_response(route)):
        result = get_device_routing_table(client, device="rtr-02", detail=True)

    assert result.total_routes == 1
    # Detail mode keeps nexthops list
    assert "nexthops" in result.routes[0]


# ---------------------------------------------------------------------------
# Interface Detail tests
# ---------------------------------------------------------------------------


def test_interface_detail_default():
    """get_interface_detail() default: units with families + VRRP counts, no ARP."""
    from nautobot_mcp.cms.interfaces import get_interface_detail

    client = _mock_client()

    unit = MagicMock()
    unit.id = "unit-001"
    unit.model_dump.return_value = {"id": "unit-001", "interface_name": "ge-0/0/0", "unit_number": 0}

    fam = MagicMock()
    fam.id = "fam-001"
    fam.model_dump.return_value = {"id": "fam-001", "family_type": "inet"}

    vrrp = MagicMock()
    vrrp.model_dump.return_value = {"id": "vrrp-001", "group_number": 1}

    with patch("nautobot_mcp.cms.interfaces.list_interface_units", return_value=_mock_list_response(unit)) as mock_units, \
         patch("nautobot_mcp.cms.interfaces.list_interface_families", return_value=_mock_list_response(fam)) as mock_fams, \
         patch("nautobot_mcp.cms.interfaces.list_vrrp_groups", return_value=_mock_list_response(vrrp)) as mock_vrrp:
        result = get_interface_detail(client, device="edge-01")

    assert isinstance(result, InterfaceDetailResponse)
    assert result.device_name == "edge-01"
    assert result.total_units == 1
    assert result.arp_entries == []  # include_arp=False by default
    assert len(result.units) == 1
    assert result.units[0]["family_count"] == 1
    assert result.units[0]["families"][0]["vrrp_group_count"] == 1

    mock_units.assert_called_once_with(client, device="edge-01", limit=0)
    mock_fams.assert_called_once_with(client, unit_id="unit-001", limit=0)
    mock_vrrp.assert_called_once_with(client, family_id="fam-001", limit=0)


def test_interface_detail_with_arp():
    """get_interface_detail(include_arp=True): should fetch and include ARP entries."""
    from nautobot_mcp.cms.interfaces import get_interface_detail

    client = _mock_client()

    unit = MagicMock()
    unit.id = "unit-002"
    unit.model_dump.return_value = {"id": "unit-002", "interface_name": "ge-0/0/1"}

    fam = MagicMock()
    fam.id = "fam-002"
    fam.model_dump.return_value = {"id": "fam-002", "family_type": "inet"}

    arp_entry = MagicMock()
    arp_entry.model_dump.return_value = {"id": "arp-001", "mac_address": "aa:bb:cc:dd:ee:ff", "ip_address": "10.0.0.1/24"}

    with patch("nautobot_mcp.cms.interfaces.list_interface_units", return_value=_mock_list_response(unit)), \
         patch("nautobot_mcp.cms.interfaces.list_interface_families", return_value=_mock_list_response(fam)), \
         patch("nautobot_mcp.cms.interfaces.list_vrrp_groups", return_value=_mock_list_response()), \
         patch("nautobot_mcp.cms.arp.list_arp_entries", return_value=_mock_list_response(arp_entry)):
        result = get_interface_detail(client, device="edge-02", include_arp=True)

    assert result.total_units == 1
    assert len(result.arp_entries) == 1
    assert result.arp_entries[0]["mac_address"] == "aa:bb:cc:dd:ee:ff"


# ---------------------------------------------------------------------------
# Firewall Summary tests
# ---------------------------------------------------------------------------


def test_firewall_summary_default():
    """get_device_firewall_summary() default: filter and policer counts."""
    from nautobot_mcp.cms.firewalls import get_device_firewall_summary

    client = _mock_client()
    fw_filter = _mock_fw_filter()
    policer = _mock_fw_policer()

    with patch("nautobot_mcp.cms.firewalls.list_firewall_filters", return_value=_mock_list_response(fw_filter)) as mock_filters, \
         patch("nautobot_mcp.cms.firewalls.list_firewall_policers", return_value=_mock_list_response(policer)) as mock_policers:
        result = get_device_firewall_summary(client, device="fw-01")

    assert isinstance(result, FirewallSummaryResponse)
    assert result.device_name == "fw-01"
    assert result.total_filters == 1
    assert result.total_policers == 1
    assert len(result.filters) == 1
    assert len(result.policers) == 1

    mock_filters.assert_called_once_with(client, device="fw-01", limit=0)
    mock_policers.assert_called_once_with(client, device="fw-01", limit=0)


def test_firewall_summary_detail():
    """get_device_firewall_summary(detail=True): filters include inlined terms."""
    from nautobot_mcp.cms.firewalls import get_device_firewall_summary

    client = _mock_client()
    fw_filter = _mock_fw_filter()
    policer = _mock_fw_policer()

    term = MagicMock()
    term.model_dump.return_value = {"id": "term-001", "name": "accept-mgmt", "match_count": 1, "action_count": 1}

    pa_action = MagicMock()
    pa_action.model_dump.return_value = {"id": "pa-001", "action_type": "policer"}

    with patch("nautobot_mcp.cms.firewalls.list_firewall_filters", return_value=_mock_list_response(fw_filter)), \
         patch("nautobot_mcp.cms.firewalls.list_firewall_policers", return_value=_mock_list_response(policer)), \
         patch("nautobot_mcp.cms.firewalls.list_firewall_terms", return_value=_mock_list_response(term)) as mock_terms, \
         patch("nautobot_mcp.cms.firewalls.list_firewall_policer_actions", return_value=_mock_list_response(pa_action)) as mock_actions:
        result = get_device_firewall_summary(client, device="fw-01", detail=True)

    assert result.total_filters == 1
    assert "terms" in result.filters[0]
    assert len(result.filters[0]["terms"]) == 1
    assert result.filters[0]["terms"][0]["name"] == "accept-mgmt"
    assert "actions" in result.policers[0]
    mock_terms.assert_called_once_with(client, filter_id="flt-001", limit=0)
    mock_actions.assert_called_once_with(client, policer_id="pol-001", limit=0)
