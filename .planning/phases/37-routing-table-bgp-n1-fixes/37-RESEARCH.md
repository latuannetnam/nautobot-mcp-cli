# Phase 37: `routing_table` + `bgp_summary` N+1 Fixes — Research

**Author:** gsd-phase-researcher
**Phase:** 37-routing-table-bgp-n1-fixes
**Date:** 2026-03-31
**Status:** ✅ Ready to plan

---

## 1. Phase Overview

### What We're Fixing

Two N+1 HTTP query loops in `nautobot_mcp/cms/routing.py`:

| Function | N+1 Pattern | Requirement | Status |
|----------|-------------|-------------|--------|
| `get_device_routing_table()` / `list_static_routes()` | Per-route nexthop fallback loop (L96-120) fires when bulk map misses a route ID | CQP-03: ≤3 HTTP calls | Fix needed |
| `get_device_bgp_summary()` | Per-neighbor AF/policy fallback guarded by `len(...) > 0` checks | CQP-04: guards verified sufficient | No code change |

### Call Path

```
get_device_routing_table()        ← composite entry (L782)
  └─ list_static_routes()           ← L46: routes + bulk nexthop prefetch
       ├─ cms_list("juniper_static_routes", ...)         [1] ← routes list
       ├─ cms_list("juniper_static_route_nexthops", ...)  [2] ← bulk all nexthops
       └─ cms_list("juniper_static_route_qualified_nexthops", ...) [3] ← bulk all qualified nexthops
            └─ PER-ROUTE FALLBACK LOOP (L96-120) ← N+1 #1 ← REMOVE THIS

get_device_bgp_summary()          ← composite entry (L639)
  ├─ list_bgp_groups(...)                              [1]
  ├─ list_bgp_neighbors(...)                            [2]
  ├─ list_bgp_address_families(limit=0) (detail only)   [3] ← bulk AF
  └─ list_bgp_policy_associations(limit=0) (detail only)[4] ← bulk policy
       └─ per-neighbor fallback (L734-751) ← triple-guarded ✓
```

### Requirements Mapping

| ID | Text | Covered by |
|----|------|-----------|
| CQP-03 | `get_device_routing_table` removes per-route nexthop fallback; ≤3 HTTP calls | Fix L96-120 removal |
| CQP-04 | `get_device_bgp_summary` guards per-neighbor AF/policy behind `len(af_by_nbr) > 0` and `len(policy_by_nbr) > 0` checks | Verified at L734/L741 |
| CQP-05 | All N+1 fixes preserve `WarningCollector` partial-failure behavior | Nexthop graceful degradation |

---

## 2. Code Analysis

### 2.1 `list_static_routes()` — The N+1 Root Cause

**File:** `nautobot_mcp/cms/routing.py`, L46-128

```python
# L72-73: Routes list (1 HTTP call via cms_list)
routes = cms_list(client, "juniper_static_routes", StaticRouteSummary,
                  limit=limit, offset=offset, **filters)

# L75-92: Bulk nexthop prefetch — ALREADY CORRECT
if routes.results:
    nh_by_route: dict = {}
    qnh_by_route: dict = {}
    try:
        # L80-83: Bulk nexthops for ALL routes — 1 HTTP call
        all_nhs = cms_list(client, "juniper_static_route_nexthops",
                           StaticRouteNexthopSummary, limit=0, device=device_id)
        for nh in all_nhs.results:
            nh_by_route.setdefault(nh.route_id, []).append(nh)
    except Exception:
        pass  # ← graceful degradation (D-02)
    try:
        # L87-90: Bulk qualified nexthops — 1 HTTP call
        all_qnhs = cms_list(client, "juniper_static_route_qualified_nexthops",
                            StaticRouteQualifiedNexthopSummary, limit=0, device=device_id)
        for q in all_qnhs.results:
            qnh_by_route.setdefault(q.route_id, []).append(q)
    except Exception:
        pass  # ← graceful degradation (D-02)

# L96-120: PER-ROUTE FALLBACK LOOP ← THE N+1
# "Backward-compatible fallback: if bulk map has no entry for a route,
#  query that route directly (preserves old test behavior/mocks)"
for route in routes.results:
    if route.id not in nh_by_route:                    # L97
        per_route_nhs = cms_list(client, "juniper_static_route_nexthops",
                                 StaticRouteNexthopSummary, limit=0, route=route.id)  # ← 1 call/route
        nh_by_route[route.id] = per_route_nhs.results
    if route.id not in qnh_by_route:                   # L109
        per_route_qnhs = cms_list(...)                 # ← 1 call/route
        qnh_by_route[route.id] = per_route_qnhs.results
```

