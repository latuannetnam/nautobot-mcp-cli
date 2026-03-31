# Phase 35 Research: `interface_detail` N+1 Fix

**Researched:** 2026-03-31
**Status:** Complete — ready for planning

---

## 1. Current N+1 Patterns (Root Cause Analysis)

### N+1 #1: Per-unit family refetch (L689-692)

```python
# CURRENT (L689-692) — get_interface_detail()
unit_families: dict[str, list] = {}
for unit in units:
    families = list_interface_families(client, unit_id=unit.id, limit=0)
    unit_families[unit.id] = families.results
```

**Problem:** For each unit, one `list_interface_families(unit_id=unit.id)` HTTP call.
On HQV-PE1 with ~2,000 units: ~2,000 extra HTTP calls.

**Note:** `list_interface_units` (L67-86) already does a bulk family prefetch for `family_count`.
But `get_interface_detail` ignores that and refetches per-unit — the two are independent calls.
This is intentional (D-01): `list_interface_units` is shallow, `get_interface_detail` needs full objects.

### N+1 #2: Per-family VRRP loop (L694-705)

```python
# CURRENT (L694-705) — get_interface_detail()
vrrp_by_family: dict[str, list] = {}

def _get_vrrp_for_family(family_id: str) -> list:
    if family_id in vrrp_by_family:   # ← memoization only within current call
        return vrrp_by_family[family_id]
    try:
        vrrp = list_vrrp_groups(client, family_id=family_id, limit=0)
        vrrp_by_family[family_id] = vrrp.results
    except Exception as e:
        collector.add(...)
        vrrp_by_family[family_id] = []
    return vrrp_by_family[family_id]
```

**Problem:** With ~2,000 families, this fires ~2,000 `list_vrrp_groups(family_id=...)` calls.
The `vrrp_by_family` memo dict only caches within one `get_interface_detail` call — not across calls.
With 2,000 units and 2,000 families: **~4,003 total HTTP calls** → timeout.

**Current VRRP map is populated lazily** (per family as needed), not prefetched.

---

## 2. Fix Design

### Bulk Prefetch Block (insert after L684 `units_resp`, before L689 loop)

```python
# STEP 1: Bulk fetch ALL families for device (replaces per-unit loop)
device_id = resolve_device_id(client, device)  # already called inside list_interface_units
all_families_resp = cms_list(
    client,
    "juniper_interface_families",
    InterfaceFamilySummary,
    device=device_id,   # device-level, not per-unit
    limit=0,
)

# STEP 2: Index all families by unit_id (same pattern as list_interface_units L68-80)
unit_families: dict[str, list[InterfaceFamilySummary]] = {}
for fam in all_families_resp.results:
    unit_families.setdefault(fam.unit_id, []).append(fam)

# STEP 3: Bulk fetch ALL VRRP groups for device
all_vrrp_resp = cms_list(
    client,
    "juniper_vrrp_groups",
    VRRPGroupSummary,
    device=device_id,   # device-level
    limit=0,
)

# STEP 4: Index VRRP groups by family_id (key = family_id on VRRPGroupSummary)
vrrp_by_family: dict[str, list[VRRPGroupSummary]] = {}
for vrrp in all_vrrp_resp.results:
    vrrp_by_family.setdefault(vrrp.family_id, []).append(vrrp)
```

**Result:** Exactly 3 HTTP calls total in `get_interface_detail`:
1. `list_interface_units(device=device_id, limit=0)` — existing (L684)
2. `cms_list(..., "juniper_interface_families", ..., device=device_id, limit=0)` — NEW bulk
3. `cms_list(..., "juniper_vrrp_groups", ..., device=device_id, limit=0)` — NEW bulk

### Update `_get_vrrp_for_family` Closure

```python
def _get_vrrp_for_family(family_id: str) -> list:
    """Look up VRRP groups for a family from prefetched map (or empty on miss)."""
    # Prefetched map always populated when this closure is called in get_interface_detail
    if family_id in vrrp_by_family:
        return vrrp_by_family[family_id]
    # Graceful degradation: family with no VRRP groups → empty list (no HTTP call)
    return []
```

**Key change:** Remove the `list_vrrp_groups` HTTP call from inside `_get_vrrp_for_family`.
The VRRP map is now pre-populated before any unit processing.

### Exception Handling (D-03 / D-04)

- **Family prefetch failure (D-03):** Propagate. Family data is critical for `detail=True` enrichment.
  ```python
  # If this raises, the outer exception handler in get_interface_detail catches it
  # Hard-fail preserves existing behavior for error path
  ```
