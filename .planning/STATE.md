---
gsd_state_version: 1.0
milestone: v1.10
milestone_name: CMS N+1 Query Elimination
status: planning
last_updated: "2026-03-31T00:00:00.000Z"
last_activity: 2026-03-31
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State: nautobot-mcp-cli

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-31)

**Core value:** AI agents can discover, read, write, and orchestrate Nautobot data through 3 tools instead of 165
**Current focus:** Phase 1 planning — CMS N+1 Query Elimination

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-31 — Milestone v1.10 started

## Context

**Root causes from investigation (2026-03-31):**

Three N+1 patterns identified across the 4 failing CMS workflows:

1. **`interface_detail`** (interfaces.py ~line 690): Bulk-fetches interface families once, then **discards the result** and refetches families one-by-one per unit. With ~2,000 units: ~2,000 HTTP requests. Then also makes one VRRP call per family: another ~2,000 requests.

2. **`routing_table`** (routing.py ~line 96): After bulk-fetching nexthops, loops over every route and fires `cms_list(route=<id>)` for uncovered routes. With thousands of routes: 2 × N_routes extra HTTP requests.

3. **Sequential `limit=0` calls** (all CMS composites): `_CMS_BULK_LIMIT = 200` reduces N+1 to ceil(N/200), but these are still sequential. Four such calls × slow CMS plugin = >120s for `firewall_summary`.

**Current HQV-PE1 smoke test results (before fix):**
- devices_inventory: PASS (8,246ms < 15,000ms)
- bgp_summary: FAIL (39,510ms > 5,000ms)
- routing_table: FAIL (115,096ms > 15,000ms)
- firewall_summary: FAIL (timeout >120s)
- interface_detail: FAIL (timeout >120s)

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| No research needed | Root causes already identified; fix scope is well-understood |
| Focus on eliminating N+1 loops | Not just tuning — fix the algorithm, not the constants |

## Accumulated Context

- v1.0 shipped 2026-03-18 with core MCP + CLI + parsing/onboarding foundations
- v1.1 shipped 2026-03-20 with agent-native tools and file-free drift
- v1.2 shipped 2026-03-21 with Juniper CMS CRUD + composite tools + CMS drift
- v1.3 shipped 2026-03-25 with 165→3 API Bridge consolidation
- v1.4 shipped 2026-03-26 with robustness, diagnostics, and response ergonomics
- v1.6 shipped 2026-03-28 with query performance optimizations
- v1.7 shipped 2026-03-29 with URI limit fixes, VLANs 500 fix, and UAT smoke script
- v1.8 shipped 2026-03-30 with CMS pagination fix (_CMS_BULK_LIMIT)
- v1.9 shipped 2026-03-30 with AF/policy gating and CLI default limit fix
- v1.10 started 2026-03-31 to eliminate remaining N+1 patterns

## Blockers

None.

---
*State initialized: 2026-03-28*
*Last updated: 2026-03-31 — v1.10 milestone started*