**Root Cause:** The bulk fetches at L79-92 use `device=device_id` to get ALL nexthops for ALL routes on the device. Since every route belongs to that device, the bulk map should contain every route's nexthops. The fallback at L96-120 fires only when the bulk map is unexpectedly missing an entry — but the bulk fetch IS the authoritative source. The fallback is a workaround for incomplete CMS data or test mocks, not production data.

**Scale impact:** On HQV-PE1 with ~N_routes, the fallback generates 2 × N_routes extra HTTP calls. With N_routes=1000, that's 2,000 extra calls.

**Fix:** Remove L96-120 entirely. If the bulk map is missing an entry, the route simply has no nexthops (empty list). Graceful degradation is already implemented for bulk fetch failures (the `except Exception: pass` blocks at L84-85 and L91-92 silently initialize empty dicts).

### 2.2 `get_device_bgp_summary()` — Guards Already Sufficient

**File:** `nautobot_mcp/cms/routing.py`, L639-779

Key guard locations:

```
L687: if detail and all_neighbors:          ← Guard #1: skip AF/pol fetch when no neighbors
L709: neighbor_ids = {n.id for n in all_neighbors}
L710: af_keyed_usable = any(getattr(af, "neighbor_id", None) in neighbor_ids for af in all_afs_results)
L711: pol_keyed_usable = any(getattr(p, "neighbor_id", None) in neighbor_ids for p in all_pols_results)

L734: if not fam_list and not af_bulk_failed and af_keyed_usable:   ← Guard #2
L741: if not pol_list and not pol_bulk_failed and pol_keyed_usable: ← Guard #3
```

**Analysis of the triple guard (L734):**
- `not fam_list` — bulk map returned empty for this neighbor
- `not af_bulk_failed` — the bulk fetch itself didn't error out
- `af_keyed_usable` — the bulk results actually contain matching `neighbor_id` keys (at least one AF has a `neighbor_id` in the neighbor set)

This triple guard is correct and sufficient. When `af_keyed_usable` is `False`, the fallback is suppressed because the bulk data doesn't have useful neighbor_id keys. The guard at L687 ensures AF/policy bulk fetches only happen when there ARE neighbors.

**CQP-04 conclusion:** No code changes needed. Guards are already correct at L687, L734, and L741.

### 2.3 `get_device_routing_table()` — Pass-through

**File:** `nautobot_mcp/cms/routing.py`, L782-835

This function is a thin wrapper that calls `list_static_routes()` (L809) and wraps the result in `RoutingTableResponse`. No N+1 here — the fix is entirely in `list_static_routes`.

---

## 3. Fix Approach

### 3.1 Remove Per-Route Fallback Loop (CQP-03)

**File:** `nautobot_mcp/cms/routing.py`
**Lines:** 94-123 (the for-loop body)

**Action:** Delete L94-123 entirely. Keep L75-93 (bulk prefetch) and L125 (return).

**Before:**
```python
# L75-93: Bulk prefetch (keep)
if routes.results:
    nh_by_route: dict = {}
    qnh_by_route: dict = {}
    try:
        all_nhs = cms_list(client, "juniper_static_route_nexthops", ...)
        for nh in all_nhs.results:
            nh_by_route.setdefault(nh.route_id, []).append(nh)
    except Exception:
        pass
    try:
        all_qnhs = cms_list(client, "juniper_static_route_qualified_nexthops", ...)
        for q in all_qnhs.results:
            qnh_by_route.setdefault(q.route_id, []).append(q)
    except Exception:
        pass

# L94-123: PER-ROUTE FALLBACK ← DELETE THIS ENTIRE BLOCK
    for route in routes.results:
        if route.id not in nh_by_route:
            per_route_nhs = cms_list(client, "juniper_static_route_nexthops", route=route.id, ...)
            nh_by_route[route.id] = per_route_nhs.results
        if route.id not in qnh_by_route:
            per_route_qnhs = cms_list(client, "juniper_static_route_qualified_nexthops", route=route.id, ...)
            qnh_by_route[route.id] = per_route_qnhs.results
        route.nexthops = nh_by_route.get(route.id, [])
        route.qualified_nexthops = qnh_by_route.get(route.id, [])

# L125: return (keep, but route.nexthops assignment moves)
    return ListResponse(count=len(routes.results), results=routes.results)
```