- **VRRP prefetch failure (D-04):** Catch, `collector.add("bulk_vrrp_fetch", str(e))`, continue with empty `vrrp_by_family = {}`.
  ```python
  try:
      all_vrrp_resp = cms_list(client, "juniper_vrrp_groups", VRRPGroupSummary, device=device_id, limit=0)
      # index ...
  except Exception as e:
      collector.add("bulk_vrrp_fetch", str(e))
      vrrp_by_family = {}  # graceful degradation
  ```

---

## 3. Code Change Map

### `get_interface_detail` — before vs after

| Region | Before | After |
|--------|--------|-------|
| L685 (prefetch) | — | New: bulk families + VRRP prefetch block |
| L689-692 (per-unit loop) | `list_interface_families(unit_id=unit.id)` per unit | `unit_families` from prefetch map |
| L694-705 (`_get_vrrp_for_family`) | Lazy per-family HTTP call via `list_vrrp_groups` | Map lookup only, no HTTP |
| Total HTTP calls | ~2×N_units + ~2×N_families + 1 | 3 (constant) |

### No structural changes to:
- `list_interface_units` — untouched (D-01)
- `get_interface_unit` — untouched; `_get_vrrp_for_family` still works via map lookup fallback
- Function signature — unchanged
- Return type — unchanged

---

## 4. `_get_vrrp_for_family` Backward Compatibility

The closure captures `vrrp_by_family` from the enclosing scope:

- **In `get_interface_detail`:** `vrrp_by_family` is always pre-populated by the prefetch block.
  The HTTP fallback inside `_get_vrrp_for_family` is **dead code** in this path.
  We remove it — family not in map → return `[]`.

- **In `get_interface_unit` (L150-153):** `get_interface_unit` calls `list_interface_families(unit_id=id)`
  then `list_vrrp_groups(family_id=...)` per family. `_get_vrrp_for_family` is NOT used in this path.
  So Phase 35 changes don't affect `get_interface_unit` at all.

**But:** The `_get_vrrp_for_family` closure IS defined inside `get_interface_detail`. If we
update it to remove the HTTP call fallback, `get_interface_unit` is unaffected. Good.

**However**, if we wanted `get_interface_unit` to also benefit from prefetching:
it's out of scope (D-01: "Do NOT refactor `list_interface_units`"). Deferred.

---

## 5. VRRP Map Index Field

`VRRPGroupSummary` model (interfaces.py, models file):
- `family_id: str` — UUID of the parent interface family
- Indexed via `vrrp_by_family.setdefault(vrrp.family_id, []).append(vrrp)`

This is the correct join key — `VRRPGroupSummary.from_nautobot()` extracts it from `record.interface_family.id`.

---

## 6. Family Prefetch vs `list_interface_families`

Two distinct APIs for families:
1. `list_interface_families(unit_id=unit_id)` — unit-scoped, used in per-unit loop (N+1)
2. `cms_list(client, "juniper_interface_families", ..., device=device_id, limit=0)` — device-scoped, bulk

Both call the same CMS endpoint (`juniper_interface_families`). The difference:
- `list_interface_families` uses `interface_unit=<uuid>` filter
- Bulk prefetch uses `device=<device_uuid>` filter (same endpoint, returns superset)

The bulk prefetch (`device=...`) returns ALL families for the device in one call.
The per-unit loop (`interface_unit=...`) returns only families for that specific unit.

Result: same data, one call vs N calls. Confirmed equivalent.

---

## 7. Existing `list_interface_units` Bulk Family Fetch

`list_interface_units` (L67-86) already does:
```python
all_families = cms_list(client, "juniper_interface_families", ..., device=device_id, limit=0)
family_count_by_unit: dict[str, int] = {}
for fam in all_families.results:
    family_count_by_unit[fam.unit_id] = family_count_by_unit.get(fam.unit_id, 0) + 1
```

**Double fetch concern:** `get_interface_detail` calls `list_interface_units` (which fetches families)
THEN prefetches families again. This is D-01 acceptable tradeoff:
- `list_interface_units` serves `family_count` (int) — lightweight
- `get_interface_detail` needs full `InterfaceFamilySummary[]` objects for `detail=True`
- These are different data needs; deduplication is out of scope for Phase 35

Future Phase could: refactor `list_interface_units` to return `family_lookup_map` and have
`get_interface_detail` reuse it. But not in Phase 35 scope.

---

## 8. Unit Test Impact

### Existing tests to update

