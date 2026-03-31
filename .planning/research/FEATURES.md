# Feature Research

**Domain:** CMS Composite Workflow N+1 Query Elimination
**Researched:** 2026-03-31
**Confidence:** HIGH

## Context: What Exists Today

Four CMS composite functions aggregate data across Juniper CMS models (routing, interfaces, firewalls). They are invoked via `nautobot_run_workflow` (workflow layer) or directly via CLI (`cms routing bgp-summary`, `cms routing routing-table`, `cms interfaces detail`, `cms firewalls firewall-summary`).

Each returns `(response_model, warnings_list)` and is wired into `WORKFLOW_REGISTRY` in `workflows.py`.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Correct per-composite output shape** | Agents depend on consistent `groups[]`, `routes[]`, `units[]`, `filters[]` arrays | LOW | Already correct — no change needed |
| **Graceful degradation on partial API failures** | Single CMS endpoint timeout should not kill entire composite | LOW | `WarningCollector` pattern already in place; N+1 fix must preserve it |
| **`detail=True` inline enrichment** | Users want full nested data without N round-trips | MEDIUM | `bgp_summary` already has AF/policy guards (v1.9); `firewall_summary` still has per-filter/per-policer loops |
| **`limit=N` per-array independent capping** | Agents paginate sub-arrays without capping top-level array | LOW | Already implemented in all 4 composites |

### Differentiators (Competitive Advantage)

Features that set the product apart.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Eliminate N+1 in `get_interface_detail`** | ULTRA-FIX: 200+ unit devices currently cause 200+ family fetches — the worst N+1 pattern in the codebase | MEDIUM-HIGH | 1 bulk family fetch (device-scoped) replaces N family fetches (per-unit); `_get_vrrp_for_family` memoization already in place but useless without families being bulk-fetched first |
| **Eliminate N+1 in `get_device_firewall_summary` (detail mode)** | Per-filter term loop + per-policer action loop — O(F+P) sequential calls | MEDIUM | 1 bulk terms fetch (device-scoped) + 1 bulk actions fetch replaces O(F) + O(P) calls |
| **Eliminate N+1 in `get_device_routing_table`** | Per-route fallback for nexthop lookups (backward-compat fallback for routes absent from bulk map) | MEDIUM | Already has bulk fetches; the fallback loop fires for every route missing from bulk map — needs to be removed or made conditional |
| **Preserve backward-compatible test mocks in `list_static_routes`** | The per-route fallback exists solely to satisfy old unit test mocks | LOW | Remove fallback loop once tests are updated to provide bulk-compatible data |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Bulk-fetch unbounded result sets regardless of device size** | "Fetch everything in 1 call" sounds optimal | Large devices (700+ units/interfaces) would create huge payloads, strain Nautobot server, and inflate MCP client memory | Keep conservative per-device limits (e.g., device-scoped bulk fetch, not global); already partially in place via `_CMS_BULK_LIMIT=200` |
| **Global (non-device-scoped) bulk fetches for AF/policy enrichment** | Simpler code — fetch all AFs once without filter | AF/policy endpoints timeout at >60s globally (even `limit=1`); returning all AFs across all devices for a device-scoped workflow is wasteful | Device-scoped bulk fetches for AF/policy — but the Nautobot CMS plugin may not support `device=` filter on these endpoints |
| **Remove all fallback patterns entirely** | "Clean code" aesthetic | Tests and real environments differ; some routes may not appear in bulk results due to ordering/offset edge cases | Keep fallback behind a feature flag or environment variable, or fix the tests |

---

## Exact N+1 Call Chain Analysis

### `get_device_bgp_summary` (routing.py → `cms/routing.py`)

```
workflows.py: run_workflow("bgp_summary", {device, detail, limit})
  └─ routing.py: get_device_bgp_summary(client, device, detail, limit)
       ├─ resolve_device_id(client, device)              [1 call]
       ├─ list_bgp_groups(client, device=id, limit=0)    [1 call]
       │    └─ cms_list("juniper_bgp_groups", ...)       [1 HTTP]
       ├─ list_bgp_neighbors(client, device=id, limit=0) [1 call]
       │    └─ cms_list("juniper_bgp_neighbors", ...)    [1 HTTP]
       │
       └─ if detail AND all_neighbors:
            ├─ list_bgp_address_families(client, limit=0)         [1 HTTP — 60s+ timeout fixed v1.9]
            └─ list_bgp_policy_associations(client, limit=0)      [1 HTTP — 60s+ timeout fixed v1.9]
            │
            └─ for each neighbor (only if af_keyed_usable=False and af_bulk_failed=False):
                 ├─ list_bgp_address_families(client, neighbor_id=nbr.id)   [N fallback calls — guarded]
                 └─ list_bgp_policy_associations(client, neighbor_id=nbr.id) [N fallback calls — guarded]
```

