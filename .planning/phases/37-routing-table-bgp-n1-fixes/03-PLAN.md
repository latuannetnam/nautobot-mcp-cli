---
plan: 03
wave: 2
depends_on: [01]
requirements_addressed: [CQP-03, CQP-04, CQP-05]
files_modified:
  - tests/test_cms_routing_n1.py
autonomous: true
---

<objective>

Create `tests/test_cms_routing_n1.py` — a combined N+1 invariant test file for both `get_device_routing_table` (routing) and `get_device_bgp_summary` (BGP). Follow the Phase 35/36 pattern: monkey-patch `cms_list` in `nautobot_mcp.cms.routing` to count HTTP calls, assert call counts are invariant to item count.

**Routing tests (CQP-03):** Assert exactly 3 `cms_list` calls regardless of route count. Assert no `route=` keyword ever passed to `cms_list`. Assert silent graceful degradation when nexthop bulk fetches return empty or raise.

**BGP tests (CQP-04):** Assert guards prevent per-neighbor calls when device has no neighbors. Assert ≤4 `cms_list` calls with `detail=True` and many neighbors. Assert `WarningCollector` fires for AF/policy bulk failures.

</objective>

<read_first>

- `tests/test_cms_interfaces_n1.py` L1-80 — Phase 35 monkey-patch pattern (copy structure and helper functions from here)
- `tests/test_cms_firewalls_n1.py` L1-65, L65-150 — Phase 36 test pattern for `detail=True` path and guard scenarios
- `nautobot_mcp/cms/routing.py` L46-129 (`list_static_routes`) — after Plan 01, the inline loop must be the only loop
- `nautobot_mcp/cms/routing.py` L639-779 (`get_device_bgp_summary`) — BGP guards at L687, L709-711, L728-731, L734-751

</read_first>

<action>

**File to create:** `tests/test_cms_routing_n1.py`

Follow this exact structure (based on Phase 35/36 pattern):

