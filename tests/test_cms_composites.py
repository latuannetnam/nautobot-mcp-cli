"""Tests for Phase 12 composite summary functions and response models.

Covers:
- BGPSummaryResponse, RoutingTableResponse, InterfaceDetailResponse,
  FirewallSummaryResponse model construction
- get_device_bgp_summary() default and detail modes
- get_device_routing_table() default and detail modes
- get_interface_detail() default and include_arp modes
- get_device_firewall_summary() default and detail modes
"""

from unittest.mock import MagicMock, PropertyMock, patch

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
        result, warnings = get_device_bgp_summary(client, device="rtr-01")

    assert isinstance(result, BGPSummaryResponse)
    assert result.device_name == "rtr-01"
    assert result.total_groups == 1
    assert result.total_neighbors == 1
    assert len(result.groups) == 1
    assert result.groups[0]["neighbor_count"] == 1
    assert warnings == []

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
        result, warnings = get_device_bgp_summary(client, device="rtr-01", detail=True)

    assert result.total_neighbors == 1
    neighbor_data = result.groups[0]["neighbors"][0]
    assert "address_families" in neighbor_data
    assert len(neighbor_data["address_families"]) == 1
    assert "policy_associations" in neighbor_data
    assert warnings == []
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
        result, warnings = get_device_routing_table(client, device="rtr-02")

    assert isinstance(result, RoutingTableResponse)
    assert result.device_name == "rtr-02"
    assert result.total_routes == 1
    assert len(result.routes) == 1
    # Default mode strips nexthops list, replaces with count
    assert "nexthop_count" in result.routes[0]
    assert "nexthops" not in result.routes[0]
    assert warnings == []
    mock_routes.assert_called_once_with(client, device="rtr-02", limit=0)


def test_routing_table_detail():
    """get_device_routing_table(detail=True): routes include full nexthop lists."""
    from nautobot_mcp.cms.routing import get_device_routing_table

    client = _mock_client()
    route = _mock_static_route()

    with patch("nautobot_mcp.cms.routing.list_static_routes", return_value=_mock_list_response(route)):
        result, warnings = get_device_routing_table(client, device="rtr-02", detail=True)

    assert result.total_routes == 1
    # Detail mode keeps nexthops list
    assert "nexthops" in result.routes[0]
    assert warnings == []


# ---------------------------------------------------------------------------
# Interface Detail tests
# ---------------------------------------------------------------------------


def test_interface_detail_default():
    """get_interface_detail() default: units with families + VRRP counts, no ARP."""
    from nautobot_mcp.cms.interfaces import get_interface_detail
    from nautobot_mcp.models.cms.interfaces import InterfaceFamilySummary, VRRPGroupSummary

    client = _mock_client()

    unit = MagicMock()
    unit.id = "unit-001"
    unit.model_dump.return_value = {"id": "unit-001", "interface_name": "ge-0/0/0", "unit_number": 0}

    # cms_list() internally calls model.from_nautobot() on raw records,
    # returning pre-constructed model instances.  Return the right types.
    fam_summary = InterfaceFamilySummary.model_construct(
        id="fam-001", unit_id="unit-001", family_type="inet"
    )
    vrrp_summary = VRRPGroupSummary.model_construct(
        id="vrrp-001", family_id="fam-001", group_number=1
    )

    def mock_cms_list(client, endpoint, model, device=None, limit=0, **kwargs):
        if endpoint == "juniper_interface_families":
            resp = MagicMock()
            resp.results = [fam_summary]
            return resp
        elif endpoint == "juniper_interface_vrrp_groups":
            resp = MagicMock()
            resp.results = [vrrp_summary]
            return resp
        raise ValueError(f"Unexpected endpoint: {endpoint}")

    with patch("nautobot_mcp.cms.interfaces.list_interface_units", return_value=_mock_list_response(unit)) as mock_units, \
         patch("nautobot_mcp.cms.interfaces.cms_list", side_effect=mock_cms_list) as mock_cms, \
         patch.object(client.api.dcim.devices, "get", return_value=MagicMock(id="edge-01")):
        result, warnings = get_interface_detail(client, device="edge-01")

    assert isinstance(result, InterfaceDetailResponse)
    assert result.device_name == "edge-01"
    assert result.total_units == 1
    assert result.arp_entries == []  # include_arp=False by default
    assert len(result.units) == 1
    assert result.units[0]["family_count"] == 1
    assert result.units[0]["families"][0]["vrrp_group_count"] == 1
    assert warnings == []

    mock_units.assert_called_once_with(client, device="edge-01", limit=0)
    # Bulk family prefetch + bulk VRRP prefetch = 2 cms_list calls
    assert mock_cms.call_count == 2