**Status: v1.9 already fixed the worst AF/policy timeout.** Remaining N+1 risk is the per-neighbor fallback loop when `af_keyed_usable=False`. However, HQV-PE1-NEW has 0 BGP groups so the fallback path is not triggered. On devices with BGP groups but AF/policy data not keyed by `neighbor_id`, this could be O(N) extra calls.

---

### `get_device_routing_table` (routing.py → `cms/routing.py`)

```
workflows.py: run_workflow("routing_table", {device, detail, limit})
  └─ routing.py: get_device_routing_table(client, device, detail, limit)
       └─ list_static_routes(client, device, limit=0)
            ├─ resolve_device_id(client, device)                           [1 call]
            ├─ cms_list("juniper_static_routes", device=id, limit=0)       [1 HTTP]
            │
            ├─ cms_list("juniper_static_route_nexthops", device=id, limit=0) [1 HTTP]  ← bulk map
            ├─ cms_list("juniper_static_route_qualified_nexthops", device=id, limit=0) [1 HTTP] ← bulk map
            │
            └─ for each route (if route not in bulk map):
                 ├─ cms_list("juniper_static_route_nexthops", route=route.id)      [N fallback]
                 └─ cms_list("juniper_static_route_qualified_nexthops", route=id) [N fallback]
```

**N+1 pattern: Per-route fallback.** The bulk map is populated first, then for every route whose ID is absent from the map, two extra calls are made. This is the "backward-compatible fallback for routes absent from bulk map" — it exists because some test mocks don't populate the bulk map.

**Correct behavior:** If bulk fetch returns results, use them. The fallback should only fire when the bulk fetch itself failed (exception path), not as a correctness path for routes missing from the map.

---

### `get_interface_detail` (interfaces.py → `cms/interfaces.py`)

```
workflows.py: run_workflow("interface_detail", {device, detail, include_arp, limit})
  └─ interfaces.py: get_interface_detail(client, device, detail, include_arp, limit)
       ├─ resolve_device_id(client, device)                           [1 call]
       ├─ list_interface_units(client, device=id, limit=0)             [1 HTTP]
       │    └─ cms_list("juniper_interface_units", device=id, limit=0) [1 HTTP]
       │
       └─ for each unit:
            └─ list_interface_families(client, unit_id=unit.id)       [N calls — THE MAJOR N+1]
                 └─ cms_list("juniper_interface_families", unit_id=unit.id) [N HTTP]
       │
       └─ _get_vrrp_for_family(family_id) — called for each family, memoized
            └─ list_vrrp_groups(client, family_id=family_id)          [M calls, cached after 1st]
       │
       └─ if include_arp: list_arp_entries(client, device=id)          [1 HTTP]
```

**N+1 pattern: Per-unit family fetch.** The biggest remaining N+1 in the codebase. For HQV-PE1-NEW (709 interfaces), this creates 709 sequential HTTP calls just for families.

**Correct behavior:** Replace the per-unit family fetch loop with a single device-scoped bulk family fetch:
```
all_families = cms_list("juniper_interface_families", device=id, limit=0)  [1 HTTP]
group by unit_id in memory
```

Then `_get_vrrp_for_family` memoization becomes effective (same family IDs appear across units).

---

### `get_device_firewall_summary` (firewalls.py → `cms/firewalls.py`)

