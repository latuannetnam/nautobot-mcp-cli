---
gsd_state_version: 1.0
milestone: v1.10
milestone_name: CMS N+1 Query Elimination
status: executing
last_updated: "2026-03-31T08:52:54.404Z"
last_activity: 2026-03-31
progress:
  total_phases: 31
  completed_phases: 28
  total_plans: 66
  completed_plans: 71
---

# Project State: nautobot-mcp-cli

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-31)

**Core value:** AI agents can discover, read, write, and orchestrate Nautobot data through 3 tools instead of 165
**Current focus:** Phase 38 — Regression Gate

## Current Position

Phase: 38
Plan: 01 shipped | 02 shipped
Status: COMPLETE — all requirements satisfied
Last activity: 2026-03-31

## Phase Plan

| Phase | Focus | Key Requirements |
|-------|-------|-------------------|
| Phase 35 | `interface_detail` N+1 Fix | ✅ COMPLETE |
| Phase 36 | `firewall_summary` Detail N+1 Fix | ✅ COMPLETE |
| Phase 37 | `routing_table` + `bgp_summary` Fixes | ✅ COMPLETE |
| Phase 38 | Regression Gate | RGP-01 ✅, RGP-02 ✅ |

## Root Causes (from investigation, 2026-03-31)

Three N+1 patterns identified across the 4 failing CMS workflows:

1. **`interface_detail`** (interfaces.py ~line 690): ~~Bulk-fetches interface families once, then discards the result and refetches families one-by-one per unit~~ — Plan 01+02 fixed both family and VRRP N+1: now ≤3 HTTP calls total (units + bulk families + bulk VRRP).

2. **`firewall_summary`** with `detail=True` (firewall.py): Per-filter loop fetches terms individually; per-term loop fetches actions individually. With many filters/terms: N×M sequential HTTP requests → >120s timeout.

3. **`routing_table`** (routing.py ~line 96): After bulk-fetching nexthops, loops over every route and fires `cms_list(route=<id>)` for uncovered routes. With thousands of routes: 2 × N_routes extra HTTP requests.

4. **`bgp_summary`**: Per-neighbor AF/policy fallback loops without `len(...) > 0` guards (partially fixed in v1.9 Phase 34, but guards may be missing in some paths).

**CQP-05 constraint**: All fixes must preserve `WarningCollector` partial-failure behavior — `status: "partial"` when child queries fail.

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Fix N+1 in each workflow individually | Each workflow has distinct data access patterns; no one-size-fits-all |
| Cross-cutting WarningCollector fix in Phases 35/36 | `CQP-05` applies to all bulk refactors; fix it once when first touching a workflow |
| Phase 38 smoke test gates the milestone | v1.9 Phase 34 smoke showed 5/5 PASS; same bar for v1.10 |
| No research needed | Root causes already identified; fix scope is well-understood |

## Context

- v1.0 shipped 2026-03-18 with core MCP + CLI + parsing/onboarding foundations
- v1.1 shipped 2026-03-20 with agent-native tools and file-free drift
- v1.2 shipped 2026-03-21 with Juniper CMS CRUD + composite tools + CMS drift
- v1.3 shipped 2026-03-25 with 165→3 API Bridge consolidation
- v1.4 shipped 2026-03-26 with robustness, diagnostics, and response ergonomics
- v1.6 shipped 2026-03-28 with query performance optimizations
- v1.7 shipped 2026-03-29 with URI limit fixes, VLANs 500 fix, and UAT smoke script
- v1.8 shipped 2026-03-30 with CMS pagination fix (`_CMS_BULK_LIMIT = 200`)
- v1.9 shipped 2026-03-30 with AF/policy gating and CLI default limit fix
- v1.10 started 2026-03-31 to eliminate remaining N+1 patterns

## Blockers

None.

## Accumulated Context

**Phase 35 success criteria (interface_detail N+1 fix):**

- `get_interface_detail()` makes ≤ 3 HTTP calls for any device regardless of unit count (bulk families, bulk VRRP, bulk units)
- No per-unit `list_interface_families()` loop in the call path
- No per-family `list_interface_vrrp_groups()` loop in the call path
- `WarningCollector` still accumulates and returns warnings on partial failure
- `interface_detail` CLI command returns within 60s on HQV-PE1
- ✅ Phase 35 COMPLETE: Plans 01+02 refactored bulk prefetch; Plan 03 added 8 unit tests in `test_cms_interfaces_n1.py`

**Phase 36 success criteria (firewall_summary detail N+1 fix):**

- `get_device_firewall_summary(detail=True)` makes ≤ 6 HTTP calls regardless of filter/policer count
- No per-filter `list_firewall_terms()` loop in the call path
- No per-term `list_firewall_term_actions()` loop in the call path
- `WarningCollector` still accumulates and returns warnings on partial failure
- `firewall_summary` CLI command returns within 60s on HQV-PE1
- ✅ Phase 36 COMPLETE: Plans 01+02 refactored bulk prefetch; Plan 03 added 8 unit tests in `test_cms_firewalls_n1.py`

**Phase 37 success criteria (routing_table + bgp_summary fixes):**

- `get_device_routing_table()` makes ≤3 HTTP calls: routes list + 2 bulk nexthop fetches (no per-route fallback)
- Nexthop bulk fetch failure → silent graceful degradation (empty dict); WarningCollector for critical paths
- Per-route fallback loop removed (L96-120 in `list_static_routes`); test mocks updated to include bulk data
- ✅ Plan 01 SHIPPED (d93a84a): N+1 loop deleted; inline assignment in bulk block; routing tests updated
- ✅ Plan 02 SHIPPED (5d0fb16): CQP-04 documented inline — triple-guard rationale explained; zero functional changes
- ✅ Plan 03 SHIPPED (145f2c5): 9 N+1 invariant tests in `tests/test_cms_routing_n1.py`; 548 unit tests pass
- `get_device_bgp_summary()` existing guards sufficient (no code changes needed for CQP-04)
- All Phase 37 tests pass

**Phase 38 success criteria (regression gate):**

- `uat_cms_smoke.py` reports all 5 workflows PASS within thresholds on HQV-PE1
- All existing unit tests pass (no regression from refactored code paths)
- Total test count ≥ 443 (v1.7 final count) + any new tests added in Phases 35-37

---
*State initialized: 2026-03-28*
*Last updated: 2026-03-31 — Phase 38 context complete; 4 decisions captured (thresholds conservative, HQV-PE1-NEW smoke target, full unit suite, manual-only smoke)*