def test_interface_detail_with_arp():
    """get_interface_detail(include_arp=True): should fetch and include ARP entries."""
    from nautobot_mcp.cms.interfaces import get_interface_detail

    client = _mock_client()

    unit = MagicMock()
    unit.id = "unit-002"
    unit.model_dump.return_value = {"id": "unit-002", "interface_name": "ge-0/0/1"}

    unit_obj = MagicMock()
    unit_obj.id = "unit-002"
    fam = MagicMock()
    fam.id = "fam-002"
    fam.interface_unit = unit_obj  # from_nautobot reads record.interface_unit.id
    fam.model_dump.return_value = {"id": "fam-002", "family_type": "inet"}

    arp_entry = MagicMock()
    arp_entry.model_dump.return_value = {"id": "arp-001", "mac_address": "aa:bb:cc:dd:ee:ff", "ip_address": "10.0.0.1/24"}

    def mock_cms_list(client, endpoint, model, device=None, limit=0, **kwargs):
        if endpoint == "juniper_interface_families":
            resp = MagicMock()
            resp.results = [fam]
            return resp
        elif endpoint == "juniper_interface_vrrp_groups":
            resp = MagicMock()
            resp.results = []
            return resp
        raise ValueError(f"Unexpected endpoint: {endpoint}")

    with patch("nautobot_mcp.cms.interfaces.list_interface_units", return_value=_mock_list_response(unit)), \
         patch("nautobot_mcp.cms.interfaces.cms_list", side_effect=mock_cms_list), \
         patch("nautobot_mcp.cms.arp.list_arp_entries", return_value=_mock_list_response(arp_entry)):
        result, warnings = get_interface_detail(client, device="edge-02", include_arp=True)

    assert result.total_units == 1
    assert len(result.arp_entries) == 1
    assert result.arp_entries[0]["mac_address"] == "aa:bb:cc:dd:ee:ff"
    assert warnings == []


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
        result, warnings = get_device_firewall_summary(client, device="fw-01")

    assert isinstance(result, FirewallSummaryResponse)
    assert result.device_name == "fw-01"
    assert result.total_filters == 1
    assert result.total_policers == 1
    assert len(result.filters) == 1
    assert len(result.policers) == 1
    assert warnings == []

    mock_filters.assert_called_once_with(client, device="fw-01", limit=0)
    mock_policers.assert_called_once_with(client, device="fw-01", limit=0)


def test_firewall_summary_detail():
    """get_device_firewall_summary(detail=True): filters include inlined terms via bulk prefetch."""
    from nautobot_mcp.cms.firewalls import get_device_firewall_summary
    from nautobot_mcp.cms.firewalls import cms_list

    client = _mock_client()
    fw_filter = _mock_fw_filter()
    policer = _mock_fw_policer()

    term = MagicMock()
    term.filter_id = "flt-001"
    term.model_dump.return_value = {"id": "term-001", "name": "accept-mgmt", "match_count": 1, "action_count": 1}

    pa_action = MagicMock()
    pa_action.policer_id = "pol-001"
    pa_action.model_dump.return_value = {"id": "pa-001", "action_type": "policer"}

    # Plan 01 bulk prefetch: detail=True calls cms_list(..., device=device_id) directly
    mock_terms_resp = _mock_list_response(term)
    mock_actions_resp = _mock_list_response(pa_action)

    def cms_list_side_effect(client_, endpoint, model, **kwargs):
        if endpoint == "juniper_firewall_terms":
            return mock_terms_resp
        if endpoint == "juniper_firewall_policer_actions":
            return mock_actions_resp
        raise RuntimeError(f"unexpected endpoint: {endpoint}")

    with patch("nautobot_mcp.cms.firewalls.list_firewall_filters", return_value=_mock_list_response(fw_filter)), \
         patch("nautobot_mcp.cms.firewalls.list_firewall_policers", return_value=_mock_list_response(policer)), \
         patch("nautobot_mcp.cms.firewalls.cms_list", side_effect=cms_list_side_effect):
        result, warnings = get_device_firewall_summary(client, device="fw-01", detail=True)

    assert result.total_filters == 1
    assert "terms" in result.filters[0]
    assert len(result.filters[0]["terms"]) == 1
    assert result.filters[0]["terms"][0]["name"] == "accept-mgmt"
    assert "actions" in result.policers[0]
    assert warnings == []


