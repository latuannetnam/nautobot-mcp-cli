# Phase 38-01 Summary — Regression Gate: Smoke Test

**Phase:** 38-regression-gate | **Plan:** 38-01
**Executed:** 2026-03-31
**Status:** SHIPPED

---

## Objective

Run UAT smoke test against HQV-PE1-NEW, verify all 5 CMS workflows pass within
thresholds to gate the v1.10 CMS N+1 Query Elimination milestone (Phases 35-37).

---

## Task 38-01-01 — Run Smoke Test

### Regression Found

`interface_detail` returned empty stdout (exit 0 but no JSON) on first run:

```
[interface_detail] Non-JSON stdout: (empty stdout)
```

**Root cause identified:** `get_interface_detail()` at line 696 passed
`device=device_id` to `juniper_interface_families` endpoint. The endpoint does NOT
support the `device` filter (400 Bad Request: `Unknown filter field`). The code
was calling `list_interface_units()` first (fetching ~2,002 units for HQV-PE1-NEW),
then making a family bulk call that 400'd. No data was returned, hence 0 units.

**Fix applied:** Chunked family prefetch — `interface_unit` ID-based filtering.

Instead of a single bulk call with unsupported `device` filter:

```python
# BEFORE (BROKEN): device filter not supported → 400
all_families_resp = cms_list(..., device=device_id, limit=0)
```

Changed to chunked `interface_unit` filter using already-fetched unit IDs:

```python
# AFTER (FIXED): interface_unit filter IS supported → 200 per chunk
_FAMILY_CHUNK_SIZE = 50  # unit IDs per family-bulk call
for i in range(0, len(unit_ids), _FAMILY_CHUNK_SIZE):
    chunk = unit_ids[i:i + _FAMILY_CHUNK_SIZE]
    chunk_resp = cms_list(..., interface_unit=chunk, limit=0)
```

This makes ceil(N_units/50) HTTP calls for families — bounded by unit count
rather than the per-unit N+1 of Phase 35's original design.

### Smoke Test Results

| Workflow | Result | Elapsed (ms) | Threshold (ms) |
|----------|--------|-------------|----------------|
| bgp_summary | **PASS** | 1558 | 5000 |
| routing_table | **PASS** | 1210 | 15000 |
| firewall_summary | **PASS** | 1637 | 15000 |
| interface_detail | **PASS** | 1626 | 15000 |
| devices_inventory | **PASS** | 6394 | 15000 |
| **Total** | **5/5 PASS** | **12536** | — |

- Exit code: 0
- No timeouts
- No parse errors
- All workflows within threshold

### Additional Fixes (Discovered During Execution)

1. **`detail` branch break-condition bug** (`interfaces.py` line ~758): The `break`
   statement inside the family loop was incorrectly placed — it would break out
   after processing just one family per unit when `limit > 0`. Removed since the
   outer unit-level loop handles the limit correctly.

2. **Test 4 updated** (`test_cms_interfaces_n1.py`): Family prefetch failure
   now gracefully degrades to `family_count=0` (CQP-05) rather than hard-failing.
   Updated test accordingly.

### Unit Tests

- `tests/test_cms_interfaces_n1.py`: **8/8 PASS**
- Full suite (`uv run pytest -q --ignore=scripts`): **546/546 PASS**

### RGP-01 Status

**RGP-01: DONE** — marked in `.planning/REQUIREMENTS.md`

---

## Changes Committed

| File | Change |
|------|--------|
| `nautobot_mcp/cms/interfaces.py` | Chunked family prefetch (replaces broken `device` filter); removed incorrect `break` in detail branch |
| `tests/test_cms_interfaces_n1.py` | 8 tests updated: `interface_unit` kwarg support; Test 4 → graceful degradation |
| `.planning/REQUIREMENTS.md` | RGP-01 marked Done; CQP-01..CQP-05 marked Done (smoke-verified) |

---

## Next Steps

Plan 38-01 is complete. Plan 38-02 (full unit test suite) was already validated
by the 546-pass run above. Phase 38 is ready to be marked complete.

**Phase 38 Status:** 1/2 plans shipped — RGP-01 satisfied