**`test_interface_detail_default` (L244-277):**
```python
# OLD assertions (will break):
mock_fams.assert_called_once_with(client, unit_id="unit-001", limit=0)  # per-unit call
mock_vrrp.assert_called_once_with(client, family_id="fam-001", limit=0)  # per-family call

# NEW assertions:
# 1. list_interface_units called once (unchanged)
mock_units.assert_called_once_with(client, device="edge-01", limit=0)
# 2. Bulk families prefetch called once with device-level filter
mock_fams.assert_called_once()  # called with device=..., not unit_id=...
# 3. list_vrrp_groups NOT called per-family (map lookup only)
mock_vrrp.assert_not_called()   # VRRP comes from prefetched map
```

**`test_interface_detail_vrrp_enrichment_failure` (L484-507):**
```python
# OLD: mocks list_vrrp_groups to raise — VRRP enrichment fails per call
# NEW: VRRP enrichment failure = bulk prefetch failure → whole map is {}
# Need to update: raise exception on bulk VRRP prefetch instead
```

**`test_interface_detail_summary_mode_strips_nested_arrays` (L536-577):**
```python
# OLD: mock_vrrp.assert_called() — VRRP called per family for count
# NEW: mock_vrrp.assert_not_called() — VRRP from prefetched map
```

### New tests to add

1. **`test_interface_detail_bulk_prefetch_exactly_3_calls`:**
   - Patches `list_interface_units`, `cms_list` (families), `cms_list` (VRRP)
   - Verifies exactly 3 HTTP call invocations
   - Uses 3 units × 2 families each

2. **`test_interface_detail_family_prefetch_failure_hard_fail`:**
   - Bulk family prefetch raises → function propagates exception
   - No unit processing occurs

3. **`test_interface_detail_vrrp_prefetch_failure_graceful`:**
   - Bulk VRRP prefetch raises → `collector.warnings` has "bulk_vrrp_fetch"
   - Response still returns with `vrrp_groups = []` per family

4. **`test_interface_detail_no_per_unit_family_calls`:**
   - Patches `list_interface_families` to raise if called
   - Verifies it is NOT called (assert_not_called)
   - Families come from prefetch map

5. **`test_interface_detail_no_per_family_vrrp_calls`:**
   - Patches `list_vrrp_groups` to raise if called
   - Verifies it is NOT called (assert_not_called)
   - VRRP comes from prefetch map

---

## 9. Smoke Test (`uat_cms_smoke.py`) Impact

The smoke test (L100-107) calls `interface_detail` via CLI subprocess:
```python
{
    "id": "interface_detail",
    "cmd": ["uv", "run", "nautobot-mcp", "--json", "cms", "interfaces", "detail", "--device", DEVICE],
},
```

**HTTP call counting (L26-46):**
- Monkey-patches `pynautobot.core.query.Request._make_call`
- Groups by URL path (e.g., `/api/plugins/netnam-cms-core/juniper_interface_units/`)
- Prints top-5 paths with >1 calls after each workflow

**Expected post-fix output:**
```
interface_detail: 3 total calls
    1x .../juniper_interface_units/
    1x .../juniper_interface_families/
    1x .../juniper_vrrp_groups/
```

**Pre-fix output (estimated):**
```
interface_detail: ~4003 total calls
    2000x .../juniper_interface_families/  (per-unit loop)
    2000x .../juniper_vrrp_groups/         (per-family loop)
       1x .../juniper_interface_units/    (existing)
```

**Threshold check (L195-201):** `interface_detail: 15000.0ms`
Post-fix should complete in <5s (down from 120s+ timeout).

---

## 10. pynautobot Bulk Fetch Quirk

From Phase 33 context (`.planning/phases/33-cms-pagination-fix/33-CONTEXT.md`):
- CMS plugin has `PAGE_SIZE=1` on some endpoints
- `pynautobot` auto-paginates: `limit=0` means one HTTP call per record without `_CMS_BULK_LIMIT`
- `_CMS_BULK_LIMIT = 200` workaround: `endpoint.all(limit=200)` → `ceil(N/200)` calls instead of N

**This fix relies on `cms_list`** (not `list_interface_families`/`list_vrrp_groups` directly):
- `cms_list` applies `_CMS_BULK_LIMIT = 200` automatically when `limit=0`
- With 2,000 families: `ceil(2000/200) = 10` HTTP calls per endpoint (not 2,000)
- 3 bulk calls × 10 pages = 30 HTTP calls max (vs ~4,000 before)
- Plus the `next` page chain traversal overhead — still bounded and fast

**Important:** `list_interface_families(client, unit_id=unit.id, limit=0)` called in the per-unit
loop ALSO goes through `cms_list`, but with a specific filter. Each call might itself paginate.
With the fix: one bulk call with `limit=0` → `_CMS_BULK_LIMIT=200` → 10 pages.