# ---------------------------------------------------------------------------
# Partial failure integration tests (Phase 19)
# ---------------------------------------------------------------------------


def test_bgp_summary_detail_address_family_enrichment_failure():
    """get_device_bgp_summary(detail=True): address-family failure → warning, neighbor still returned."""
    from nautobot_mcp.cms.routing import get_device_bgp_summary

    client = _mock_client()
    grp = _mock_bgp_group()
    nbr = _mock_bgp_neighbor(group_id=grp.id)
    pol = MagicMock()
    pol.model_dump.return_value = {"policy_name": "EXPORT"}

    with patch("nautobot_mcp.cms.routing.list_bgp_groups", return_value=_mock_list_response(grp)), \
         patch("nautobot_mcp.cms.routing.list_bgp_neighbors", return_value=_mock_list_response(nbr)), \
         patch("nautobot_mcp.cms.routing.list_bgp_address_families", side_effect=RuntimeError("AF timeout")), \
         patch("nautobot_mcp.cms.routing.list_bgp_policy_associations", return_value=_mock_list_response(pol)):
        result, warnings = get_device_bgp_summary(client, device="rtr-01", detail=True)

    # Partial result: neighbor still present
    assert result.total_neighbors == 1
    nbr_data = result.groups[0]["neighbors"][0]
    # AF failed → empty list, count 0
    assert nbr_data["address_families"] == []
    assert nbr_data["address_family_count"] == 0
    # Policy succeeded
    assert len(nbr_data["policy_associations"]) == 1
    # Warning recorded
    assert len(warnings) == 1
    assert warnings[0]["operation"] == "list_bgp_address_families"
    assert "AF timeout" in warnings[0]["error"]


def test_bgp_summary_detail_policy_enrichment_failure():
    """get_device_bgp_summary(detail=True): policy-association failure → warning, AF still returned."""
    from nautobot_mcp.cms.routing import get_device_bgp_summary

    client = _mock_client()
    grp = _mock_bgp_group()
    nbr = _mock_bgp_neighbor(group_id=grp.id)
    af = MagicMock()
    af.model_dump.return_value = {"address_family": "ipv4"}

    with patch("nautobot_mcp.cms.routing.list_bgp_groups", return_value=_mock_list_response(grp)), \
         patch("nautobot_mcp.cms.routing.list_bgp_neighbors", return_value=_mock_list_response(nbr)), \
         patch("nautobot_mcp.cms.routing.list_bgp_address_families", return_value=_mock_list_response(af)), \
         patch("nautobot_mcp.cms.routing.list_bgp_policy_associations", side_effect=RuntimeError("policy 503")):
        result, warnings = get_device_bgp_summary(client, device="rtr-01", detail=True)

    nbr_data = result.groups[0]["neighbors"][0]
    assert len(nbr_data["address_families"]) == 1
    assert nbr_data["policy_associations"] == []
    assert len(warnings) == 1
    assert warnings[0]["operation"] == "list_bgp_policy_associations"


def test_firewall_summary_filters_failure_policers_partial():
    """get_device_firewall_summary(): filters fail → policers returned, warning captured."""
    from nautobot_mcp.cms.firewalls import get_device_firewall_summary

    client = _mock_client()
    policer = _mock_fw_policer()

    with patch("nautobot_mcp.cms.firewalls.list_firewall_filters", side_effect=RuntimeError("filter 500")), \
         patch("nautobot_mcp.cms.firewalls.list_firewall_policers", return_value=_mock_list_response(policer)):
        result, warnings = get_device_firewall_summary(client, device="fw-01")

    # Filters failed but policers still returned
    assert isinstance(result, FirewallSummaryResponse)
    assert result.total_filters == 0
    assert result.total_policers == 1
    assert len(result.policers) == 1
    assert len(warnings) == 1
    assert warnings[0]["operation"] == "list_firewall_filters"


