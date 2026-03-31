# Phase 37: `routing_table` + `bgp_summary` N+1 Fixes - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Eliminate N+1 HTTP query loops in two CMS composite functions in `nautobot_mcp/cms/routing.py`:

1. **`get_device_routing_table`** — Remove per-route nexthop fallback loop (L96-120 in `list_static_routes`). Bulk nexthop map is considered complete — no per-route calls needed.
2. **`get_device_bgp_summary`** — Verify per-neighbor AF/policy fallback guards (L734-751). Existing guards are sufficient; CQP-04 is already satisfied.

Goals: CQP-03 (≤3 HTTP calls for routing_table), CQP-04 (AF/policy guards in bgp_summary), CQP-05 (WarningCollector preserved).

Out of scope: Other CMS workflows, global bulk fetches, async rewrite.

</domain>

<decisions>
## Implementation Decisions

### routing_table Fallback Removal (CQP-03)
- **D-01:** Remove the per-route nexthop fallback loop entirely (L96-120 in `list_static_routes`). Bulk nexthop map at L79-82 and bulk qualified nexthop map at L87-90 are the complete source of truth. No per-route HTTP calls under any condition.
- **D-02:** If bulk fetch fails (exception caught at L84-85/L91-92), set `nh_by_route = {}` / `qnh_by_route = {}` silently. Routes with no nexthop data return empty lists. This is graceful degradation for non-critical enrichment (nexthops enrich routes, not co-primary data).
- **D-03:** "Backward-compatible fallback" comment (L94-95) is a test artifact only. Update test mocks to include bulk data so tests pass without the fallback loop.

### routing_table HTTP Call Budget (CQP-03)
- **D-04:** Target: ≤3 HTTP calls in `get_device_routing_table`:
  1. `list_static_routes(..., device=device_id)` (routes list)
  2. `cms_list(..., device=device_id)` for nexthops (bulk — 1 call, not 1 per route)
  3. `cms_list(..., device=device_id)` for qualified nexthops (bulk — 1 call, not 1 per route)

### bgp_summary Guard Hardening (CQP-04)
- **D-05:** Existing guard pattern at L734/L741 is sufficient. Guard conditions: `(not fam_list) AND (not af_bulk_failed) AND (af_keyed_usable)` / `(not pol_list) AND (not pol_bulk_failed) AND (pol_keyed_usable)`. No code changes needed — CQP-04 is already satisfied.
- **D-06:** Guard #1 at L687: `if detail and all_neighbors:` already prevents timeout on devices with no BGP groups. This is confirmed correct and should not be changed.

### Unit Test Strategy
- **D-07:** New combined test file: `tests/test_cms_routing_n1.py` covering N+1 invariants for BOTH `get_device_routing_table` and `get_device_bgp_summary`. Consolidating into one file reduces maintenance overhead vs two separate files.
- **D-08:** Follow Phase 35/36 pattern: monkey-patch `cms_list` in the routing module to count HTTP calls, assert ≤N regardless of how many routes/nexthops/neighbors/AFs are in the mocked responses.
- **D-09:** Routing N+1 test: assert exactly 3 calls with mock data (routes + 2 bulk nexthops). Include test where bulk nexthop fetch returns empty — assert routes still return without per-route fallback calls.
- **D-10:** BGP N+1 test: assert guards prevent per-neighbor calls when device has no neighbors. Assert ≤6 calls with detail=True and many neighbors/AFs/policies.

### Cross-cutting: CQP-05 Compliance
- **D-11:** All N+1 fixes in Phase 37 preserve `WarningCollector` partial-failure behavior. Nexthop bulk fetch failure uses silent graceful degradation (non-critical enrichment). BGP guards already handle failures via `collector.add()`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 37 Requirements
- `.planning/ROADMAP.md` §v1.10 — Phase 37 goals: CQP-03 (≤3 calls routing_table), CQP-04 (bgp guards), CQP-05 (WarningCollector)
- `.planning/REQUIREMENTS.md` §CQP — CQP-03 (≤3 HTTP calls), CQP-04 (AF/policy guards), CQP-05 (WarningCollector preserved)
- `.planning/STATE.md` — Root cause: per-route nexthop fallback loop in list_static_routes; Phase 35/36 precedent