---

## 11. `WarningCollector` Integration (CQP-05)

From `warnings.py` and Phase 35 decisions:

- **Family prefetch hard-fail:** No `WarningCollector` involvement. Exception propagates.
  `collector.add` not called — this is critical data, not partial failure.

- **VRRP prefetch graceful degradation:** Wrapped in try/except, calls `collector.add("bulk_vrrp_fetch", str(e))`.
  Example: `{"operation": "bulk_vrrp_fetch", "error": "Connection timeout"}`
  - After: `vrrp_by_family = {}` (empty map)
  - Per-family: `_get_vrrp_for_family(fam.id)` → returns `[]` (family not in map)
  - Result: `vrrp_groups = []` for all families, response still complete

- **Existing per-family VRRP failures:** After fix, `_get_vrrp_for_family` never makes HTTP calls.
  So existing `collector.add` in that path is dead code. This is acceptable — the graceful degradation
  path is preserved for the VRRP prefetch failure case, which is the non-critical one.

---

## 12. Summary of All Findings

| Question | Answer |
|----------|--------|
| N+1 #1 exact lines | L690-692: `list_interface_families(unit_id=unit.id)` per unit in loop |
| N+1 #2 exact lines | L696-705: `list_vrrp_groups(family_id=family_id)` per family in `_get_vrrp_for_family` |
| Prefetch structure | After `units_resp` (L684), before unit loop (L689): bulk families → index by unit_id, bulk VRRP → index by family_id |
| `_get_vrrp_for_family` update | Remove HTTP call; map lookup only; family not in map → `[]` |
| Family prefetch failure | Hard-fail (D-03): propagate exception |
| VRRP prefetch failure | Graceful degradation (D-04): `collector.add("bulk_vrrp_fetch", str(e))`, `vrrp_by_family = {}` |
| `get_interface_unit` affected? | No — not called from there; `_get_vrrp_for_family` closure only used in `get_interface_detail` |
| Existing tests to update | `test_interface_detail_default`, `test_interface_detail_vrrp_enrichment_failure`, `test_interface_detail_summary_mode_strips_nested_arrays` |
| New tests needed | 5 new tests covering bulk prefetch, hard-fail, graceful degradation, no-per-unit-calls, no-per-family-calls |
| Smoke test behavior | `interface_detail` will show 3 unique URL paths (units, families, VRRP) with 1 call each |
| pynautobot quirk | `_CMS_BULK_LIMIT=200` handles PAGE_SIZE=1; bulk call = 10 HTTP pages for 2000 records |
| `list_interface_units` double-fetch | Intentional (D-01); separate data needs; out of Phase 35 scope |

---

## 13. Open Questions / Clarifications

| # | Question | Recommendation |
|---|----------|----------------|
| 1 | Should `device_id` be resolved once or twice? | `list_interface_units` calls `resolve_device_id` internally. `get_interface_detail` doesn't have `device_id` in scope. Solution: call `resolve_device_id` once before prefetch block, reuse for both bulk calls. |
| 2 | What if `units` list is empty? | Prefetch block still runs (empty families + VRRP → both empty maps). No harm. |
| 3 | `unit_families` vs `vrrp_by_family` types | `unit_families: dict[str, list[InterfaceFamilySummary]]`, `vrrp_by_family: dict[str, list[VRRPGroupSummary]]` |
| 4 | Limit enforcement | Prefetch fetches ALL (limit=0). Limit applied at output serialization step (L723-724, L736-737). Correct. |
| 5 | Should prefetch be gated on `detail=True`? | No. `detail=False` summary mode still calls `_get_vrrp_for_family` for count (L730). VRRP prefetch benefits both modes. Family prefetch only needed for `detail=True` but the overhead of fetching them is minimal (~2000 records). |

---

## 14. Planning Inputs

**Ready for PLAN.md:**
- Exact 3-call structure confirmed
- All 7 decisions (D-01 through D-07) from 35-CONTEXT.md are respected
- Test coverage plan: 5 new tests + 3 updated existing tests
- Smoke test observable outcome: 3 URL paths with 1 call each
- No blockers identified

**Key risk:** The existing test `test_interface_detail_default` asserts per-unit/per-family call counts
that will change. These tests must be updated as part of the fix (not deferred). Plan should include test updates.

**Key observation:** The VRRP prefetch failure graceful degradation (`WarningCollector`) is already
the established pattern for VRRP in Phase 19. The fix extends it to the bulk prefetch level rather
than per-family calls. No new conceptual ground.