def test_firewall_summary_both_fail_raises():
    """get_device_firewall_summary(): both co-primaries fail → RuntimeError raised."""
    from nautobot_mcp.cms.firewalls import get_device_firewall_summary
    import pytest

    client = _mock_client()

    with patch("nautobot_mcp.cms.firewalls.list_firewall_filters", side_effect=RuntimeError("500")), \
         patch("nautobot_mcp.cms.firewalls.list_firewall_policers", side_effect=RuntimeError("503")):
        with pytest.raises(RuntimeError, match="Both primary queries failed"):
            get_device_firewall_summary(client, device="fw-01")


def test_firewall_summary_detail_term_enrichment_failure():
    """get_device_firewall_summary(detail=True): term enrichment failure → warning, filter still returned."""
    from nautobot_mcp.cms.firewalls import get_device_firewall_summary
    from nautobot_mcp.cms.firewalls import cms_list

    client = _mock_client()
    fw_filter = _mock_fw_filter()
    policer = _mock_fw_policer()
    pa_action = MagicMock()
    pa_action.policer_id = "pol-001"
    pa_action.model_dump.return_value = {"id": "pa-001"}

    mock_actions_resp = _mock_list_response(pa_action)

    def cms_list_side_effect(client_, endpoint, model, **kwargs):
        # Terms fail with RuntimeError → captured by WarningCollector
        if endpoint == "juniper_firewall_terms":
            raise RuntimeError("term timeout")
        if endpoint == "juniper_firewall_policer_actions":
            return mock_actions_resp
        raise RuntimeError(f"unexpected endpoint: {endpoint}")

    with patch("nautobot_mcp.cms.firewalls.list_firewall_filters", return_value=_mock_list_response(fw_filter)), \
         patch("nautobot_mcp.cms.firewalls.list_firewall_policers", return_value=_mock_list_response(policer)), \
         patch("nautobot_mcp.cms.firewalls.cms_list", side_effect=cms_list_side_effect):
        result, warnings = get_device_firewall_summary(client, device="fw-01", detail=True)

    assert result.total_filters == 1
    # terms failed → empty
    assert result.filters[0]["terms"] == []
    # policer actions succeeded
    assert len(result.policers[0]["actions"]) == 1
    assert len(warnings) == 1
    assert warnings[0]["operation"] == "bulk_terms_fetch"


def test_interface_detail_vrrp_enrichment_failure():
    """get_interface_detail(): Bulk VRRP prefetch failure → graceful degradation, families still returned."""
    from nautobot_mcp.cms.interfaces import get_interface_detail

    client = _mock_client()
    unit = MagicMock()
    unit.id = "unit-001"
    unit.model_dump.return_value = {"id": "unit-001", "interface_name": "ge-0/0/0"}

    fam = MagicMock()
    fam.id = "fam-001"
    fam.unit_id = "unit-001"
    fam.model_dump.return_value = {"id": "fam-001", "family_type": "inet"}

    def mock_cms_list(client, endpoint, model, device=None, limit=0, **kwargs):
        if endpoint == "juniper_interface_families":
            resp = MagicMock()
            resp.results = [fam]
            return resp
        elif endpoint == "juniper_interface_vrrp_groups":
            raise RuntimeError("vrrp unreachable")
        raise ValueError(f"Unexpected endpoint: {endpoint}")

    with patch("nautobot_mcp.cms.interfaces.list_interface_units", return_value=_mock_list_response(unit)), \
         patch("nautobot_mcp.cms.interfaces.cms_list", side_effect=mock_cms_list):
        result, warnings = get_interface_detail(client, device="edge-01")

    assert result.total_units == 1
    assert result.units[0]["families"][0]["vrrp_groups"] == []
    assert result.units[0]["families"][0]["vrrp_group_count"] == 0
    assert len(warnings) == 1
    assert warnings[0]["operation"] == "bulk_vrrp_fetch"
    assert "vrrp unreachable" in warnings[0]["error"]