### Prior Phase Decisions
- `.planning/phases/33-cms-pagination-fix/33-CONTEXT.md` — `_CMS_BULK_LIMIT = 200` constant
- `.planning/phases/35-interface-detail-n1-fix/35-CONTEXT.md` — Inline prefetch pattern, graceful degradation for non-critical, dedicated test file
- `.planning/phases/36-firewall-summary-n1-fix/36-CONTEXT.md` — Combined test files, co-primaries pattern

### Codebase References
- `nautobot_mcp/cms/routing.py` — `list_static_routes()` (L45-128) — PRIMARY fix target (remove L96-120 fallback)
- `nautobot_mcp/cms/routing.py` — `get_device_routing_table()` (L782-835) — calls list_static_routes, ≤3 call target
- `nautobot_mcp/cms/routing.py` — `get_device_bgp_summary()` (L639-779) — Verify guards at L687, L709-711, L734-751
- `nautobot_mcp/cms/client.py` — `cms_list()` (L135-168) — already handles `_CMS_BULK_LIMIT = 200`
- `nautobot_mcp/warnings.py` — `WarningCollector` — already imported in routing.py

### Test References
- `tests/test_cms_interfaces_n1.py` — Phase 35 N+1 pattern (to replicate for routing)
- `tests/test_cms_firewalls_n1.py` — Phase 36 N+1 pattern (to replicate for bgp)
- `scripts/uat_cms_smoke.py` — existing smoke test for routing_table + bgp_summary workflows

</canonical_refs>

<codebase_context>
## Existing Code Insights

### Reusable Assets
- Bulk nexthop fetch pattern already exists in `list_static_routes` L79-92 — just need to remove the fallback that bypasses it
- `WarningCollector` already imported in routing.py — only need to use it for nexthop bulk fetch failure
- Phase 35 `test_cms_interfaces_n1.py` monkey-patch pattern can be directly copied for routing N+1 tests

### Established Patterns
- Inline prefetch (Phase 35): prefetch block immediately after co-primary fetches, before per-item enrichment
- Graceful degradation for non-critical: try/except → empty dict, no warning needed for nexthops
- WarningCollector for critical failures: `collector.add(key, str(e))` pattern
- Bulk + lookup dict: `bulk_results = cms_list(...); lookup = {item.route_id: [...] for item in bulk_results}`

### Integration Points
- `get_device_routing_table` called by: `workflows.py` `routing_table` workflow, CLI `nautobot-mcp --json cms routing routing-table`
- `get_device_bgp_summary` called by: `workflows.py` `bgp_summary` workflow, CLI `nautobot-mcp --json cms routing bgp-summary`
- Return types unchanged: `tuple[RoutingTableResponse, list]`, `tuple[BGPSummaryResponse, list]`

### Key Code Observations
- Routing N+1: The fallback at L96-120 fires when `route.id not in nh_by_route`. Since the bulk fetch at L79-82 gets ALL nexthops for ALL routes on the device, `route.id` should always be in `nh_by_route` unless the CMS plugin data is incomplete. Removing the fallback exposes incomplete CMS data rather than silently paper over it.
- BGP guards: L709 `neighbor_ids = {n.id for n in all_neighbors}` captures all neighbor IDs first. L710-711 check if any AF/policy has a `neighbor_id` in that set. L734/L741 use `af_keyed_usable`/`pol_keyed_usable` to gate per-neighbor fallback. This triple-guard (bulk failed flag + keyed usable check + not empty list) is correct.

</codebase_context>

<specifics>
## Specific Ideas

- "Remove fallback entirely — bulk is the source of truth. If CMS plugin data is incomplete, that's a plugin issue to fix, not a code workaround."
- "Nexthop graceful degradation: if bulk fetch fails, silent empty dict — nexthops are enrichment, not co-primary"
- "Test mocks for routing: include `juniper_static_route_nexthops` and `juniper_static_route_qualified_nexthops` in bulk responses so tests pass without fallback"
- "BGP guards already correct: no code changes needed for CQP-04"

</specifics>

<deferred>
## Deferred Ideas

### Reviewed Todos (not matched)
No pending todos matched Phase 37 scope.

### Scope Deferred
- `get_bgp_neighbor` per-neighbor fallback — Phase 37 focuses on `get_device_bgp_summary` guards verification; `list_bgp_neighbors` has its own fallback pattern (L460-470) for environments without device filter support, deferred separately
- `list_static_route_nexthops` standalone function — the CRUD endpoint itself still exists and works, but the N+1 is in `list_static_routes` which is the composite caller

---

*Phase: 37-routing-table-bgp-n1-fixes*
*Context gathered: 2026-03-31*