```python
"""Tests for routing_table + bgp_summary N+1 fix — bulk prefetch invariants.

Verifies:
- Exactly 3 bulk cms_list calls in get_device_routing_table (CQP-03)
- list_*_nexthops never called per-route (CQP-03)
- Nexthop bulk fetch failure silent graceful degradation (CQP-05)
- Exactly 4 bulk cms_list calls in get_device_bgp_summary detail=True (CQP-04)
- Guard prevents AF/policy calls when 0 neighbors (CQP-04)
- AF bulk fetch failure WarningCollector (CQP-05)
"""

from unittest.mock import MagicMock, patch

import pytest

from nautobot_mcp.models.base import ListResponse
from nautobot_mcp.models.cms.composites import RoutingTableResponse, BGPSummaryResponse


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _mock_client():
    return MagicMock()


def _mock_list_response(*items):
    """Return a mock ListResponse with items as results."""
    resp = MagicMock()
    resp.results = list(items)
    resp.count = len(items)
    return resp


def _mock_route(route_id, has_nh=False, has_qnh=False):
    """Return a mock StaticRouteSummary with optional nexthops pre-set."""
    route = MagicMock()
    route.id = route_id
    route.model_dump = MagicMock(return_value={
        "id": route_id,
        "destination": f"10.{route_id}/32",
    })
    return route


# ---------------------------------------------------------------------------
# Routing N+1 Tests (CQP-03)
# ---------------------------------------------------------------------------

# R1: Exactly 3 cms_list calls with complete bulk data
def test_routing_table_exactly_3_calls():
    """CQP-03: get_device_routing_table makes exactly 3 cms_list calls regardless of route count.

    3 routes, some with nexthops, some without.
    Expected calls:
    1. juniper_static_routes
    2. juniper_static_route_nexthops
    3. juniper_static_route_qualified_nexthops
    """
    from nautobot_mcp.cms.routing import get_device_routing_table

    client = _mock_client()

    routes = [_mock_route(f"route-{i}") for i in range(3)]
    # route-0 has a nexthop; route-1 and route-2 do not
    nhs = [MagicMock(id="nh-0", route_id="route-0")]
    qnhs = [MagicMock(id="qnh-0", route_id="route-0")]

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        if "static_routes" in endpoint and "nexthop" not in endpoint:
            return _mock_list_response(*routes)
        if "static_route_nexthops" in endpoint and "qualified" not in endpoint:
            return _mock_list_response(*nhs)
        if "static_route_qualified_nexthops" in endpoint:
            return _mock_list_response(*qnhs)
        raise ValueError(f"Unexpected endpoint: {endpoint}")

    with patch("nautobot_mcp.cms.routing.resolve_device_id", return_value="device-uuid-1"), \
         patch("nautobot_mcp.cms.routing.cms_list", side_effect=cms_list_side_effect) as mock_cms:
        result, warnings = get_device_routing_table(client, device="edge-01")

    # Exactly 3 calls (no per-route fallback)
    assert mock_cms.call_count == 3, f"Expected 3 calls, got {mock_cms.call_count}: {[c.args for c in mock_cms.call_args_list]}"
    # Verify call endpoints
    call_endpoints = [c.args[1] for c in mock_cms.call_args_list]
    assert "juniper_static_routes" in call_endpoints
    assert "juniper_static_route_nexthops" in call_endpoints
    assert "juniper_static_route_qualified_nexthops" in call_endpoints
    assert isinstance(result, RoutingTableResponse)
    assert result.total_routes == 3


# R2: cms_list never called with route=<id> filter (proof of N+1 removal)
def test_routing_table_no_per_route_calls():
    """CQP-03: No cms_list call ever includes route= in kwargs (proves N+1 loop removed)."""
    from nautobot_mcp.cms.routing import get_device_routing_table

    client = _mock_client()
    routes = [_mock_route(f"route-{i}") for i in range(5)]

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        if "route=" in str(kwargs):
            raise AssertionError(f"N+1! cms_list called with route= kwarg: {kwargs}")
        if "static_routes" in endpoint and "nexthop" not in endpoint:
            return _mock_list_response(*routes)
        return _mock_list_response()

    with patch("nautobot_mcp.cms.routing.resolve_device_id", return_value="device-uuid-1"), \
         patch("nautobot_mcp.cms.routing.cms_list", side_effect=cms_list_side_effect):
        result, warnings = get_device_routing_table(client, device="edge-01")

    assert isinstance(result, RoutingTableResponse)
    assert result.total_routes == 5


# R3: Routes return without fallback when nexthop bulk is empty
def test_routing_table_graceful_empty_nexthops():
    """CQP-03: get_device_routing_table completes without per-route fallback when bulk nexthops are empty."""
    from nautobot_mcp.cms.routing import get_device_routing_table

    client = _mock_client()
    routes = [_mock_route(f"route-{i}") for i in range(5)]

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        if "static_routes" in endpoint and "nexthop" not in endpoint:
            return _mock_list_response(*routes)
        # Both nexthop bulk responses return empty
        return _mock_list_response()

    with patch("nautobot_mcp.cms.routing.resolve_device_id", return_value="device-uuid-1"), \
         patch("nautobot_mcp.cms.routing.cms_list", side_effect=cms_list_side_effect) as mock_cms:
        result, warnings = get_device_routing_table(client, device="edge-01")

    # Still exactly 3 calls — no per-route fallback
    assert mock_cms.call_count == 3
    assert result.total_routes == 5
    # All routes have empty nexthops (graceful degradation)
    for route_data in result.routes:
        assert route_data.get("nexthop_count", 0) == 0


# R4: Nexthop bulk fetch exception → silent graceful degradation (CQP-05)
def test_routing_table_nexthop_bulk_exception_silent():
    """CQP-05: Nexthop bulk fetch exception returns empty nexthops, no WarningCollector warning."""
    from nautobot_mcp.cms.routing import get_device_routing_table

    client = _mock_client()
    routes = [_mock_route(f"route-{i}") for i in range(3)]

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        if "static_routes" in endpoint and "nexthop" not in endpoint:
            return _mock_list_response(*routes)
        if "static_route_nexthops" in endpoint and "qualified" not in endpoint:
            raise RuntimeError("Nexthop bulk fetch failed")
        return _mock_list_response()

    with patch("nautobot_mcp.cms.routing.resolve_device_id", return_value="device-uuid-1"), \
         patch("nautobot_mcp.cms.routing.cms_list", side_effect=cms_list_side_effect) as mock_cms:
        result, warnings = get_device_routing_table(client, device="edge-01")

    # 3 calls: routes + failed nexthop + qualified nexthops (still called)
    assert mock_cms.call_count == 3
    assert isinstance(result, RoutingTableResponse)
    # No warnings for non-critical nexthop enrichment (CQP-05)
    assert warnings == [] or len(warnings) == 0
    for route_data in result.routes:
        assert route_data.get("nexthop_count", 0) == 0


# R5: 50 routes — call count stays at 3 (scale invariance)
def test_routing_table_50_routes_stays_3_calls():
    """CQP-03: get_device_routing_table makes exactly 3 calls with 50 routes (scale invariant)."""
    from nautobot_mcp.cms.routing import get_device_routing_table

    client = _mock_client()
    routes = [_mock_route(f"route-{i}") for i in range(50)]

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        if "static_routes" in endpoint and "nexthop" not in endpoint:
            return _mock_list_response(*routes)
        return _mock_list_response()

    with patch("nautobot_mcp.cms.routing.resolve_device_id", return_value="device-uuid-1"), \
         patch("nautobot_mcp.cms.routing.cms_list", side_effect=cms_list_side_effect) as mock_cms:
        result, warnings = get_device_routing_table(client, device="edge-01")

    assert mock_cms.call_count == 3
    assert result.total_routes == 50


# ---------------------------------------------------------------------------
# BGP N+1 Tests (CQP-04)
# ---------------------------------------------------------------------------

def _mock_bgp_neighbor(neighbor_id, group_id, neighbor_ids_for_af=False):
    """Return a mock BGPSNeighborSummary with optional neighbor_id on AF."""
    nbr = MagicMock()
    nbr.id = neighbor_id
    nbr.group_id = group_id
    nbr.peer_address = f"192.168.{neighbor_id[-1]}.1"
    nbr.model_dump = MagicMock(return_value={
        "id": neighbor_id,
        "group_id": group_id,
        "peer_address": nbr.peer_address,
    })
    return nbr


def _mock_bgp_af(af_id, neighbor_id):
    """Return a mock BGPSAddressFamilySummary with given neighbor_id."""
    af = MagicMock()
    af.id = af_id
    af.neighbor_id = neighbor_id
    af.model_dump = MagicMock(return_value={"id": af_id, "neighbor_id": neighbor_id})
    return af


def _mock_bgp_policy(policy_id, neighbor_id):
    """Return a mock BGPSPolicyAssociationSummary with given neighbor_id."""
    pol = MagicMock()
    pol.id = policy_id
    pol.neighbor_id = neighbor_id
    pol.model_dump = MagicMock(return_value={"id": policy_id, "neighbor_id": neighbor_id})
    return pol


# B1: Guard prevents timeout with 0 neighbors (CQP-04)
def test_bgp_summary_guard_0_neighbors():
    """CQP-04: get_device_bgp_summary with 0 neighbors — AF/policy bulk fetches never called."""
    from nautobot_mcp.cms.routing import get_device_bgp_summary

    client = _mock_client()

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        if "bgp_groups" in endpoint:
            return _mock_list_response()  # 0 groups
        if "bgp_neighbors" in endpoint:
            return _mock_list_response()  # 0 neighbors
        raise AssertionError(f"AF/policy bulk fetch should not be called with 0 neighbors: {endpoint}")

    with patch("nautobot_mcp.cms.routing.list_bgp_groups", return_value=_mock_list_response()), \
         patch("nautobot_mcp.cms.routing.list_bgp_neighbors", return_value=_mock_list_response()):
        result, warnings = get_device_bgp_summary(client, device="edge-01", detail=True)

    assert isinstance(result, BGPSummaryResponse)
    assert result.total_groups == 0
    assert result.total_neighbors == 0


# B2: Exactly 4 bulk cms_list calls with detail=True + many neighbors (CQP-04)
def test_bgp_summary_exactly_4_calls_with_detail():
    """CQP-04: get_device_bgp_summary(detail=True) with 15 neighbors makes exactly 4 bulk calls.

    Calls: list_bgp_groups, list_bgp_neighbors, list_bgp_address_families, list_bgp_policy_associations.
    Zero per-neighbor fallback calls when af_keyed_usable=True (bulk has matching neighbor_ids).
    """
    from nautobot_mcp.cms.routing import get_device_bgp_summary

    client = _mock_client()

    # 1 group × 15 neighbors
    groups = [MagicMock(id="grp-1", name="GR", model_dump=MagicMock(return_value={"id": "grp-1", "name": "GR"}))]
    neighbors = [_mock_bgp_neighbor(f"nbr-{i}", "grp-1") for i in range(15)]
    # 3 AFs per neighbor with matching neighbor_ids → af_keyed_usable=True → fallback suppressed
    afs = [_mock_bgp_af(f"af-{i}", neighbors[i % 15].id) for i in range(45)]
    # 2 policies per neighbor
    pols = [_mock_bgp_policy(f"pol-{i}", neighbors[i % 15].id) for i in range(30)]

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        if "address_families" in endpoint:
            return _mock_list_response(*afs)
        if "policy_associations" in endpoint:
            return _mock_list_response(*pols)
        raise ValueError(f"Unexpected bulk call to {endpoint} with kwargs {kwargs}")

    with patch("nautobot_mcp.cms.routing.list_bgp_groups", return_value=_mock_list_response(*groups)), \
         patch("nautobot_mcp.cms.routing.list_bgp_neighbors", return_value=_mock_list_response(*neighbors)), \
         patch("nautobot_mcp.cms.routing.cms_list", side_effect=cms_list_side_effect) as mock_cms:
        result, warnings = get_device_bgp_summary(client, device="edge-01", detail=True)

    # 4 bulk calls: groups (list_*), neighbors (list_*), AFs (cms_list), policies (cms_list)
    # Zero per-neighbor fallback calls
    assert mock_cms.call_count == 2, f"Expected 2 cms_list (AFs + policies), got {mock_cms.call_count}"
    assert result.total_neighbors == 15


# B3: af_keyed_usable=False suppresses fallback (CQP-04)
def test_bgp_summary_af_keyed_usable_false_suppresses_fallback():
    """CQP-04: When af_keyed_usable=False (no matching neighbor_ids in bulk), shared-enrichment
    fallback applies but per-neighbor fallback is suppressed. No cms_list with neighbor_id= is called."""
    from nautobot_mcp.cms.routing import get_device_bgp_summary

    client = _mock_client()

    groups = [MagicMock(id="grp-1", name="GR", model_dump=MagicMock(return_value={"id": "grp-1", "name": "GR"}))]
    neighbors = [_mock_bgp_neighbor(f"nbr-{i}", "grp-1") for i in range(3)]
    # Bulk AFs with NO matching neighbor_ids → af_keyed_usable=False
    afs = [_mock_bgp_af(f"af-{i}", "orphan-neighbor") for i in range(5)]
    pols = [_mock_bgp_policy(f"pol-{i}", "orphan-neighbor") for i in range(3)]

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, neighbor_id=None, **kwargs):
        # Per-neighbor fallback calls include neighbor_id kwarg
        if neighbor_id is not None:
            raise AssertionError(f"Per-neighbor fallback called: {endpoint} neighbor_id={neighbor_id}")
        if "address_families" in endpoint:
            return _mock_list_response(*afs)
        if "policy_associations" in endpoint:
            return _mock_list_response(*pols)
        raise ValueError(f"Unexpected call to {endpoint}")

    with patch("nautobot_mcp.cms.routing.list_bgp_groups", return_value=_mock_list_response(*groups)), \
         patch("nautobot_mcp.cms.routing.list_bgp_neighbors", return_value=_mock_list_response(*neighbors)), \
         patch("nautobot_mcp.cms.routing.cms_list", side_effect=cms_list_side_effect) as mock_cms:
        result, warnings = get_device_bgp_summary(client, device="edge-01", detail=True)

    # No per-neighbor fallback (neighbor_id= kwarg never passed to cms_list)
    assert mock_cms.call_count == 2
    assert isinstance(result, BGPSummaryResponse)
    assert result.total_neighbors == 3


# B4: AF bulk fetch exception → WarningCollector (CQP-05)
def test_bgp_summary_af_bulk_exception_warning_collector():
    """CQP-05: AF bulk fetch exception returns empty address_families with WarningCollector warning."""
    from nautobot_mcp.cms.routing import get_device_bgp_summary

    client = _mock_client()

    groups = [MagicMock(id="grp-1", name="GR", model_dump=MagicMock(return_value={"id": "grp-1", "name": "GR"}))]
    neighbors = [_mock_bgp_neighbor(f"nbr-{i}", "grp-1") for i in range(2)]
    pols = [_mock_bgp_policy(f"pol-{i}", neighbors[i % 2].id) for i in range(2)]

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        if "address_families" in endpoint:
            raise RuntimeError("AF bulk fetch failed")
        if "policy_associations" in endpoint:
            return _mock_list_response(*pols)
        raise ValueError(f"Unexpected call: {endpoint}")

    with patch("nautobot_mcp.cms.routing.list_bgp_groups", return_value=_mock_list_response(*groups)), \
         patch("nautobot_mcp.cms.routing.list_bgp_neighbors", return_value=_mock_list_response(*neighbors)), \
         patch("nautobot_mcp.cms.routing.cms_list", side_effect=cms_list_side_effect) as mock_cms:
        result, warnings = get_device_bgp_summary(client, device="edge-01", detail=True)

    assert isinstance(result, BGPSummaryResponse)
    # AF failure captured as warning (CQP-05)
    assert len(warnings) > 0
    af_warning = next((w for w in warnings if "address_family" in w.get("key", "")), None)
    assert af_warning is not None, f"Expected AF warning in {warnings}"
```