**After:**
```python
# L75-93: Bulk prefetch (keep as-is)
if routes.results:
    nh_by_route: dict = {}
    qnh_by_route: dict = {}
    try:
        all_nhs = cms_list(client, "juniper_static_route_nexthops", ...)
        for nh in all_nhs.results:
            nh_by_route.setdefault(nh.route_id, []).append(nh)
    except Exception:
        pass
    try:
        all_qnhs = cms_list(client, "juniper_static_route_qualified_nexthops", ...)
        for q in all_qnhs.results:
            qnh_by_route.setdefault(q.route_id, []).append(q)
    except Exception:
        pass

    # Inline nexthops into each route (no per-route HTTP calls)
    for route in routes.results:
        route.nexthops = nh_by_route.get(route.id, [])
        route.qualified_nexthops = qnh_by_route.get(route.id, [])

return ListResponse(count=len(routes.results), results=routes.results)
```

**Key changes:**
1. Delete L94-95 comment and L96-120 for-loop (per-route fallback)
2. Move the `route.nexthops = ...` assignment inside the `if routes.results:` block (L122-123 logic)
3. The `except Exception: pass` blocks at L84-85 and L91-92 already handle graceful degradation when bulk fetches fail — they leave empty dicts, so `route.nexthops = []` is returned
4. No `WarningCollector` needed for nexthop enrichment failure — it's non-critical (nexthops enrich routes, not co-primary data), matching Phase 35/36 pattern

**HTTP Call Budget After Fix:**
| Call | Description |
|------|-------------|
| 1 | `cms_list("juniper_static_routes", device=device_id, limit=0)` — routes list |
| 2 | `cms_list("juniper_static_route_nexthops", device=device_id, limit=0)` — all nexthops |
| 3 | `cms_list("juniper_static_route_qualified_nexthops", device=device_id, limit=0)` — all qualified nexthops |

Total: **3 HTTP calls** regardless of route count. ✅ CQP-03 satisfied.

### 3.2 BGP Guard Verification (CQP-04) — No Code Change

The triple-guard pattern at L734/L741 is correct:
- `not fam_list` — no data in bulk map for this neighbor
- `not af_bulk_failed` — bulk fetch didn't error
- `af_keyed_usable` — bulk data has valid `neighbor_id` keys

When all three conditions are `True`, the fallback fires. But `af_keyed_usable` being `True` means the bulk data IS usable, so the fallback won't fire unnecessarily. When `af_keyed_usable` is `False`, the fallback is suppressed because the bulk data doesn't have usable keys.

**CQP-04 is already satisfied.** Document this in tests.

---

## 4. Testing Strategy

### 4.1 Test File: `tests/test_cms_routing_n1.py`

Following the Phase 35 (`test_cms_interfaces_n1.py`) and Phase 36 (`test_cms_firewalls_n1.py`) pattern:

- Monkey-patch `cms_list` in the routing module to count HTTP calls
- Assert ≤N calls regardless of how many routes/neighbors/AFs are in mocked responses
- Mock `WarningCollector` via the module-level import pattern

**Module under test:** `nautobot_mcp.cms.routing`
**Functions to test:** `get_device_routing_table`, `get_device_bgp_summary`
**Patching target:** `nautobot_mcp.cms.routing.cms_list`

### 4.2 Routing N+1 Tests (CQP-03)

#### Test R1: Exactly 3 `cms_list` calls (bulk data complete)

```
3 routes × mixed nexthops (some have both NH + QNH, some have none)
```

Assert:
- `cms_list` called exactly 3 times
- Call #1 endpoint: `juniper_static_routes`
- Call #2 endpoint: `juniper_static_route_nexthops`
- Call #3 endpoint: `juniper_static_route_qualified_nexthops`
- All routes have correct nexthops from bulk maps
- Zero per-route fallback calls

#### Test R2: Routes return without fallback when nexthop bulk is empty

```
5 routes, bulk nexthop response is empty (nh_by_route = {})
```

Assert:
- `cms_list` called exactly 3 times (bulk fetches still fire, return [])
- All routes have `nexthops = []` and `qualified_nexthops = []`
- No additional per-route calls

#### Test R3: `cms_list` never called with `route=<id>` filter

```
Patch cms_list to raise AssertionError if any call includes `route=` kwarg.
```

Assert:
- Function completes without raising
- Proves the per-route fallback was removed

#### Test R4: Nexthop bulk fetch exception → silent graceful degradation (CQP-05)

```
Bulk nexthop fetch raises RuntimeError.
```

