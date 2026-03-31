# Project Research Summary

**Project:** CMS N+1 Query Elimination (v1.10)
**Domain:** MCP Server / Nautobot CMS Plugin / HTTP Concurrency
**Researched:** 2026-03-31
**Confidence:** HIGH

## Executive Summary

Four CMS composite workflows (`bgp_summary`, `routing_table`, `firewall_summary`, `interface_detail`) aggregate Juniper CMS model data from Nautobot's CMS plugin. Three of them contain N+1 query patterns — sequential HTTP calls inside loops — that cause 60+ second latencies on high-interface-count devices. The fourth (`bgp_summary`) has a minor edge-case fallback guard that needs tightening.

The recommended approach is **bulk pre-fetch + in-memory distribution**: replace per-item CMS calls with a single device-scoped bulk fetch, then distribute results via dict lookups. This eliminates N+1 entirely without async/await rewrites, and is compatible with the existing `pynautobot` + `requests.Session` stack. A secondary `ThreadPoolExecutor` layer (proven in `devices.py` v1.6) parallelizes independent co-primary fetches. The biggest win is `get_interface_detail` on HQV-PE1-NEW: 709 interface units drive 709 sequential family fetches today → 1 bulk family fetch after the fix.

Key risks: **never** set `adapter.max_retries` globally (pynautobot already retries 3× internally; collision → 9 attempts/call), **never** use `max_workers > 5` for CMS calls (the plugin has unindexed slow queries; 20 parallel threads destabilizes the server), and **never** share a single `WarningCollector` across ThreadPoolExecutor workers (it's not thread-safe).

## Key Findings

### Recommended Stack

`concurrent.futures.ThreadPoolExecutor` (stdlib) is the sole concurrency primitive needed — no asyncio, no aiohttp, no new dependencies. pynautobot ≥ 2.3.0 already exposes `threading=True` and `max_workers=N` on the `Api` class for page-level parallel pagination, but that only helps when pages contain multiple records. The real fix is `_CMS_BULK_LIMIT = 200` (v1.8 Phase 33) collapsing per-record pagination into bulk fetches, combined with bulk pre-fetch at the composite function level. `requests.Session` is thread-safe for concurrent reads; the only rule is no session-level mutations inside worker threads.

**Core technologies:**
- `concurrent.futures.ThreadPoolExecutor` (stdlib): parallelize independent CMS co-primary fetches — already proven in `devices.py` v1.6
- `pynautobot` `threading=True` + `max_workers=N` (≥ 2.3.0): page-level pagination parallelism — useful but secondary to bulk pre-fetch
- `_CMS_BULK_LIMIT = 200` in `cms/client.py`: collapses PAGE_SIZE=1 CMS plugin pagination into ceil(N/200) HTTP calls — already deployed, foundation for all bulk patterns

### Expected Features

**Must have (table stakes):**
- `get_interface_detail` — bulk family fetch eliminates 700+ sequential calls per workflow run; update VRRP memoization to use pre-built family map
- `get_device_firewall_summary` detail mode — bulk terms + bulk match-conditions + bulk actions + bulk policer-actions replace O(F+P) sequential loops
- `get_device_routing_table` — remove per-route nexthop fallback loop (backward-compat path fires even when bulk map is globally empty)
- Smoke test regression gate — all 4 composites pass within v1.9 SLA thresholds on HQV-PE1-NEW

**Should have (competitive):**
- `get_device_bgp_summary` edge-case guard — refine per-neighbor AF/policy fallback guard from `any()` comprehension to strict `len(af_by_nbr) > 0`
- `uat_cms_smoke.py` HTTP call count assertions — block PRs if call count increases by >10% per workflow

**Defer (v2+):**
- Global performance dashboard — aggregate HTTP call counts across all workflows/devices to detect regressions proactively
- Per-device pagination for `interface_detail` — large devices (700+ units) could chunk families if memory becomes a concern

### Architecture Approach

The CMS client is a stateless helper module whose functions delegate to pynautobot, which uses a shared `requests.Session` with auth baked in. This session is thread-safe for reads and is the foundation for all ThreadPoolExecutor patterns. Four composite domain functions in `cms/routing.py`, `cms/interfaces.py`, and `cms/firewalls.py` are the N+1 culprits — each calls a list function, then loops to call child-enrichment functions per parent record. The fix is to pre-fetch all children at the device level upfront (one bulk `cms_list` call), group them by parent ID in a dict, then distribute in-memory inside the loop. The CLI and MCP workflow layers share the entire call stack, so a fix benefits both simultaneously with no extra work. `workflows.py` is a thin dispatcher — no changes needed there.

**Major components:**
1. `cms/client.py` — add `_cms_bulk_families_by_unit()`, `_cms_bulk_vrrp_by_family()`, `_cms_bulk_terms_by_filter()`, `_cms_bulk_actions_by_policer()` as reusable helpers
2. `cms/interfaces.py` — rewrite `get_interface_detail` to use bulk family + VRRP pre-fetch before the unit loop
3. `cms/firewalls.py` — rewrite `get_device_firewall_summary` detail loop to use bulk term + action pre-fetch before the filter/policer loop
4. `cms/routing.py` — remove per-route nexthop fallback when bulk map is globally empty; tighten BGP AF/policy guard

### Critical Pitfalls

1. **Sequential per-unit family loop — 700+ HTTP calls** — `get_interface_detail` calls `list_interface_families(client, unit_id=unit.id)` inside a `for unit in units` loop. `list_interface_units` already builds `family_count_by_unit` but `get_interface_detail` discards it. Fix: bulk-fetch all families at device level before the loop.

2. **Per-filter/policer detail loops in `get_device_firewall_summary`** — `detail=True` fires sequential `cms_list` per filter and per policer. Fix: bulk-fetch all terms and actions at device level before the loops; distribute via dict keyed by filter_id/policer_id.

3. **`HTTPAdapter` retry collision** — pynautobot already retries 3× internally. Setting `adapter.max_retries = 3` globally (a common "fix" for flaky servers) collides with that → 9 attempts/call. Never set adapter retries globally; assert `adapter.max_retries == 0` in a unit test.

4. **Over-parallelizing CMS calls** — `max_workers > 5` creates simultaneous slow queries against the CMS plugin, which has unindexed Postgres queries (60s+ timeouts observed in v1.9). Cap `max_workers` at 3–5; add per-call 5s timeout; fall back to sequential on timeout.

5. **Shared `WarningCollector` across threads** — `WarningCollector` uses plain `list.append()`, not thread-safe. Each ThreadPoolExecutor worker must capture its own warnings; collect and merge in the main thread after `as_completed()`.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 35: `get_interface_detail` Bulk Fix
**Rationale:** Highest-impact fix — eliminates the worst N+1 in the codebase. 709-unit HQV-PE1-NEW goes from 700+ sequential HTTP calls to ~3. `list_interface_units` already has the bulk family map; the fix reuses it.
**Delivers:** `get_interface_detail` with bulk family + VRRP pre-fetch; unit tests verifying call count ≤ 4; thread safety review; HTTP config audit (assert `adapter.max_retries == 0`).
**Addresses:** `interface_detail` bulk family fetch (P1 from FEATURES.md).
**Avoids:** Pitfall 1 (sequential per-unit loop), Pitfall 3 (shared session), Pitfall 4 (dual-retry collision), Pitfall 5 (error partitioning), Pitfall 6 (over-parallelization).
**Research Flag:** Phase 35 needs to confirm `juniper_interface_families` and `juniper_vrrp_groups` both support `device=` filter for bulk pre-fetch — verify in `CMS_ENDPOINTS` before coding.

### Phase 36: `get_device_firewall_summary` Detail Bulk Fix
**Rationale:** Second-highest impact. The `detail=True` path currently makes O(F+P) sequential calls for terms and actions. The `detail=False` path is already optimal (v1.9 co-primary parallelism).
**Delivers:** Detail loop with bulk term + match-condition + action + policer-action pre-fetch; updated smoke test call counts; unit tests for bulk distribution.
**Addresses:** `firewall_summary` detail bulk term/action fetch (P1 from FEATURES.md).
**Avoids:** Pitfall 2 (per-filter/policer loops), Pitfall 5 (error partitioning).
**Research Flag:** Phase 36 needs to confirm all four term/action endpoints support `device=` filter. If any lack it, fall back to ThreadPoolExecutor with `max_workers=3` for parallel per-parent fetches.

### Phase 37: Routing + BGP Fallback Guards
**Rationale:** Correctness fixes rather than performance. The per-route nexthop fallback fires N times even when bulk map is globally empty. The BGP AF/policy fallback has a weak guard. Both are isolated fixes with minimal risk.
**Delivers:** Strict `if not nh_by_route` guard in `list_static_routes`; strict `len(af_by_nbr) > 0` guard in `get_device_bgp_summary`; updated test mocks for both.
**Addresses:** `routing_table` remove fallback (P1), `bgp_summary` edge-case guard (P2 from FEATURES.md).
**Avoids:** Pitfall 7 (per-route false fallback), Pitfall 8 (weak BGP guard).

### Phase 38: Regression Gate + CI Integration
**Rationale:** Lock in gains. Add `uat_cms_smoke.py` HTTP call count assertions with a 10% increase threshold; unit tests for all new bulk helpers; CLI smoke test.
**Delivers:** Pass/fail gate blocking regressions; documentation of new call count baselines.
**Addresses:** `uat_cms_smoke.py` call count assertions (P2 from FEATURES.md).

### Phase Ordering Rationale

- **Phase 35 before 36** because `get_interface_detail` is the worst N+1 (700+ units on HQV-PE1-NEW) and the fix is simpler (only 2 bulk fetches: families + VRRP). `get_device_firewall_summary` has 4 bulk fetches and a co-primary pattern already in place.
- **Phase 37 after 35+36** because the routing/BGP fixes are isolated correctness changes with no dependency on the bulk pre-fetch infrastructure — but they should ship together in the same milestone to avoid CI noise.
- **Phase 38 is the quality gate** that must pass before closing the milestone — smoke test, unit tests, and CLI regression must all clear before declaring v1.10 done.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 35 (`get_interface_detail`):** Need to confirm `juniper_interface_families` and `juniper_vrrp_groups` support `device=` filter for bulk pre-fetch — confirm in `CMS_ENDPOINTS` before coding. If either lacks it, fall back to ThreadPoolExecutor with `max_workers=3` for parallel per-unit/per-family fetches.
- **Phase 36 (`firewall_summary` detail):** Need to confirm `juniper_firewall_terms`, `juniper_firewall_match_conditions`, `juniper_firewall_actions`, and `juniper_firewall_policer_actions` all support `device=` filter. If any lack it, fall back to parallel ThreadPoolExecutor with `max_workers=3`.

Phases with standard patterns (skip research-phase):
- **Phase 37 (routing/BGP guards):** Pure code correctness changes — bulk pre-fetch pattern already validated; just applying it to two existing fallback paths.
- **Phase 38 (regression gate):** Follows existing Phase 33 `uat_cms_smoke.py` pattern; no new research needed.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | `ThreadPoolExecutor` + `_CMS_BULK_LIMIT=200` validated across v1.6–v1.9; pynautobot threading internals confirmed via source; `requests.Session` thread-safety documented |
| Features | HIGH | All 4 composite N+1 patterns mapped to exact file:line locations; correct behavior defined per composite; test update requirements identified |
| Architecture | HIGH | Layer architecture (CLI ↔ workflows ↔ CMS domain ↔ cms/client ↔ pynautobot) confirmed; shared session thread-safety rationale documented; bulk pre-fetch pattern proven in `list_firewall_filters` term count |
| Pitfalls | HIGH | All 8 pitfalls traced to specific file:line references; recovery strategies documented; "looks done but isn't" checklist covers all risky changes |

**Overall confidence:** HIGH

### Gaps to Address

- **CMS endpoint filter support for bulk pre-fetch:** The entire bulk pre-fetch strategy depends on `device=` filter support across `juniper_interface_families`, `juniper_vrrp_groups`, `juniper_firewall_terms`, `juniper_firewall_match_conditions`, `juniper_firewall_actions`, and `juniper_firewall_policer_actions`. Need to verify all 6 in `CMS_ENDPOINTS` config before Phase 35/36 planning. If any lack `device=` support, fall back to ThreadPoolExecutor with `max_workers=3` for parallel per-parent fetches.
- **Test mock compatibility:** All three composite fixes require updating unit test mocks to provide bulk-compatible data. The routing fallback fix (`list_static_routes`) is particularly dependent on mocks — if mocks don't populate the bulk map, the fallback will still fire in tests. Resolve by updating mocks before marking Phase 37 done.

## Sources

### Primary (HIGH confidence)
- `nautobot_mcp/cms/interfaces.py` — `get_interface_detail` N+1 analysis (lines 658–761); `list_interface_units` bulk family map (lines 69–83)
- `nautobot_mcp/cms/firewalls.py` — `get_device_firewall_summary` N+1 analysis (lines 654–750); co-primary parallelism pattern
- `nautobot_mcp/cms/routing.py` — `get_device_bgp_summary` (lines 639–779); `list_static_routes` fallback (lines 46–128)
- `nautobot_mcp/cms/client.py` — `_CMS_BULK_LIMIT = 200`; `cms_list` pagination implementation
- `nautobot_mcp/devices.py` — `ThreadPoolExecutor(max_workers=3)` pattern (lines 374–384); `WarningCollector` thread-safety note
- pynautobot 3.0.0 source — `Api.__init__`, `Request.concurrent_get()`, `Endpoint.filter()` threading internals

### Secondary (MEDIUM confidence)
- `.planning/PROJECT.md` — v1.8 Phase 33 PAGE_SIZE=1 root cause; v1.9 Phase 34 AF/policy timeout fix; v1.10 active milestone

### Tertiary (LOW confidence)
- CMS endpoint filter support — needs live API verification against Nautobot CMS plugin; not all `device=` filters may be present

---
*Research completed: 2026-03-31*
*Ready for roadmap: yes*
