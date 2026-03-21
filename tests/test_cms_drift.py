"""Unit tests for CMS drift verification engine (Phase 13).

Covers:
- CMSDriftReport Pydantic model defaults and structure
- _serialize_nexthops helper: ordering, CIDR stripping, edge cases
- _build_cms_summary helper: zero-drift counts, mixed-section counts
- LiveBGPAdapter.load(): valid, missing peer_ip, non-dict entries
- LiveStaticRouteAdapter.load(): valid, nexthop formats, bad types
- compare_bgp_neighbors(): no drift, missing in Nautobot, extra in Nautobot, changed fields
- compare_static_routes(): no drift, missing in Nautobot, extra in Nautobot, changed nexthops
- Edge cases: empty live data, CMS no records
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from nautobot_mcp.cms.cms_drift import (
    LiveBGPAdapter,
    LiveStaticRouteAdapter,
    SyncBGPNeighbor,
    SyncStaticRoute,
    _build_cms_summary,
    _serialize_nexthops,
    compare_bgp_neighbors,
    compare_static_routes,
)
from nautobot_mcp.models.cms.cms_drift import CMSDriftReport
from nautobot_mcp.models.verification import DriftItem, DriftSection


# ---------------------------------------------------------------------------
# Helper: create a mock BGPNeighborSummary-like object for CMSBGPAdapter
# ---------------------------------------------------------------------------


def _make_nbr_record(peer_ip: str, peer_as: int, group_id: str, local_address: str = ""):
    """Build a minimal BGPNeighborSummary-like mock for CMS adapter tests."""
    r = MagicMock()
    r.peer_ip = peer_ip
    r.peer_as = peer_as
    r.group_id = group_id
    r.local_address = local_address
    return r


def _make_route_record(destination: str, nexthops=None, preference=5, metric=0, routing_instance=""):
    """Build a minimal StaticRouteSummary-like mock for CMSStaticRouteAdapter tests."""
    r = MagicMock()
    r.destination = destination
    r.preference = preference
    r.metric = metric
    r.routing_instance_name = routing_instance
    # Build nexthops inline mocks
    nh_mocks = []
    for ip in (nexthops or []):
        nh = MagicMock()
        nh.ip_address = ip
        nh_mocks.append(nh)
    r.nexthops = nh_mocks
    r.qualified_nexthops = []
    return r


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestCMSDriftReport:
    """Test CMSDriftReport Pydantic model structure and defaults."""

    def test_default_sections_empty(self):
        """Newly created report has empty drift sections."""
        report = CMSDriftReport(device="test-rtr-01")
        assert report.device == "test-rtr-01"
        assert report.bgp_neighbors.missing == []
        assert report.bgp_neighbors.extra == []
        assert report.bgp_neighbors.changed == []
        assert report.static_routes.missing == []
        assert report.static_routes.extra == []
        assert report.static_routes.changed == []

    def test_default_summary_empty(self):
        """Summary defaults to empty dict."""
        report = CMSDriftReport(device="test-rtr-01")
        assert report.summary == {}

    def test_default_warnings_empty(self):
        """Warnings defaults to empty list."""
        report = CMSDriftReport(device="test-rtr-01")
        assert report.warnings == []

    def test_model_dump_serializable(self):
        """model_dump() returns JSON-serializable dict."""
        report = CMSDriftReport(device="test-rtr-01")
        data = report.model_dump()
        assert isinstance(data, dict)
        assert data["device"] == "test-rtr-01"
        assert "bgp_neighbors" in data
        assert "static_routes" in data


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestSerializeNexthops:
    """Test _serialize_nexthops IP serialization helper."""

    def test_bare_strings_sorted(self):
        """Plain IP strings are sorted alphabetically."""
        result = _serialize_nexthops(["10.0.0.3", "10.0.0.1", "10.0.0.2"])
        assert result == "10.0.0.1,10.0.0.2,10.0.0.3"

    def test_cidr_stripped(self):
        """CIDR notation is stripped before sorting."""
        result = _serialize_nexthops(["10.0.0.1/32", "10.0.0.2/32"])
        assert result == "10.0.0.1,10.0.0.2"

    def test_dict_ip_address_key(self):
        """Dicts with 'ip_address' key are extracted."""
        result = _serialize_nexthops([{"ip_address": "10.0.0.1/32"}, {"ip_address": "10.0.0.2/32"}])
        assert result == "10.0.0.1,10.0.0.2"

    def test_dict_address_key(self):
        """Dicts with 'address' key (fallback) are extracted."""
        result = _serialize_nexthops([{"address": "192.168.1.1"}])
        assert result == "192.168.1.1"

    def test_empty_list(self):
        """Empty nexthop list returns empty string."""
        result = _serialize_nexthops([])
        assert result == ""

    def test_deduplication_order_independent(self):
        """Different input order produces same sorted output."""
        r1 = _serialize_nexthops(["10.0.0.2", "10.0.0.1"])
        r2 = _serialize_nexthops(["10.0.0.1", "10.0.0.2"])
        assert r1 == r2


class TestBuildCMSSummary:
    """Test _build_cms_summary count aggregation."""

    def test_zero_drift(self):
        """Empty sections produce zero counts."""
        report = CMSDriftReport(device="rtr")
        summary = _build_cms_summary(report)
        assert summary["total_drifts"] == 0
        assert summary["by_type"]["bgp_neighbors"]["total"] == 0
        assert summary["by_type"]["static_routes"]["total"] == 0

    def test_counts_missing_extra_changed(self):
        """Counts missing, extra, and changed items correctly."""
        report = CMSDriftReport(device="rtr")
        report.bgp_neighbors.missing = [DriftItem(name="10.0.0.1", status="missing_in_nautobot")]
        report.bgp_neighbors.changed = [DriftItem(name="10.0.0.2", status="changed")]
        report.static_routes.extra = [DriftItem(name="192.168.1.0/24", status="missing_on_device")]

        summary = _build_cms_summary(report)
        assert summary["total_drifts"] == 3
        assert summary["by_type"]["bgp_neighbors"]["missing"] == 1
        assert summary["by_type"]["bgp_neighbors"]["changed"] == 1
        assert summary["by_type"]["static_routes"]["extra"] == 1


# ---------------------------------------------------------------------------
# Adapter unit tests
# ---------------------------------------------------------------------------


class TestLiveBGPAdapter:
    """Test LiveBGPAdapter.load() from raw dicts."""

    def test_loads_valid_neighbor(self):
        """Single valid neighbor dict produces one SyncBGPNeighbor."""
        adapter = LiveBGPAdapter()
        adapter.live_data = [
            {"peer_ip": "10.0.0.1", "peer_as": 65001, "local_address": "10.0.0.2", "group_name": "EXTERNAL"}
        ]
        adapter.load()
        nbr = adapter.get(SyncBGPNeighbor, "10.0.0.1")
        assert nbr.peer_as == 65001
        assert nbr.group_name == "EXTERNAL"

    def test_skips_entry_without_peer_ip(self):
        """Entry missing peer_ip is skipped."""
        adapter = LiveBGPAdapter()
        adapter.live_data = [{"peer_as": 65001}]
        adapter.load()
        assert len(list(adapter.get_all(SyncBGPNeighbor))) == 0

    def test_skips_non_dict_entries(self):
        """Non-dict entries (e.g., None, str) are skipped."""
        adapter = LiveBGPAdapter()
        adapter.live_data = [None, "bad-entry", 42]
        adapter.load()
        assert len(list(adapter.get_all(SyncBGPNeighbor))) == 0

    def test_handles_bad_peer_as(self):
        """Non-numeric peer_as defaults to 0."""
        adapter = LiveBGPAdapter()
        adapter.live_data = [{"peer_ip": "10.0.0.1", "peer_as": "not-a-number"}]
        adapter.load()
        nbr = adapter.get(SyncBGPNeighbor, "10.0.0.1")
        assert nbr.peer_as == 0


class TestLiveStaticRouteAdapter:
    """Test LiveStaticRouteAdapter.load() from raw dicts."""

    def test_loads_valid_route(self):
        """Single valid route dict produces one SyncStaticRoute."""
        adapter = LiveStaticRouteAdapter()
        adapter.live_data = [
            {
                "destination": "192.168.1.0/24",
                "nexthops": ["10.0.0.1", "10.0.0.2"],
                "preference": 5,
                "metric": 0,
                "routing_instance": "default",
            }
        ]
        adapter.load()
        route = adapter.get(SyncStaticRoute, "192.168.1.0/24")
        assert route.nexthops_str == "10.0.0.1,10.0.0.2"
        assert route.preference == 5

    def test_skips_entry_without_destination(self):
        """Entry missing destination is skipped."""
        adapter = LiveStaticRouteAdapter()
        adapter.live_data = [{"nexthops": ["10.0.0.1"], "preference": 5}]
        adapter.load()
        assert len(list(adapter.get_all(SyncStaticRoute))) == 0

    def test_nexthops_sorted(self):
        """Nexthops are sorted for consistent comparison."""
        adapter = LiveStaticRouteAdapter()
        adapter.live_data = [{"destination": "0.0.0.0/0", "nexthops": ["10.0.0.3", "10.0.0.1"]}]
        adapter.load()
        route = adapter.get(SyncStaticRoute, "0.0.0.0/0")
        assert route.nexthops_str == "10.0.0.1,10.0.0.3"

    def test_handles_none_nexthops(self):
        """None nexthops field defaults to empty string."""
        adapter = LiveStaticRouteAdapter()
        adapter.live_data = [{"destination": "10.0.0.0/8", "nexthops": None}]
        adapter.load()
        route = adapter.get(SyncStaticRoute, "10.0.0.0/8")
        assert route.nexthops_str == ""


# ---------------------------------------------------------------------------
# compare_bgp_neighbors integration tests
# ---------------------------------------------------------------------------


class TestCompareBGPNeighbors:
    """Integration tests for compare_bgp_neighbors using mocked CMS calls."""

    def _mock_client_bgp(self, group_records, neighbor_records):
        """Build a mocked NautobotClient for BGP comparisons."""
        mock_client = MagicMock()
        return mock_client

    @patch("nautobot_mcp.cms.cms_drift.list_bgp_groups")
    @patch("nautobot_mcp.cms.cms_drift.list_bgp_neighbors")
    def test_no_drift(self, mock_list_nbrs, mock_list_groups):
        """Identical live and CMS data → zero drifts."""
        # CMS has one group and one neighbor
        grp = MagicMock()
        grp.id = "grp-001"
        grp.name = "EXTERNAL"
        mock_list_groups.return_value = MagicMock(results=[grp])

        nbr = _make_nbr_record("10.0.0.1", 65001, "grp-001", "10.0.0.2")
        mock_list_nbrs.return_value = MagicMock(results=[nbr])

        live = [{"peer_ip": "10.0.0.1", "peer_as": 65001, "local_address": "10.0.0.2", "group_name": "EXTERNAL"}]
        report = compare_bgp_neighbors(MagicMock(), "test-rtr-01", live)

        assert report.summary["total_drifts"] == 0

    @patch("nautobot_mcp.cms.cms_drift.list_bgp_groups")
    @patch("nautobot_mcp.cms.cms_drift.list_bgp_neighbors")
    def test_missing_in_nautobot(self, mock_list_nbrs, mock_list_groups):
        """Neighbor on device but not in CMS → missing item in report."""
        mock_list_groups.return_value = MagicMock(results=[])
        mock_list_nbrs.return_value = MagicMock(results=[])

        live = [{"peer_ip": "10.0.0.99", "peer_as": 65099}]
        report = compare_bgp_neighbors(MagicMock(), "test-rtr-01", live)

        assert report.summary["by_type"]["bgp_neighbors"]["missing"] == 1
        assert any(item.name == "10.0.0.99" for item in report.bgp_neighbors.missing)

    @patch("nautobot_mcp.cms.cms_drift.list_bgp_groups")
    @patch("nautobot_mcp.cms.cms_drift.list_bgp_neighbors")
    def test_extra_in_nautobot(self, mock_list_nbrs, mock_list_groups):
        """Neighbor in CMS but not on device → extra item in report."""
        grp = MagicMock()
        grp.id = "grp-001"
        grp.name = "EXTERNAL"
        mock_list_groups.return_value = MagicMock(results=[grp])

        nbr = _make_nbr_record("10.0.0.1", 65001, "grp-001")
        mock_list_nbrs.return_value = MagicMock(results=[nbr])

        # Live data is empty — nothing on device
        report = compare_bgp_neighbors(MagicMock(), "test-rtr-01", [])

        assert report.summary["by_type"]["bgp_neighbors"]["extra"] == 1
        assert any(item.name == "10.0.0.1" for item in report.bgp_neighbors.extra)

    @patch("nautobot_mcp.cms.cms_drift.list_bgp_groups")
    @patch("nautobot_mcp.cms.cms_drift.list_bgp_neighbors")
    def test_changed_peer_as(self, mock_list_nbrs, mock_list_groups):
        """Same peer_ip but different peer_as → changed item in report."""
        grp = MagicMock()
        grp.id = "grp-001"
        grp.name = "EXTERNAL"
        mock_list_groups.return_value = MagicMock(results=[grp])

        nbr = _make_nbr_record("10.0.0.1", 65001, "grp-001")
        mock_list_nbrs.return_value = MagicMock(results=[nbr])

        # Live has peer_as 65999 (differs from CMS 65001)
        live = [{"peer_ip": "10.0.0.1", "peer_as": 65999}]
        report = compare_bgp_neighbors(MagicMock(), "test-rtr-01", live)

        assert report.summary["by_type"]["bgp_neighbors"]["changed"] == 1
        changed_item = report.bgp_neighbors.changed[0]
        assert "peer_as" in changed_item.changed_fields

    @patch("nautobot_mcp.cms.cms_drift.list_bgp_groups")
    @patch("nautobot_mcp.cms.cms_drift.list_bgp_neighbors")
    def test_empty_live_data(self, mock_list_nbrs, mock_list_groups):
        """Empty live data with CMS records → all CMS records appear as extra."""
        grp = MagicMock()
        grp.id = "grp-001"
        grp.name = "EXTERNAL"
        mock_list_groups.return_value = MagicMock(results=[grp])

        nbr1 = _make_nbr_record("10.0.0.1", 65001, "grp-001")
        nbr2 = _make_nbr_record("10.0.0.2", 65002, "grp-001")
        mock_list_nbrs.return_value = MagicMock(results=[nbr1, nbr2])

        report = compare_bgp_neighbors(MagicMock(), "test-rtr-01", [])
        assert report.summary["by_type"]["bgp_neighbors"]["extra"] == 2


# ---------------------------------------------------------------------------
# compare_static_routes integration tests
# ---------------------------------------------------------------------------


class TestCompareStaticRoutes:
    """Integration tests for compare_static_routes using mocked CMS calls."""

    @patch("nautobot_mcp.cms.cms_drift.list_static_routes")
    def test_no_drift(self, mock_list_routes):
        """Identical live and CMS routes → zero drifts."""
        route = _make_route_record("192.168.1.0/24", nexthops=["10.0.0.1"], preference=5)
        mock_list_routes.return_value = MagicMock(results=[route])

        live = [{"destination": "192.168.1.0/24", "nexthops": ["10.0.0.1"], "preference": 5, "metric": 0}]
        report = compare_static_routes(MagicMock(), "test-rtr-01", live)

        assert report.summary["total_drifts"] == 0

    @patch("nautobot_mcp.cms.cms_drift.list_static_routes")
    def test_missing_in_nautobot(self, mock_list_routes):
        """Route on device but not in CMS → missing item in report."""
        mock_list_routes.return_value = MagicMock(results=[])

        live = [{"destination": "10.99.0.0/24", "nexthops": ["10.0.0.1"]}]
        report = compare_static_routes(MagicMock(), "test-rtr-01", live)

        assert report.summary["by_type"]["static_routes"]["missing"] == 1
        assert any(item.name == "10.99.0.0/24" for item in report.static_routes.missing)

    @patch("nautobot_mcp.cms.cms_drift.list_static_routes")
    def test_extra_in_nautobot(self, mock_list_routes):
        """Route in CMS but not on device → extra item in report."""
        route = _make_route_record("10.99.0.0/24", nexthops=["10.0.0.1"])
        mock_list_routes.return_value = MagicMock(results=[route])

        # Live is empty
        report = compare_static_routes(MagicMock(), "test-rtr-01", [])

        assert report.summary["by_type"]["static_routes"]["extra"] == 1
        assert any(item.name == "10.99.0.0/24" for item in report.static_routes.extra)

    @patch("nautobot_mcp.cms.cms_drift.list_static_routes")
    def test_changed_nexthops(self, mock_list_routes):
        """Same destination but different nexthops → changed item in report."""
        # CMS has one nexthop: 10.0.0.1
        route = _make_route_record("192.168.1.0/24", nexthops=["10.0.0.1"])
        mock_list_routes.return_value = MagicMock(results=[route])

        # Live has a different nexthop: 10.0.0.99
        live = [{"destination": "192.168.1.0/24", "nexthops": ["10.0.0.99"], "preference": 5, "metric": 0}]
        report = compare_static_routes(MagicMock(), "test-rtr-01", live)

        assert report.summary["by_type"]["static_routes"]["changed"] == 1
        changed = report.static_routes.changed[0]
        assert "nexthops_str" in changed.changed_fields

    @patch("nautobot_mcp.cms.cms_drift.list_static_routes")
    def test_nexthop_ordering_independent(self, mock_list_routes):
        """Different nexthop order on device vs CMS → no drift (same IPs)."""
        # CMS has nexthops in one order
        route = _make_route_record("0.0.0.0/0", nexthops=["10.0.0.1", "10.0.0.2"])
        mock_list_routes.return_value = MagicMock(results=[route])

        # Live has them in a different order
        live = [{"destination": "0.0.0.0/0", "nexthops": ["10.0.0.2", "10.0.0.1"]}]
        report = compare_static_routes(MagicMock(), "test-rtr-01", live)

        assert report.summary["total_drifts"] == 0

    @patch("nautobot_mcp.cms.cms_drift.list_static_routes")
    def test_empty_live_data(self, mock_list_routes):
        """Empty live data with two CMS routes → both appear as extra."""
        r1 = _make_route_record("192.168.1.0/24", nexthops=["10.0.0.1"])
        r2 = _make_route_record("10.0.0.0/8", nexthops=["10.0.0.2"])
        mock_list_routes.return_value = MagicMock(results=[r1, r2])

        report = compare_static_routes(MagicMock(), "test-rtr-01", [])
        assert report.summary["by_type"]["static_routes"]["extra"] == 2

    @patch("nautobot_mcp.cms.cms_drift.list_static_routes")
    def test_summary_structure(self, mock_list_routes):
        """Summary always contains expected keys."""
        mock_list_routes.return_value = MagicMock(results=[])
        report = compare_static_routes(MagicMock(), "test-rtr-01", [])

        assert "total_drifts" in report.summary
        assert "by_type" in report.summary
        assert "bgp_neighbors" in report.summary["by_type"]
        assert "static_routes" in report.summary["by_type"]