```
workflows.py: run_workflow("firewall_summary", {device, detail, limit})
  └─ firewalls.py: get_device_firewall_summary(client, device, detail, limit)
       ├─ resolve_device_id(client, device)                              [1 call]
       ├─ list_firewall_filters(client, device=id, limit=0)              [1 HTTP]
       │    └─ cms_list("juniper_firewall_filters", device=id, limit=0)  [1 HTTP]
       │    └─ cms_list("juniper_firewall_terms", device=id, limit=0)    [1 HTTP] ← bulk term count ✓
       │
       ├─ list_firewall_policers(client, device=id, limit=0)             [1 HTTP]
       │    └─ cms_list("juniper_firewall_policers", device=id, limit=0) [1 HTTP]
       │    └─ cms_list("juniper_firewall_policer_actions", device=id, limit=0) [1 HTTP] ← bulk action count ✓
       │
       └─ if detail:
            ├─ for each filter:
            │    └─ list_firewall_terms(client, filter_id=fw_filter.id)     [F sequential calls]
            │         └─ cms_list("juniper_firewall_terms", filter=id)       [F HTTP]
            │         └─ cms_list("juniper_firewall_match_conditions", filter=id) [F HTTP]
            │         └─ cms_list("juniper_firewall_actions", filter=id)      [F HTTP]
            │
            └─ for each policer:
                 └─ list_firewall_policer_actions(client, policer_id=policer.id) [P sequential calls]
                      └─ cms_list("juniper_firewall_policer_actions", policer=id) [P HTTP]
```

**N+1 pattern: Per-filter and per-policer sequential enrichment.** `detail=True` makes O(F+P) sequential HTTP calls.

**Correct behavior:** In `detail=True` mode, replace per-filter/per-policer enrichment with:
1. One bulk `juniper_firewall_terms` (device-scoped) → group by `filter_id` in memory
2. One bulk `juniper_firewall_match_conditions` (device-scoped) → group by `term_id` in memory
3. One bulk `juniper_firewall_actions` (device-scoped) → group by `term_id` in memory
4. One bulk `juniper_firewall_policer_actions` (device-scoped) → group by `policer_id` in memory

This reduces `detail=True` from O(F+P+3F) HTTP calls to 5 total.

---

## Feature Dependencies

```
[bulk_family_fetch_for_interface_detail]
    └──requires──> [remove per-unit list_interface_families loop]
                        └──requires──> [update tests that rely on per-unit fetch shape]

[bulk_term_fetch_for_firewall_detail]
    └──requires──> [update tests that rely on per-filter term enrichment shape]

[remove_route_fallback_loop]
    └──requires──> [update test mocks to provide bulk-compatible route data]

[bgp_af_policy_conditional_fallback]
    └──enhances──> [get_device_bgp_summary]
                       └──conflicts──> [none — backward compat only]
```

### Dependency Notes

- **Bulk family fetch requires removing the per-unit `list_interface_families` loop:** The loop is the source of the N+1; replacing it with device-scoped bulk fetch is the fix.
- **Tests need updating for all three composites:** Existing tests mock the per-item fetch patterns; after fixing to bulk, test mocks must provide bulk-compatible data. Tests should verify the bulk fetch is called once, not N times.
- **`bgp_summary` fallback loop is guarded:** The per-neighbor AF/policy fallback only fires when `af_keyed_usable=False` and `af_bulk_failed=False`. This is a narrow edge case; priority is lower than `interface_detail` and `firewall_summary`.
- **No conflict between composites:** Each composite is independently fixed; fixing one does not break another.

---

## Correct Behavior Per Composite

### `get_interface_detail`

| Mode | Current | Correct |
|------|---------|---------|
| `detail=True` (default) | 1 (units) + N (families, per-unit) + M (VRRP, cached per family) | 1 (units) + 1 (all families, device-scoped) + M (VRRP, cached per family) |
| `detail=False` | 1 (units) + N (families, per-unit, for VRRP count) | 1 (units) + 1 (all families, device-scoped) + M (VRRP, cached) |

**Expected HTTP call reduction:** For 700-unit device: 701 → ~3 calls.

---

### `get_device_firewall_summary`

| Mode | Current | Correct |
|------|---------|---------|
| `detail=False` | 1 (filters) + 1 (terms bulk) + 1 (policers) + 1 (actions bulk) = 4 ✓ | Same — already optimal |
| `detail=True` | 4 + F (per-filter terms) + P (per-policer actions) | 4 + 1 (bulk terms) + 1 (bulk match-conditions) + 1 (bulk actions) + 1 (bulk policer-actions) = 8 |

**Note:** In `detail=False` mode, `firewall_summary` is already near-optimal — bulk term/action count fetches are already in place.