def test_interface_detail_arp_enrichment_failure():
    """get_interface_detail(include_arp=True): ARP failure → warning, units still returned."""
    from nautobot_mcp.cms.interfaces import get_interface_detail

    client = _mock_client()
    unit = MagicMock()
    unit.id = "unit-003"
    unit.model_dump.return_value = {"id": "unit-003", "interface_name": "ge-0/0/2"}

    def mock_cms_list(client, endpoint, model, device=None, limit=0, **kwargs):
        if endpoint == "juniper_interface_families":
            return _mock_list_response()  # no families
        elif endpoint == "juniper_interface_vrrp_groups":
            return _mock_list_response()  # no VRRP
        raise ValueError(f"Unexpected endpoint: {endpoint}")

    with patch("nautobot_mcp.cms.interfaces.list_interface_units", return_value=_mock_list_response(unit)), \
         patch("nautobot_mcp.cms.interfaces.cms_list", side_effect=mock_cms_list), \
         patch("nautobot_mcp.cms.arp.list_arp_entries", side_effect=RuntimeError("arp timeout")):
        result, warnings = get_interface_detail(client, device="edge-03", include_arp=True)

    assert result.total_units == 1
    assert result.arp_entries == []
    assert len(warnings) == 1
    assert warnings[0]["operation"] == "list_arp_entries"
    assert "arp timeout" in warnings[0]["error"]


# ---------------------------------------------------------------------------
# RSP-01: detail=False summary mode for interface_detail
# ---------------------------------------------------------------------------


def test_interface_detail_summary_mode_strips_nested_arrays():
    """RSP-01: get_interface_detail(detail=False) returns family_count but no families/vrrp_groups."""
    from nautobot_mcp.cms.interfaces import get_interface_detail
    from nautobot_mcp.models.cms.interfaces import InterfaceFamilySummary, VRRPGroupSummary

    client = _mock_client()
    unit = MagicMock()
    unit.id = "unit-001"
    unit.model_dump.return_value = {"id": "unit-001", "interface_name": "ge-0/0/0"}

    # cms_list() internally calls model.from_nautobot() on raw records.
    fam_summary = InterfaceFamilySummary.model_construct(
        id="fam-001", unit_id="unit-001", family_type="inet"
    )
    vrrp_summary = VRRPGroupSummary.model_construct(
        id="vrrp-001", family_id="fam-001", group_number=1
    )

    def mock_cms_list(client, endpoint, model, device=None, limit=0, **kwargs):
        if endpoint == "juniper_interface_families":
            resp = MagicMock()
            resp.results = [fam_summary]
            return resp
        elif endpoint == "juniper_interface_vrrp_groups":
            resp = MagicMock()
            resp.results = [vrrp_summary]
            return resp
        raise ValueError(f"Unexpected endpoint: {endpoint}")

    with patch(
        "nautobot_mcp.cms.interfaces.list_interface_units",
        return_value=_mock_list_response(unit),
    ) as mock_units, patch(
        "nautobot_mcp.cms.interfaces.cms_list",
        side_effect=mock_cms_list,
    ) as mock_cms, patch.object(client.api.dcim.devices, "get", return_value=MagicMock(id="edge-01")):
        result, warnings = get_interface_detail(client, device="edge-01", detail=False)

    assert isinstance(result, InterfaceDetailResponse)
    assert result.device_name == "edge-01"
    assert result.total_units == 1
    assert len(result.units) == 1
    assert result.units[0]["families"] == [], (
        "families[] must be stripped (empty list) in detail=False mode"
    )
    assert "family_count" in result.units[0], "family_count must be present in summary mode"
    assert result.units[0]["family_count"] == 1
    assert "vrrp_group_count" in result.units[0], "vrrp_group_count must be present in summary mode"
    assert result.units[0]["vrrp_group_count"] == 1, "vrrp_group_count should reflect actual VRRP count"
    # Bulk family + bulk VRRP prefetch = 2 cms_list calls (no per-family HTTP calls)
    assert mock_cms.call_count == 2
    assert warnings == []


