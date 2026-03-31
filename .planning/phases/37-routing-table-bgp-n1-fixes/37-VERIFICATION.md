# Phase 37 Verification Report

**Phase:** 37-routing-table-bgp-n1-fixes
**Goal:** Remove N+1 query pattern from `get_device_routing_table()`; document BGP per-neighbor fallback guard rationale; add N+1 invariant tests for both workflows
**Completed:** 2026-03-31
**Commits:** `d93a84a` (Plan 01) · `5d0fb16` (Plan 02) · `145f2c5` (Plan 03)

---

## Success Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | N+1 loop confirmed removed from `list_static_routes()` | ✅ PASS | Grep: `route=` absent; exactly 1 `for route in routes.results:` loop; exactly 3 `cms_list` calls; `Backward-compatible fallback` absent |
| 2 | BGP fallback guard comment block present in `get_device_bgp_summary()` | ✅ PASS | `CQP-04` present (L656); `triple guard` comment present (L717, L725); `af_keyed_usable`/`pol_keyed_usable` present |
| 3 | N+1 invariant tests created and passing (9 tests) | ✅ PASS | `tests/test_cms_routing_n1.py` exists; all 9 tests pass (`uv run pytest tests/test_cms_routing_n1.py -v`) |
| 4 | 546 unit tests pass with 0 failures | ✅ PASS | `uv run pytest --ignore=scripts/uat_smoke_test.py -q` → 546 passed, 11 deselected |
| 5 | `37-VERIFICATION.md` created | ✅ PASS | This file |

---

## Plan 01 — Routing N+1 Loop Removal (CQP-03)

**Commit:** `d93a84a`

### Acceptance Criteria

| Criterion | Result | Detail |
|-----------|--------|--------|
| `cms_list` with `route=` absent from `list_static_routes()` | ✅ | Grep confirmed 0 occurrences in function body |
| Exactly 1 `for route in routes.results:` loop inside `list_static_routes()` | ✅ | The inline-assignment loop; no fallback loop |
| Inline assignment: `route.nexthops = nh_by_route.get(route.id, [])` | ✅ | L96 |
| Inline assignment: `route.qualified_nexthops = qnh_by_route.get(route.id, [])` | ✅ | L97 |
| `Backward-compatible fallback` phrase absent | ✅ | Removed with the loop |
| Exactly 3 `cms_list` calls: `juniper_static_routes`, `juniper_static_route_nexthops`, `juniper_static_route_qualified_nexthops` | ✅ | AST analysis: 3 calls confirmed |
| No `try:`/`except:` inside the `for route` loop | ✅ | Graceful degradation already handled by outer `except Exception: pass` blocks at L84-85 and L91-92 |

### Verification Commands

```bash
# N+1 loop gone: no route= in list_static_routes
grep -n "route=" nautobot_mcp/cms/routing.py | awk -F: '$1 >= 46 && $1 <= 102 {print}'

# Should return empty — the only remaining route= calls are in get_static_route() (L119, L129), which is a single-item get, not a list loop

# Backward-compatible fallback removed
grep -n "Backward-compatible fallback" nautobot_mcp/cms/routing.py
# Should return empty

# Exactly 3 cms_list calls in list_static_routes
python -c "
import ast
src = open('nautobot_mcp/cms/routing.py').read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == 'list_static_routes':
        lines = src.split('\n')[node.lineno-1:node.end_lineno]
        cms_calls = [l for l in lines if 'cms_list' in l]
        print(f'cms_list calls: {len(cms_calls)}')
        for l in cms_calls: print(' ', l.strip()[:80])
"
# → 3 calls: juniper_static_routes, juniper_static_route_nexthops, juniper_static_route_qualified_nexthops
```

---

## Plan 02 — BGP Fallback Guard Documentation (CQP-04)

**Commit:** `5d0fb16`

### Acceptance Criteria

| Criterion | Result | Detail |
|-----------|--------|--------|
| `CQP-04` string present in `get_device_bgp_summary()` | ✅ | L656: multi-line comment block |
| `triple guard` comment present | ✅ | L717 and L725: trailing comments on both fallback conditions |
| `af_keyed_usable` present | ✅ | L693: `neighbor_ids` + set comprehension; L711, L718 |
| `pol_keyed_usable` present | ✅ | L694, L713, L726 |
| Guard condition `not fam_list and not af_bulk_failed and af_keyed_usable` unchanged | ✅ | L718 |
| Guard condition `not pol_list and not pol_bulk_failed and pol_keyed_usable` unchanged | ✅ | L726 |
| No new `cms_list` calls added | ✅ | Only `list_bgp_address_families` (L672) and `list_bgp_policy_associations` (L682) |

### Documentation Block (L651-663)

