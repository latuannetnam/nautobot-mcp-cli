---
phase: 37-routing-table-bgp-n1-fixes
plan: 01
subsystem: cms
tags: [n+1, pynautobot, cms, routing, performance]

# Dependency graph
requires:
  - phase: 36-firewall-summary-n1-fixes
    provides: bulk prefetch + WarningCollector pattern, N+1 invariant test structure
provides:
  - N+1 loop removed from `list_static_routes()` — nexthops inlined from bulk dicts
  - `get_device_routing_table()` now makes exactly 3 HTTP calls regardless of route count
affects:
  - phase: 38-regression-gate
  - phase: 37-plan-02

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Bulk prefetch with dict-by-FK grouping — same pattern as Phase 35 interfaces + Phase 36 firewalls"

key-files:
  created: []
  modified:
    - nautobot_mcp/cms/routing.py
    - tests/test_cms_routing.py

key-decisions:
  - "Nexthop/qualified-nexthop bulk fetches already existed at L79-92; the N+1 loop at L96-123 was redundant — simply deleted it and kept the inline assignment"
  - "Bulk fetch `except Exception: pass` blocks already provide graceful degradation — no WarningCollector needed for non-critical nexthop data"

patterns-established:
  - "Bulk prefetch → dict-by-route_id → inline loop assignment: standard N+1 elimination pattern for CMS composite functions"

requirements-completed: [CQP-03]

# Metrics
duration: 5min
completed: 2026-03-31
---

# Phase 37 Plan 01 Summary

**N+1 loop removed from `list_static_routes()` — nexthops inlined from pre-fetched bulk dicts; routing_table now makes exactly 3 HTTP calls regardless of route count**

## Performance

- **Duration:** ~5 min
- **Tasks:** 1 (atomic fix + test update)
- **Files modified:** 2
- **Commit:** `d93a84a`

## Accomplishments
- Deleted the per-route `cms_list(route=route.id)` fallback for-loop (26 lines removed)
- Inlined `route.nexthops` and `route.qualified_nexthops` assignment into the existing bulk block
- `get_device_routing_table()` now achieves the ≤3 HTTP call target (routes + all nexthops + all qualified nexthops)
- Updated `test_list_inlines_nexthops` to mock the bulk `device=device_id` path instead of the removed per-route `route=` path

## Task Commits

1. **fix(cms/routing): remove N+1 loop from list_static_routes() — nexthops inlined into bulk block** — `d93a84a` (fix)

## Files Created/Modified
- `nautobot_mcp/cms/routing.py` — removed N+1 fallback loop; added inline assignment comment
- `tests/test_cms_routing.py` — updated mock for bulk nexthop path; removed per-route `side_effect` function

## Decisions Made
None — plan executed exactly as written. The fix was straightforward because the bulk fetches at L79-92 were already correct; only the N+1 fallback loop (L96-123) and the `route.nexthops` lines inside it needed to be replaced with a single inline assignment loop.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

**1. Test `test_list_inlines_nexthops` failed after N+1 loop removal**
- **Found during:** Verification (running `pytest tests/test_cms_routing.py`)
- **Issue:** Mock used a `side_effect` that only returned nexthops when `kwargs.get("route")` matched — but after the fix, the code calls `cms_list` with `device=device_id` (not `route=route.id`), so the mock returned empty `[]` for all nexthops
- **Fix:** Changed mock to a simple `return_value=[nh_record]` on `juniper_static_route_nexthops.filter` (bulk device-level query); added `nh_record.route.id` so the Pydantic model builder populates `nh.route_id` for the dict-by-route_id lookup
- **Files modified:** `tests/test_cms_routing.py`
- **Verification:** All 22 routing tests pass; 539 total tests pass
- **Committed in:** `d93a84a` (same commit as the fix)

## Next Phase Readiness
- Plan 01 complete — routing N+1 eliminated
- Plan 02 (bgp_summary guard hardening) and Plan 03 (routing/bgp N+1 invariant tests) are next
- No blockers

---
*Phase: 37-routing-table-bgp-n1-fixes*
*Completed: 2026-03-31*