def test_interface_detail_summary_mode_does_not_affect_arp():
    """RSP-01: detail=False does not affect include_arp behavior (ARP controlled by include_arp)."""
    from nautobot_mcp.cms.interfaces import get_interface_detail

    client = _mock_client()
    unit = MagicMock()
    unit.id = "unit-002"
    unit.model_dump.return_value = {"id": "unit-002", "interface_name": "ge-0/0/1"}

    fam = MagicMock()
    fam.id = "fam-002"
    fam.unit_id = "unit-002"
    fam.model_dump.return_value = {"id": "fam-002", "family_type": "inet"}

    arp_entry = MagicMock()
    arp_entry.model_dump.return_value = {
        "id": "arp-001",
        "mac_address": "aa:bb:cc:dd:ee:ff",
        "ip_address": "10.0.0.1/24",
    }

    def mock_cms_list(client, endpoint, model, device=None, limit=0, **kwargs):
        if endpoint == "juniper_interface_families":
            resp = MagicMock()
            resp.results = [fam]
            return resp
        elif endpoint == "juniper_interface_vrrp_groups":
            resp = MagicMock()
            resp.results = []
            return resp
        raise ValueError(f"Unexpected endpoint: {endpoint}")

    with patch(
        "nautobot_mcp.cms.interfaces.list_interface_units",
        return_value=_mock_list_response(unit),
    ), patch(
        "nautobot_mcp.cms.interfaces.cms_list",
        side_effect=mock_cms_list,
    ), patch(
        "nautobot_mcp.cms.arp.list_arp_entries",
        return_value=_mock_list_response(arp_entry),
    ):
        result, warnings = get_interface_detail(
            client, device="edge-02", include_arp=True, detail=False
        )

    assert result.units[0]["families"] == [], "families[] still stripped when include_arp=True"
    assert len(result.arp_entries) == 1, "ARP entries should be present when include_arp=True"
    assert result.arp_entries[0]["mac_address"] == "aa:bb:cc:dd:ee:ff"


def test_interface_detail_detail_true_unchanged():
    """RSP-01: get_interface_detail(detail=True) behavior is unchanged from default."""
    from nautobot_mcp.cms.interfaces import get_interface_detail
    from nautobot_mcp.models.cms.interfaces import InterfaceFamilySummary, VRRPGroupSummary

    client = _mock_client()
    unit = MagicMock()
    unit.id = "unit-003"
    unit.model_dump.return_value = {"id": "unit-003", "interface_name": "ge-0/0/2"}

    # cms_list() internally calls model.from_nautobot() on raw records.
    fam_summary = InterfaceFamilySummary.model_construct(
        id="fam-003", unit_id="unit-003", family_type="inet6"
    )
    vrrp_summary = VRRPGroupSummary.model_construct(
        id="vrrp-003", family_id="fam-003", group_number=10
    )

    def mock_cms_list(client, endpoint, model, device=None, limit=0, **kwargs):
        if endpoint == "juniper_interface_families":
            resp = MagicMock()
            resp.results = [fam_summary]
            return resp
        elif endpoint == "juniper_interface_vrrp_groups":
            resp = MagicMock()
            resp.results = [vrrp_summary]
            return resp
        raise ValueError(f"Unexpected endpoint: {endpoint}")

    with patch(
        "nautobot_mcp.cms.interfaces.list_interface_units",
        return_value=_mock_list_response(unit),
    ) as mock_units, patch(
        "nautobot_mcp.cms.interfaces.cms_list",
        side_effect=mock_cms_list,
    ) as mock_cms, patch.object(client.api.dcim.devices, "get", return_value=MagicMock(id="edge-03")):
        result, warnings = get_interface_detail(client, device="edge-03", detail=True)

    assert isinstance(result, InterfaceDetailResponse)
    assert len(result.units) == 1
    # In detail=True mode, families should NOT be stripped
    assert len(result.units[0]["families"]) == 1, "families[] must be populated in detail=True"
    assert result.units[0]["families"][0]["vrrp_group_count"] == 1
    assert "vrrp_groups" in result.units[0]["families"][0]
    # Bulk family + bulk VRRP prefetch = 2 cms_list calls (no per-family HTTP calls)
    assert mock_cms.call_count == 2


# ---------------------------------------------------------------------------
# RSP-03: limit parameter for all 4 composites
# ---------------------------------------------------------------------------