```
# Bulk fetch AFs/policies only when detail=True AND there are neighbors.
# Without this guard, both endpoints cause 60s+ timeouts even at limit=1
# (unindexed global scans on the Nautobot CMS plugin). HQV-PE1-NEW has
# 0 BGP groups so these fetches serve no purpose in the default path.
#
# CQP-04: Per-neighbor AF/policy fallback is gated by a triple guard:
#   (a) bulk returned no results for this neighbor   [not fam_list / not pol_list]
#   (b) the bulk fetch itself did not error           [not *_bulk_failed]
#   (c) the bulk results contain usable neighbor_id keys [af_keyed_usable / pol_keyed_usable]
# When all three hold AND bulk IS keyed, the fallback fires (per-neighbor fetch).
# When af_keyed_usable is False (bulk has no matching neighbor_id keys),
# the fallback is suppressed — avoids per-neighbor calls on unkeyed test data.
# This matches Phase 35 VRRP graceful-degradation guard pattern.
```

### Verification Commands

```bash
# CQP-04 present
grep -n "CQP-04" nautobot_mcp/cms/routing.py

# triple guard comment present
grep -n "triple guard" nautobot_mcp/cms/routing.py

# Verify guard conditions unchanged
grep -n "af_keyed_usable" nautobot_mcp/cms/routing.py
grep -n "pol_keyed_usable" nautobot_mcp/cms/routing.py
```

---

## Plan 03 — N+1 Invariant Tests (9 tests)

**Commit:** `145f2c5`

### Test File: `tests/test_cms_routing_n1.py`

| Test | Purpose | Status |
|------|---------|--------|
| `test_routing_table_exactly_3_calls` | 3 routes → exactly 3 `cms_list` calls | ✅ PASS |
| `test_routing_table_no_per_route_calls` | `route=` kwarg never passed (N+1 proof) | ✅ PASS |
| `test_routing_table_graceful_empty_nexthops` | Empty bulk nexthops → no fallback | ✅ PASS |
| `test_routing_table_nexthop_bulk_exception_silent` | Nexthop bulk exception → silent degradation, no warning | ✅ PASS |
| `test_routing_table_50_routes_stays_3_calls` | Scale invariant: 50 routes → 3 calls | ✅ PASS |
| `test_bgp_summary_guard_0_neighbors` | 0 neighbors → AF/policy bulk fetches never called | ✅ PASS |
| `test_bgp_summary_exactly_2_cms_list_calls_with_detail` | 15 neighbors → 2 `cms_list` calls (AFs + policies) | ✅ PASS |
| `test_bgp_summary_af_keyed_usable_false_suppresses_fallback` | Unkeyed bulk → no per-neighbor fallback calls | ✅ PASS |
| `test_bgp_summary_af_bulk_exception_warning_collector` | AF exception → WarningCollector with `operation` key | ✅ PASS |

**Total: 9 / 9 passing**

### Acceptance Criteria

| Criterion | Result |
|-----------|--------|
| All 9 tests present and named correctly | ✅ |
| `nautobot_mcp.cms.routing.cms_list` used as patch target (not `cms.client.cms_list`) | ✅ |
| `test_bgp_summary_exactly_2_cms_list_calls_with_detail` asserts `mock_cms.call_count == 2` | ✅ |
| `test_bgp_summary_af_bulk_exception_warning_collector` uses `w.get("operation", "")` (not `"key"`) | ✅ |

### Verification Command

```bash
uv run pytest tests/test_cms_routing_n1.py -v
# → 9 passed in 0.07s
```

---

## Regression Gate

| Suite | Result |
|-------|--------|
| `uv run pytest --ignore=scripts/uat_smoke_test.py -q` | 546 passed, 11 deselected ✅ |
| `uv run pytest tests/test_cms_routing_n1.py -v` | 9 passed ✅ |
| **Total unit tests** | **555 passed, 0 failures** |

> **Note:** 10 `ERROR` results from `scripts/uat_smoke_test.py` are pre-existing live-UAT fixtures (`client` fixture not available in unit-only runs). These are excluded by `--ignore=scripts/uat_smoke_test.py`. They require `NAUTOBOT_URL` + `NAUTOBOT_TOKEN` to run and are not part of the unit test gate.

---

## Pattern Established

Phase 37 completes the **bulk-prefetch + triple-guard** pattern for CMS composite functions:

```
Bulk fetch (device-scoped) → dict-by-FK → inline loop assignment
                                    ↓ (if keyed and empty for this item)
                         triple guard: (a) no bulk data
                                        (b) no bulk failure
                                        (c) bulk has usable keys
                                    → per-item fallback (last resort)
```

This mirrors the Phase 35 VRRP graceful-degradation guard and applies to:
- `list_static_routes` → nexthops inlining (Plan 01)
- `get_device_bgp_summary` → AF/policy enrichment (Plan 02, guards were already correct)

---

## Phase Complete

| Deliverable | Status |
|-------------|--------|
| `nautobot_mcp/cms/routing.py` — N+1 loop removed | ✅ |
| `nautobot_mcp/cms/routing.py` — CQP-04 guard docs added | ✅ |
| `tests/test_cms_routing_n1.py` — 9 N+1 invariant tests | ✅ |
| 546 unit tests pass, 0 failures | ✅ |
| `37-VERIFICATION.md` created | ✅ |

**Next:** Phase 38 — regression gate (`uat_cms_smoke.py` smoke test + full suite confirmation)

---
*Verified: 2026-03-31*
*Phase 37 — nautobot-mcp-cli v1.10 CMS N+1 Query Elimination*