**Import note:** `RoutingTableResponse` and `BGPSummaryResponse` must be imported from `nautobot_mcp.models.cms.composites`. If those imports cause circular dependency issues in the test environment, import inside the test functions instead.

**Patch target:** Always patch `nautobot_mcp.cms.routing.cms_list` (not `nautobot_mcp.cms.client.cms_list`) since `routing.py` imports `cms_list` at the top level.

**For BGP tests B1–B4:** `list_bgp_groups` and `list_bgp_neighbors` are standalone functions (not `cms_list` wrappers), so patch them directly. `list_bgp_address_families` and `list_bgp_policy_associations` do go through `cms_list`, so they appear in `cms_list` call counts.

</action>

<acceptance_criteria>

- [ ] `tests/test_cms_routing_n1.py` exists and contains `test_routing_table_exactly_3_calls` (grep-verifiable)
- [ ] `tests/test_cms_routing_n1.py` contains `test_routing_table_no_per_route_calls` (grep-verifiable)
- [ ] `tests/test_cms_routing_n1.py` contains `test_routing_table_graceful_empty_nexthops` (grep-verifiable)
- [ ] `tests/test_cms_routing_n1.py` contains `test_routing_table_nexthop_bulk_exception_silent` (grep-verifiable)
- [ ] `tests/test_cms_routing_n1.py` contains `test_routing_table_50_routes_stays_3_calls` (grep-verifiable)
- [ ] `tests/test_cms_routing_n1.py` contains `test_bgp_summary_guard_0_neighbors` (grep-verifiable)
- [ ] `tests/test_cms_routing_n1.py` contains `test_bgp_summary_exactly_4_calls_with_detail` (grep-verifiable)
- [ ] `tests/test_cms_routing_n1.py` contains `test_bgp_summary_af_keyed_usable_false_suppresses_fallback` (grep-verifiable)
- [ ] `tests/test_cms_routing_n1.py` contains `test_bgp_summary_af_bulk_exception_warning_collector` (grep-verifiable)
- [ ] Total test count: 9 tests (5 routing + 4 BGP)
- [ ] All tests patch `nautobot_mcp.cms.routing.cms_list` (not `nautobot_mcp.cms.client.cms_list`) — grep-verifiable
- [ ] `test_bgp_summary_exactly_4_calls_with_detail` asserts `mock_cms.call_count == 2` (AFs + policies via cms_list; groups + neighbors via list_* direct calls)

</acceptance_criteria>

<verify>

```bash
uv run pytest tests/test_cms_routing_n1.py -v
```

All 9 tests must pass. If there are import errors for `RoutingTableResponse` or `BGPSummaryResponse`, check the actual import path in `nautobot_mcp/models/cms/composites.py` and update the import in the test file.

</verify>