def test_bgp_summary_limit_caps_groups_and_neighbors():
    """RSP-03: bgp_summary(limit=N) caps groups[] and neighbors[] independently."""
    from nautobot_mcp.cms.routing import get_device_bgp_summary

    client = _mock_client()
    grps = [_mock_bgp_group(id_=f"grp-{i}") for i in range(5)]
    nbrs = [_mock_bgp_neighbor(id_=f"nbr-{i}", group_id="grp-0") for i in range(5)]

    with patch(
        "nautobot_mcp.cms.routing.list_bgp_groups",
        return_value=_mock_list_response(*grps),
    ), patch(
        "nautobot_mcp.cms.routing.list_bgp_neighbors",
        return_value=_mock_list_response(*nbrs),
    ):
        result, warnings = get_device_bgp_summary(client, device="rtr-01", limit=3)

    assert len(result.groups) <= 3, f"groups[] must be capped at 3, got {len(result.groups)}"
    for grp in result.groups:
        assert len(grp.get("neighbors", [])) <= 3, (
            f"neighbors[] per group must be capped at 3, got {len(grp.get('neighbors', []))}"
        )


def test_routing_table_limit_caps_routes():
    """RSP-03: routing_table(limit=N) caps routes[]."""
    from nautobot_mcp.cms.routing import get_device_routing_table

    client = _mock_client()
    routes = [_mock_static_route(id_=f"rt-{i}", destination=f"10.{i}.0.0/16") for i in range(5)]

    with patch(
        "nautobot_mcp.cms.routing.list_static_routes",
        return_value=_mock_list_response(*routes),
    ):
        result, warnings = get_device_routing_table(client, device="rtr-01", limit=2)

    assert len(result.routes) <= 2, f"routes[] must be capped at 2, got {len(result.routes)}"


def test_firewall_summary_limit_caps_filters_and_policers():
    """RSP-03: firewall_summary(limit=N) caps filters[] and policers[] independently."""
    from nautobot_mcp.cms.firewalls import get_device_firewall_summary

    client = _mock_client()
    fw_filters = [_mock_fw_filter(id_=f"fw-{i}") for i in range(5)]
    fw_policers = [_mock_fw_policer(id_=f"pol-{i}") for i in range(5)]

    with patch(
        "nautobot_mcp.cms.firewalls.list_firewall_filters",
        return_value=_mock_list_response(*fw_filters),
    ), patch(
        "nautobot_mcp.cms.firewalls.list_firewall_policers",
        return_value=_mock_list_response(*fw_policers),
    ):
        result, warnings = get_device_firewall_summary(client, device="fw-01", limit=2)

    assert len(result.filters) <= 2, f"filters[] must be capped at 2, got {len(result.filters)}"
    assert len(result.policers) <= 2, f"policers[] must be capped at 2, got {len(result.policers)}"


def test_interface_detail_limit_caps_units_and_families():
    """RSP-03: interface_detail(limit=N) caps units[] and caps families[] per unit."""
    from nautobot_mcp.cms.interfaces import get_interface_detail

    client = _mock_client()
    units = [
        MagicMock(
            id=f"unit-{i}",
            model_dump=lambda i=i: {"id": f"unit-{i}", "interface_name": f"ge-0/0/{i}"},
        )
        for i in range(5)
    ]
    # Give each unit 3 families
    families_per_unit = [
        MagicMock(
            id=f"fam-{j}",
            model_dump=lambda j=j: {"id": f"fam-{j}", "family_type": "inet"},
        )
        for j in range(3)
    ]
    with patch(
        "nautobot_mcp.cms.interfaces.list_interface_units",
        return_value=_mock_list_response(*units),
    ), patch(
        "nautobot_mcp.cms.interfaces.list_interface_families",
        return_value=_mock_list_response(*families_per_unit),
    ), patch(
        "nautobot_mcp.cms.interfaces.list_vrrp_groups",
        return_value=_mock_list_response(),
    ):
        result, warnings = get_interface_detail(client, device="edge-01", limit=2)

    assert len(result.units) <= 2, f"units[] must be capped at 2, got {len(result.units)}"
    for unit in result.units:
        assert len(unit.get("families", [])) <= 2, (
            f"families[] per unit must be capped at 2, got {len(unit.get('families', []))}"
        )
