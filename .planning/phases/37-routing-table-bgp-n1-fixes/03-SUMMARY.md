---
phase: 37-routing-table-bgp-n1-fixes
plan: 03
subsystem: tests
tags: [n+1, routing, bgp, test, invariant]

# Dependency graph
requires:
  - phase: 37-routing-table-bgp-n1-fixes
    provides: Plan 01 (routing N+1 loop removed, d93a84a); Plan 02 (CQP-04 documented, 5d0fb16)
provides:
  - 9 N+1 invariant tests in tests/test_cms_routing_n1.py
affects:
  - Phase 38 regression gate

# Tech tracking
tech-stack:
  added:
    - tests/test_cms_routing_n1.py
  patterns:
    - Routing bulk: exactly 3 cms_list calls (routes + 2 bulk nexthops), no per-route fallback
    - BGP bulk: exactly 2 cms_list calls (AFs + policies), groups/neighbors patched separately
    - WarningCollector "operation" field (not "key") — confirmed from live test output

key-files:
  created:
    - tests/test_cms_routing_n1.py (9 tests, 361 lines)
  modified: []

patterns-established:
  - "route= kwarg assertion pattern" — detect N+1 by asserting no cms_list call ever receives route= kwarg
  - "cms_list call_count invariant" — assert call_count is constant regardless of item count

requirements-completed: [CQP-03, CQP-04, CQP-05]

# Metrics
duration: 15min
completed: 2026-03-31
---

# Phase 37: Routing Table + BGP N+1 Fixes — Plan 03 Summary

**9 N+1 invariant tests created in `tests/test_cms_routing_n1.py` — all 9 pass; 548 total unit tests pass**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-31T09:15:00Z
- **Completed:** 2026-03-31T09:30:00Z
- **Tasks:** 9 tests (5 routing + 4 BGP)
- **Files created:** 1
- **Commit:** `145f2c5`

## Accomplishments

- Created `tests/test_cms_routing_n1.py` following Phase 35/36 N+1 invariant test pattern
- 5 routing tests (CQP-03 + CQP-05):
  - `test_routing_table_exactly_3_calls` — confirms exactly 3 cms_list calls with 3 routes
  - `test_routing_table_no_per_route_calls` — `route=` kwarg assertion proves N+1 loop removed
  - `test_routing_table_graceful_empty_nexthops` — empty bulk nexthops → no per-route fallback
  - `test_routing_table_nexthop_bulk_exception_silent` — bulk exception → empty nexthops, no warning
  - `test_routing_table_50_routes_stays_3_calls` — scale invariant (3 calls for 50 routes)
- 4 BGP tests (CQP-04 + CQP-05):
  - `test_bgp_summary_guard_0_neighbors` — guard prevents AF/policy calls when 0 neighbors
  - `test_bgp_summary_exactly_2_cms_list_calls_with_detail` — 15 neighbors → 2 cms_list calls (AFs + policies)
  - `test_bgp_summary_af_keyed_usable_false_suppresses_fallback` — unkeyed bulk → shared fallback, no per-neighbor calls
  - `test_bgp_summary_af_bulk_exception_warning_collector` — AF exception → WarningCollector with `operation` field
- Bug found and fixed: WarningCollector uses `"operation"` field, not `"key"` — corrected assertion
- All 548 unit tests pass (no regression)

## Task Commits

1. **N+1 invariant tests** — `145f2c5` (test)

## Files Created/Modified

- `tests/test_cms_routing_n1.py` — 9 new tests, 361 lines; follows Phase 35 `test_cms_interfaces_n1.py` pattern

## Decisions Made

- Patch `nautobot_mcp.cms.routing.cms_list` (not `cms.client.cms_list`) since routing.py imports it at top level
- `list_bgp_groups` and `list_bgp_neighbors` patched separately; only AF/policy go through `cms_list`
- `WarningCollector` warning dict uses `"operation"` key (not `"key"`) — confirmed from live log output

## Deviations from Plan

- Minor: `w.get("key", "")` → `w.get("operation", "")` — corrected after seeing actual WarningCollector shape

## Issues Encountered

- Initial assertion used `"key"` field for WarningCollector dict — live test revealed it uses `"operation"`. Fixed in 1 edit, all tests green.

## Phase 37 Complete

All 3 plans shipped:
- Plan 01 (`d93a84a`): N+1 loop removed from `list_static_routes`
- Plan 02 (`5d0fb16`): CQP-04 triple-guard documented inline
- Plan 03 (`145f2c5`): 9 N+1 invariant tests in `tests/test_cms_routing_n1.py`

## Next Phase Readiness

- Phase 37 COMPLETE
- Phase 38 (regression gate) next: `uat_cms_smoke.py` smoke test + full unit suite confirmation

---
*Phase: 37-routing-table-bgp-n1-fixes, Plan 03*
*Completed: 2026-03-31*
