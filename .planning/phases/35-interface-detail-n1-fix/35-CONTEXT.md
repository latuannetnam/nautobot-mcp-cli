# Phase 35: `interface_detail` N+1 Fix - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Eliminate N+1 HTTP query loops in `get_interface_detail()` in `nautobot_mcp/cms/interfaces.py`. Two specific patterns:

1. **Per-unit family refetch (N+1 #1):** `list_interface_families(unit_id=unit.id)` called per-unit in a loop (L690-692). With ~2,000 units on HQV-PE1: ~2,000 HTTP calls instead of 1.
2. **Per-family VRRP loop (N+1 #2):** `_get_vrrp_for_family()` calls `list_vrrp_groups(family_id=family_id)` per family (L700). With ~2,000 families: ~2,000 VRRP HTTP calls.

Goal (CQP-01): `get_interface_detail` makes ≤3 HTTP calls regardless of device unit count — 1 bulk units, 1 bulk families, 1 bulk VRRP.

Out of scope: `list_interface_units` family_count bulk fetch (already correct), `list_interface_units` itself, other CMS workflows.

</domain>

<decisions>
## Implementation Decisions

### Family Prefetch Strategy
- **D-01:** Bulk family prefetch lives **inside `get_interface_detail` only**. Do NOT refactor `list_interface_units` to return a shared lookup map. Do NOT create a new shared helper. The duplicate bulk fetch between `list_interface_units` and `get_interface_detail` is acceptable — they serve different data needs (counts vs full objects).

### VRRP Prefetch Boundary
- **D-02:** Bulk VRRP prefetch in `get_interface_detail`: 1 bulk call to `juniper_vrrp_groups` for the device, build `family_id → VRRPGroup[]` lookup map. Replace `_get_vrrp_for_family()` HTTP call with a map lookup. No per-family HTTP calls.

### Partial Failure Handling (CQP-05)
- **D-03:** Family prefetch failure → hard-fail (propagate exception). Family data is critical for the `detail=True` enrichment path — returning an empty map would produce a misleading response.
- **D-04:** VRRP prefetch failure → graceful degradation: catch exception, `WarningCollector.add("bulk_vrrp_fetch", str(e))`, return empty `{}` map. VRRP is non-critical enrichment — existing VRRP memoization pattern already handles this gracefully (L699-704).

### HTTP Call Budget (CQP-01)
- **D-05:** Target: exactly 3 bulk HTTP calls in `get_interface_detail` for a fully-enriched response:
  1. `list_interface_units` (1 call, existing)
  2. Bulk families prefetch: `cms_list(..., device=device_id)` (1 new call)
  3. Bulk VRRP prefetch: `cms_list(..., device=device_id)` (1 new call)

### Structure
- **D-06:** Prefetch block comes immediately after `units_resp` fetch, before any unit processing loop. Family lookup map built first, then VRRP lookup map. `_get_vrrp_for_family` updated to use the VRRP map (cache remains for backward compat with `get_interface_unit` which still uses per-family VRRP calls).

### Cross-cutting: CQP-05 Compliance
- **D-07:** All N+1 fixes in Phase 35 preserve `WarningCollector` partial-failure behavior. VRRP graceful degradation is the only exception point (non-critical enrichment).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 35 Requirements
- `.planning/ROADMAP.md` §v1.10 — Phase 35 goal: CQP-01 (≤3 HTTP calls), CQP-05 (WarningCollector preserved)
- `.planning/REQUIREMENTS.md` §CQP — CQP-01 (≤3 HTTP calls), CQP-05 (WarningCollector preserved)
- `.planning/STATE.md` — Root cause: per-unit family refetch (~2,000 calls), per-family VRRP (~2,000 calls)

### Prior Phase Decisions
- `.planning/phases/33-cms-pagination-fix/33-CONTEXT.md` — `_CMS_BULK_LIMIT = 200` constant, bulk fetch via `cms_list()` with limit override
- `.planning/phases/30-direct-http-bulk-fetch/30-CONTEXT.md` — Direct HTTP + `return_obj()` + bulk fetch patterns
- `.planning/phases/19-partial-failure-resilience/19-CONTEXT.md` — `WarningCollector` pattern and partial failure philosophy

### Codebase References
- `nautobot_mcp/cms/interfaces.py` — `get_interface_detail()` (L658-761) — PRIMARY fix target
- `nautobot_mcp/cms/interfaces.py` — `list_interface_units()` (L45-91) — existing bulk family fetch for `family_count`, do NOT modify
- `nautobot_mcp/cms/interfaces.py` — `_get_vrrp_for_family()` (L696-705) — existing memoization, replace HTTP call with map lookup
- `nautobot_mcp/cms/client.py` — `cms_list()` (L135-168) — already handles `_CMS_BULK_LIMIT = 200` correctly
- `nautobot_mcp/cms/client.py` — `CMS_ENDPOINTS` registry (L27-72) — endpoint names for families and VRRP
- `nautobot_mcp/warnings.py` — `WarningCollector` — already imported in `interfaces.py`

### Test/Verification
- `scripts/uat_cms_smoke.py` — existing smoke test infrastructure for `interface_detail` workflow
- `nautobot_mcp/workflows.py` — `interface_detail` workflow stub (L110-113)

</canonical_refs>

<codebase_context>
## Existing Code Insights

### Reusable Assets
- `cms_list(client, "juniper_interface_families", InterfaceFamilySummary, device=device_id, limit=0)` — already used in `list_interface_units`; pattern proven for bulk family fetch
- `cms_list(client, "juniper_vrrp_groups", VRRPGroupSummary, device=device_id, limit=0)` — correct endpoint for bulk VRRP fetch (registered in `CMS_ENDPOINTS` as `"juniper_vrrp_groups"`)
- `WarningCollector` already imported and wired in `get_interface_detail` — only need to use it for VRRP prefetch failure

### Established Patterns
- Bulk fetch + lookup map: `list_interface_units` L68-80 already does this for `family_count_by_unit`; apply same pattern for full family objects
- VRRP memoization: `_get_vrrp_for_family` already exists (L696-705); replace internal HTTP call with map lookup
- Graceful VRRP degradation: exception handling in `_get_vrrp_for_family` already returns `[]` on failure; preserve this pattern
- Hard-fail for critical data: `list_interface_units` already hard-fails if bulk families fetch fails (L84-86 `pass` still propagates outer exception); apply same to family prefetch in `get_interface_detail`

### Integration Points
- `get_interface_detail` is called by: `workflows.py` `interface_detail` workflow stub (L110-113), CLI `nautobot-mcp --json cms interfaces detail`
- Return type: `tuple[InterfaceDetailResponse, list[dict]]` — no change
- `_get_vrrp_for_family` is also used by `get_interface_unit` (L153 `get_interface_unit` calls it indirectly via families enrichment) — `_get_vrrp_for_family` behavior must remain for that path too

### Key Observation
- `list_interface_units` (L68-80) already bulk-fetches families and builds `family_count_by_unit` map. This is NOT the N+1 — it's a correct bulk fetch. The N+1 is in `get_interface_detail` which calls `list_interface_families` per unit, bypassing the `list_interface_units` bulk fetch entirely.
- `InterfaceUnitSummary` has `family_count` field (int) — does NOT have full family objects. `get_interface_detail` with `detail=True` needs full family objects, which `list_interface_units` does not provide.

</codebase_context>

<specifics>
## Specific Ideas

- "Bulk VRRP prefetch: use `cms_list(client, 'juniper_vrrp_groups', VRRPGroupSummary, device=device_id, limit=0)` — same `device=device_id` filter as units/families"
- "VRRP graceful degradation already works via `_get_vrrp_for_family` exception handling — just need to wire in the prefetched map"
- "Test device: HQV-PE1-NEW (~2,000 units, ~2,000 families, VRRP on some families) — primary regression target"
- "Performance target: interface_detail on HQV-PE1-NEW should complete in <5s instead of current timeout"

</specifics>

<deferred>
## Deferred Ideas

### Reviewed Todos (not matched)
No pending todos matched Phase 35 scope.

### Scope Deferred
- `get_interface_unit` VRRP enrichment — Phase 35 fixes `get_interface_detail` VRRP; `get_interface_unit` still uses per-family VRRP calls. Fix it in a future phase if needed.
- `list_interface_units` deduplication — keeping the separate bulk family fetch in `list_interface_units` means two bulk family fetches per `get_interface_detail` call. Future phase could refactor `list_interface_units` to share the lookup map, but not in Phase 35 scope.

</deferred>

---

*Phase: 35-interface-detail-n1-fix*
*Context gathered: 2026-03-31*