Assert:
- Function returns valid `RoutingTableResponse`
- Routes have `nexthops = []` for the failed fetch type
- No exception propagates
- No `WarningCollector` warning for non-critical nexthop enrichment (matches D-02)

#### Test R5: Many routes — call count stays at 3

```
50 routes with varying nexthop counts
```

Assert:
- `cms_list` called exactly 3 times
- All 50 routes correctly enriched

### 4.3 BGP N+1 Tests (CQP-04)

#### Test B1: Guard prevents timeout when device has no neighbors

```
0 groups, 0 neighbors
```

Assert:
- AF/policy bulk fetches never called
- `cms_list` called ≤2 times (groups + neighbors)
- Response valid with `groups=[]`

#### Test B2: Exactly 6 `cms_list` calls with detail=True and many neighbors

```
3 groups × 5 neighbors = 15 neighbors
3 AFs per neighbor, 2 policies per neighbor
```

Assert:
- `cms_list` called exactly 4 times:
  - groups, neighbors, AFs (bulk), policies (bulk)
- Zero per-neighbor fallback calls
- All neighbors enriched with correct AF/policy counts

#### Test B3: Guards verified — no per-neighbor fallback when keyed usable

```
Bulk AF response has matching neighbor_ids for all neighbors.
```

Assert:
- `af_keyed_usable = True` → fallback at L734 never fires
- `cms_list` called with `neighbor_id=` filter: 0 times

#### Test B4: AF bulk fetch exception → WarningCollector (CQP-05)

```
Bulk AF fetch raises RuntimeError.
```

Assert:
- Response returns valid `BGPSummaryResponse`
- All neighbors have `address_families = []`
- `collector.warnings` contains the AF error
- Function does NOT raise

### 4.4 Mock Data Requirements

To support the tests without the per-route fallback:

```python
# Routes with route_ids
_ROUTES = [MagicMock(id=f"route-{i}", ...) for i in range(3)]

# Nexthops for routes 0 and 2 only (route-1 has no nexthops — valid case)
_NH_BY_ROUTE = {
    "route-0": [MagicMock(id="nh-0", route_id="route-0", ...)],
    "route-2": [MagicMock(id="nh-2", route_id="route-2", ...)],
}

# Qualified nexthops for route-0 only
_QNH_BY_ROUTE = {
    "route-0": [MagicMock(id="qnh-0", route_id="route-0", ...)],
}
```

The `cms_list` mock for `juniper_static_route_nexthops` must return `list(_NH_BY_ROUTE.values())[0] + list(_NH_BY_ROUTE.values())[1]` flattened — all nexthops as a flat list, not grouped.

---

## 5. Risks and Edge Cases

### Risk 1: Existing tests with incomplete nexthop mock data

**Severity:** High
**Description:** If existing tests mock `juniper_static_route_nexthops` to return data only for `route=<id>` (per-route), they will fail after L96-120 removal because the bulk fetch won't return any nexthops for the routes in the mock.

**Mitigation:** Update test mocks to include nexthops in bulk responses. The bulk fetches use `device=device_id`, so mocks need to return nexthops in the bulk response, not in per-route responses.

**Detection:** Run `uv run pytest tests/` — existing routing tests will fail if they rely on the fallback loop.

### Risk 2: Production CMS plugin returns incomplete nexthop data

**Severity:** Low
**Description:** If the CMS plugin `juniper_static_route_nexthops` endpoint is missing entries for some routes (plugin bug, sync delay), routes will return with empty nexthops after this fix.

**Mitigation:** The fix exposes incomplete CMS data rather than silently papering over it. This is the correct behavior — the bulk map IS the authoritative source. If data is missing, the CMS plugin needs to be fixed, not the client.

**User impact:** Routes that previously had nexthops via fallback will now return with empty nexthops. The `WarningCollector` could be used to detect this pattern (count of routes with no nexthops vs. routes with nexthops), but this is out of scope for Phase 37.

### Risk 3: Nexthop bulk fetch times out on large devices

**Severity:** Low
**Description:** With `limit=0`, the nexthop bulk fetches use `_CMS_BULK_LIMIT = 200` to paginate internally. On a device with 10,000 nexthops, this takes 50 sequential HTTP calls.

**Mitigation:** This is the same behavior as before — `_CMS_BULK_LIMIT` was introduced in Phase 33 specifically to handle this. The per-route fallback was making it worse by adding N more calls. After this fix, the upper bound is 3 + ceil(N/200) calls for N nexthops.

### Risk 4: `WarningCollector` not used for nexthop enrichment failure

