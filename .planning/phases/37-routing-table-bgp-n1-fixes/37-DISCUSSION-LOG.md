# Phase 37: `routing_table` + `bgp_summary` N+1 Fixes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-31
**Phase:** 37-routing-table-bgp-n1-fixes
**Mode:** discuss
**Areas discussed:** routing_table fallback strategy, routing_table HTTP call budget, bgp_summary guard hardening, Unit test strategy

---

## routing_table Fallback Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Remove fallback entirely | Bulk nexthop map is complete. Update test mocks. Simplest path. | ✓ |
| Keep as defensive fallback | Remove N+1 in production but keep for edge cases. Existing test mocks. | |

**User's choice:** Remove fallback entirely
**Recommendation provided:** Yes — user asked for recommendation. Advised removal because: (1) bulk fetch is complete and exhaustive, (2) `_CMS_BULK_LIMIT = 200` handles large counts efficiently, (3) Phase 35 precedent uses hard-fail for incomplete data, (4) keeping fallback defeats the N+1 fix if CMS returns incomplete data, (5) "backward-compatible fallback" is a test artifact.

---

## routing_table HTTP Call Budget

| Option | Description | Selected |
|--------|-------------|----------|
| ≤3 calls (recommended) | 1 routes + 1 bulk nexthops + 1 bulk qualified nexthops. Clean co-primary pattern. | ✓ |
| ≤4 calls (defensive) | Same + conditional fallback for edge cases. More defensive but risks defeating the fix. | |

**User's choice:** ≤3 calls (recommended)

---

## bgp_summary Guard Hardening

| Option | Description | Selected |
|--------|-------------|----------|
| Existing guards sufficient | Guard pattern: (not bulk_failed) AND (keyed_usable) AND (not empty list). CQP-04 already satisfied. | ✓ |
| Need stricter length checks | Add explicit len() checks per CQP-04 text. More verbose but defensive. | |

**User's choice:** Existing guards sufficient
**Notes:** Verified existing guards at L734/L741 match CQP-04 intent: triple-guard with bulk_failed flag, keyed_usable check, and empty list condition. No code changes needed.

---

## Unit Test Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| One combined file (recommended) | tests/test_cms_routing_n1.py covering both routing_table and bgp_summary. Consolidated maintenance. | ✓ |
| Two separate files | test_cms_routing_n1.py and test_cms_bgp_n1.py. More isolated, more files. | |

**User's choice:** One combined file (recommended)

---

## Claude's Discretion

- Exact exception handling for bulk nexthop fetch failure: silent empty dict vs WarningCollector warning — decided: silent graceful degradation (nexthops are non-critical enrichment)
- Specific mock data for routing N+1 test (how many routes, how many nexthops per route) — deferred to planner/executor
- BGP N+1 test mock data structure — deferred to planner/executor

## Deferred Ideas

- `list_bgp_neighbors` per-group fallback pattern (L460-470) — deferred to future phase; Phase 37 focuses on `get_device_bgp_summary` guard verification
- `list_static_route_nexthops` standalone CRUD endpoint — unchanged, N+1 is in the composite caller `list_static_routes`