---

### `get_device_routing_table`

| Mode | Current | Correct |
|------|---------|---------|
| Always | 1 (routes) + 1 (nexthops bulk) + 1 (qualified nexthops bulk) + N fallback | 1 (routes) + 1 (nexthops bulk) + 1 (qualified nexthops bulk) |

**Expected HTTP call reduction:** For 100-route device: 102+N → 3 calls (N=0 when bulk map is complete).

---

### `get_device_bgp_summary`

| Mode | Current | Correct |
|------|---------|---------|
| `detail=False` (default) | 1 (groups) + 1 (neighbors) = 2 ✓ | Same — already optimal |
| `detail=True` + keyed AF/policy data | 2 + 1 (AF bulk) + 1 (policy bulk) = 4 ✓ | Same — already optimal |
| `detail=True` + unkeyed (edge case) | 2 + 1 + 1 + O(N) fallback per neighbor | Guard fallback behind `af_keyed_usable=False AND all_afs_results non-empty` — fallback should only fire when bulk returned data but it couldn't be keyed |

**Priority:** LOW. The primary path (detail=False, or detail=True with keyed data) is already efficient. The fallback path is a narrow edge case.

---

## MVP Definition

### Launch With (v1.10)

Minimum viable product — what's needed to validate N+1 elimination.

- [ ] `get_interface_detail` — replace per-unit family fetch with single device-scoped bulk family fetch; update VRRP memoization to use pre-built family map; add/fix unit tests to verify bulk behavior
- [ ] `get_device_firewall_summary` detail=True — replace per-filter/per-policer loops with 1 bulk terms + 1 bulk match-conditions + 1 bulk actions + 1 bulk policer-actions; update tests
- [ ] `get_device_routing_table` — remove per-route fallback loop (backward compat path only); update test mocks to provide bulk-compatible data
- [ ] Smoke test regression gate: all 4 composites pass within current v1.9 thresholds on HQV-PE1-NEW (bgp_summary < 5s, routing_table < 5s, firewall_summary < 5s, interface_detail < 10s)

### Add After Validation (v1.11)

- [ ] `get_device_bgp_summary` edge-case fallback guard — conditionalize per-neighbor AF/policy fallback behind stricter `af_keyed_usable=False AND not all_afs_results` check; add unit tests for unkeyed scenario

### Future Consideration (v2+)

- [ ] Global performance dashboard — aggregate HTTP call counts across all workflows for all devices to proactively detect regressions
- [ ] Per-device pagination for `interface_detail` — large devices (700+ units) could paginate families by unit in chunks if memory is a concern

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| `interface_detail` — bulk family fetch | HIGH — 700+ unit devices go from 700+ calls to 3 | MEDIUM — logic change + test updates | P1 |
| `firewall_summary` detail — bulk term/action fetch | HIGH — eliminates O(F+P) sequential calls | MEDIUM — 4 new bulk fetch paths + test updates | P1 |
| `routing_table` — remove per-route fallback | MEDIUM — prevents spurious N extra calls on well-populated devices | LOW — remove fallback loop + update test mocks | P1 |
| `bgp_summary` edge-case fallback guard | LOW — primary path already optimal | LOW — refine guard condition + edge-case tests | P2 |

**Priority key:**
- P1: Must have for v1.10 — ship quality gate
- P2: Should have — add as refinement after P1 passes
- P3: Nice to have — future consideration

---

## Sources

- `nautobot_mcp/cms/routing.py` — `get_device_bgp_summary`, `get_device_routing_table`, `list_static_routes`
- `nautobot_mcp/cms/interfaces.py` — `get_interface_detail`, `list_interface_units`, `get_interface_unit`
- `nautobot_mcp/cms/firewalls.py` — `get_device_firewall_summary`, `list_firewall_filters`, `list_firewall_terms`
- `nautobot_mcp/cms/client.py` — `cms_list`, `_CMS_BULK_LIMIT = 200`, `resolve_device_id`
- `nautobot_mcp/workflows.py` — `WORKFLOW_REGISTRY`, `run_workflow`
- `.planning/PROJECT.md` — v1.9 Phase 34 validated decisions, v1.10 active milestone

---
*Feature research for: CMS N+1 Query Elimination*
*Researched: 2026-03-31*