**Severity:** Info
**Description:** Per D-02, nexthop bulk fetch failure uses silent graceful degradation (empty dict, no warning). This is consistent with Phase 35 VRRP graceful degradation.

**Mitigation:** No change needed. Nexthops are non-critical enrichment.

### Risk 5: BGP guards work differently in test vs. production

**Severity:** Low
**Description:** In test mocks, AF/policy bulk responses often don't have matching `neighbor_id` keys (they're generic mock objects). This makes `af_keyed_usable = False` in tests, which suppresses the fallback. The guards are correct in production but behave differently in tests.

**Mitigation:** Tests should explicitly verify the guard behavior. Test B3 (above) sets up bulk AF data with matching `neighbor_id` values to verify `af_keyed_usable = True` suppresses fallback.

---

## 6. Validation Architecture

### 6.1 N+1 Invariant (Call Budget Assertion)

The core validation principle (following Phase 35/36):

> `cms_list` call count MUST be invariant to the number of items in the enriched collection.

For routing:
- Vary `N_routes` from 0 to 1000
- `cms_list` call count stays at 3

For BGP:
- Vary `N_neighbors` from 0 to 100, `N_AFs` from 0 to 1000
- `cms_list` call count stays at 4 (detail=True) or 2 (detail=False)

### 6.2 Failsafe Assertion (Proof of N+1 Removal)

```python
# Patch the per-route fallback endpoint to raise if called
with patch.object(routing_module, "cms_list",
                  side_effect=lambda *args, **kwargs:
                      AssertionError(f"N+1! cms_list called with route= kwarg: {kwargs}")
                      if kwargs.get("route") else _cms_list_real(*args, **kwargs)):
    result, warnings = get_device_routing_table(client, device="edge-01")

# If we reach here, no per-route fallback fired → N+1 is gone
assert isinstance(result, RoutingTableResponse)
```

This pattern is directly copied from `test_interface_detail_no_per_unit_family_calls` in Phase 35 (L119-126).

### 6.3 Regression Gate (Phase 38)

After Phase 37 implementation:
1. Run `uv run pytest tests/test_cms_routing_n1.py` — all new tests must pass
2. Run `uv run pytest tests/` — no existing tests regressed
3. Run `python scripts/uat_cms_smoke.py` — `routing_table` and `bgp_summary` pass within thresholds

### 6.4 Smoke Test Thresholds

| Workflow | Threshold | Expected |
|----------|-----------|----------|
| `routing_table` | < 60s | < 5s (was ~N×2s with N+1) |
| `bgp_summary` | < 60s | < 5s (guards prevent timeout) |

---

## 7. Summary of Changes

### Code Changes (1 file)

**`nautobot_mcp/cms/routing.py`:**
- `list_static_routes()` L96-123: Delete per-route fallback for-loop
- `list_static_routes()` L122-123: Move `route.nexthops` assignment inside `if routes.results:` block

### Test Changes (1 new file)

**`tests/test_cms_routing_n1.py`** (9 tests):
- R1: Exactly 3 `cms_list` calls (CQP-03)
- R2: Routes return without fallback when nexthop bulk is empty (CQP-03)
- R3: `cms_list` never called with `route=<id>` filter (CQP-03)
- R4: Nexthop bulk fetch exception → silent graceful degradation (CQP-05)
- R5: 50 routes — call count stays at 3 (CQP-03)
- B1: Guard prevents timeout with 0 neighbors (CQP-04)
- B2: Exactly 4 `cms_list` calls with detail=True + many neighbors (CQP-04)
- B3: `af_keyed_usable = True` suppresses per-neighbor fallback (CQP-04)
- B4: AF bulk fetch exception → WarningCollector (CQP-05)

### No Changes Needed

- `get_device_bgp_summary()` — guards verified sufficient
- `WarningCollector` usage — already correct for BGP; nexthop uses silent degradation (D-02)
- `cms_list()` in `client.py` — already handles `_CMS_BULK_LIMIT = 200`
- Any existing test mocks for BGP — guard pattern already in place

---

## 8. File Index

| File | Lines | Change |
|------|-------|--------|
| `nautobot_mcp/cms/routing.py` | L96-123 | DELETE per-route fallback loop |
| `nautobot_mcp/cms/routing.py` | L122-123 | MOVE nexthop assignment into `if routes.results:` |
| `tests/test_cms_routing_n1.py` | NEW | 9 N+1 invariant tests |
| `.planning/phases/37-routing-table-bgp-n1-fixes/37-RESEARCH.md` | NEW | This document |
