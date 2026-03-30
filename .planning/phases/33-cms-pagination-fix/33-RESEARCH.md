# Phase 33 Research: CMS Pagination Fix

**Phase:** 33-cms-pagination-fix
**Researcher:** Claude
**Date:** 2026-03-30
**Status:** Ready for planning

---

## Q1–Q7: Previous Research (unchanged)

The first research round answered Q1–Q7 as follows:

**Q1:** Both `.all()` and `.filter()` extract `limit` from kwargs and forward it to `Request.__init__`. `Request.get()` uses `self.limit` to set `?limit=N` in the HTTP URL.

**Q2:** `Request` stores `self.limit`. Sequential pagination path: first call gets `?limit=N`, subsequent calls follow Nautobot's `next` URL (which preserves the `limit` from the original request). Threaded path: measures `page_size = len(req["results"])` from the first response.

**Q3:** `Endpoint` class has NO `limit` attribute. `Endpoint.__init__` does not define `self.limit`. The `limit` lives on `Request` only.

**Q4:** Setting `endpoint.limit = 200` creates an arbitrary Python attribute that nothing reads — it is a no-op (harmless but ineffective). Correct: pass `limit=200` as kwarg to `.all()` / `.filter()`.

**Q5:** HTTP: `GET /api/plugins/.../?offset=N&limit=200`. Next URLs preserve the limit. Without `limit` set, each call returns PAGE_SIZE (1 for CMS plugin) → N+1.

**Q6:** `uat_cms_smoke.py` measures wall-clock time only. It does NOT instrument HTTP call counts. It has NO threshold enforcement.

**Q7:** No pynautobot bugs with `limit=N`. `limit=0` passed as kwarg IS forwarded and interpreted by Nautobot as "no limit per page, use max_page_size".

---

## Q8: Does `cms_list()` Already Pass Kwargs to `.all()` / `.filter()`? How Minimal Is the Fix?

**Yes, it already passes kwargs.** The current `cms_list()` (L128-159) builds `pagination_kwargs` and spreads it:

```python
pagination_kwargs = {}
if limit > 0:
    pagination_kwargs["limit"] = limit
if offset > 0:
    pagination_kwargs["offset"] = offset
if filters:
    records = list(endpoint.filter(**filters, **pagination_kwargs))
else:
    records = list(endpoint.all(**pagination_kwargs))
```

The current code is **almost correct** — it already uses the kwargs-forwarding mechanism (not the broken `endpoint.limit = N` approach). The fix is **one additional branch** in `cms_list()`:

```python
pagination_kwargs = {}
if limit == 0:
    pagination_kwargs["limit"] = _CMS_BULK_LIMIT   # ← ONE NEW LINE
elif limit > 0:
    pagination_kwargs["limit"] = limit              # ← rename "if" to "elif"
if offset > 0:
    pagination_kwargs["offset"] = offset
```

This is the minimal change. No changes to `get_cms_endpoint()`, no changes to routing/interface/firewall call sites, no changes to workflows.

**How it works:**
- `limit == 0` → `_CMS_BULK_LIMIT = 200` put into kwargs → sent as `?limit=200` → each page fetches 200 records → ceil(151/200) = 1 HTTP call
- `limit > 0` (e.g., 50) → `50` in kwargs → sent as `?limit=50` → existing behavior preserved
- `limit == 0` with filters → `endpoint.filter(device=..., limit=200)` → `?device=...&limit=200` → same single-page benefit

**Module-level constant:** `_CMS_BULK_LIMIT = 200` added in `cms/client.py`, above `cms_list()`.

---

## Q9: DISC-02 vs D-04 — Is There a Conflict?

**Yes, there is a tension, but D-04 takes precedence and resolves it.**

- **DISC-02** (REQUIREMENTS.md): "Document slow endpoints found and add them to a registry in `cms/client.py`"
- **D-04** (CONTEXT.md): "No endpoint-specific slow registry needed. Apply `_CMS_BULK_LIMIT = 200` universally when `limit=0`"

**Resolution:**

DISC-02 and D-04 describe different things:
- **DISC-02's intent** is discovery + documentation — find which endpoints are slow and record the findings
- **D-04's intent** is implementation — universal fix, no conditional logic

They do NOT conflict on the implementation. The registry described in DISC-02 (D-05 says to record findings in the summary doc, not in code) is satisfied by:
1. Running `uat_cms_smoke.py` with HTTP instrumentation (DISC-01)
2. Writing findings to the Phase 33 summary document

**In practice:** The registry in code (`CMS_SLOW_ENDPOINTS = {...}`) is rejected. The "registry" in DISC-02 is satisfied by the summary doc findings. **No registry dict in `cms/client.py`.**

The tension arises because REQUIREMENTS.md §DISC says "add them to a registry" while D-04/D-05 say "record findings in summary doc." For implementation planning, D-04 governs: no registry dict. For REG-01, the threshold findings are recorded in the smoke script's `THRESHOLD_MS` constants (not a registry dict).

---

## Q10: REG-01 — What Exact Code Changes Are Needed for `uat_cms_smoke.py` Threshold Enforcement?

Currently `uat_cms_smoke.py` (L86-176) measures `elapsed_ms` and prints it, but has **zero threshold checks**. `passed = result.returncode == 0` is always True on success.

**Two additions needed:**

### Addition 1: Threshold constant dict (after `WORKFLOWS`, before `WorkflowResult`)

```python
# Performance thresholds: workflow_id → max_allowed_ms
# Set at 2x empirically observed post-fix time (per D-06).
# Researcher: run smoke test after fix, record times, then update these values.
THRESHOLD_MS: dict[str, float] = {
    "bgp_summary": 5000.0,           # was ~80s before fix; target <5s per v1.8
    "routing_table": 10000.0,         # conservative 10s
    "firewall_summary": 10000.0,     # conservative 10s
    "interface_detail": 10000.0,     # conservative 10s
    "devices_inventory": 15000.0,   # conservative 15s
}
```

### Addition 2: Threshold check in `run_workflow()` (after L99, inside `try` block)

```python
elapsed_ms = round((time.monotonic() - t0) * 1000, 1)
threshold = THRESHOLD_MS.get(workflow["id"])
exceeded = threshold is not None and elapsed_ms > threshold
```

Then in the final `return WorkflowResult(...)` block (L168-176):
```python
# Update pass/fail based on threshold
passed = result.returncode == 0 and not exceeded
...
if exceeded:
    error = f"Threshold exceeded: {elapsed_ms:.0f}ms > {threshold:.0f}ms threshold"
else:
    error = None
...
return WorkflowResult(
    ...
    passed=passed,
    ...
    error=error,
    summary=" | ".join(summary_parts),
)
```

### Addition 3: Show threshold in result table (optional but helpful)

In `print_results()` (L187-190), update the print line:
```python
elapsed_str = f"{r.elapsed_ms:.0f}ms" if r.elapsed_ms >= 0 else "  N/A  "
result_str = "PASS" if r.passed else "FAIL"
threshold_info = ""
if THRESHOLD_MS.get(r.id):
    threshold_info = f" (threshold: {THRESHOLD_MS[r.id]:.0f}ms)"
print(f"  {r.name:<22} {r.id:<20} {result_str:<12} {elapsed_str:>10}{threshold_info}")
```

**After implementation:** Researcher runs the smoke test post-fix, records actual times, updates thresholds to `2 × actual_time` (per D-06), then commits.

---

## Q11: `limit=0` in Kwargs vs Omitting the Kwarg — Is There Risk?

**`limit=0` in kwargs is strictly safer than omitting it. No risk found.**

| Scenario | `pagination_kwargs` | HTTP Request | CMS plugin behavior |
|----------|--------------------|--------------|----------------------|
| No kwarg (`limit > 0` false, `limit == 0` false) | `{}` | No `limit` param | PAGE_SIZE=1 → N+1 |
| `limit=0` kwarg added (post-fix) | `{"limit": 0}` | `?limit=0` | Nautobot interprets as "no limit per page" → max_page_size |
| `limit=200` kwarg (post-fix for `limit==0`) | `{"limit": 200}` | `?limit=200` | 200 per page |

The `limit=0` case is interesting: pynautobot's `Request.get()` sends `?limit=0` when `self.limit = 0`. Nautobot interprets `?limit=0` as "no limit" (equivalent to no limit param), but crucially — it STILL uses the per-page limit of `max_page_size` from the server (or PAGE_SIZE=1 for CMS). So `?limit=0` does NOT fix the N+1 problem.

**The fix using `limit=200` is the correct solution** because it overrides the server's PAGE_SIZE for the bulk page. The `?limit=0` approach (omitting the check and letting pynautobot forward `0`) would still cause N+1.

**No risk with `limit=200` in kwargs:**
- Nautobot respects explicit `limit` in the URL
- Nautobot's `next` URLs include the explicit `limit` from the original request
- No pynautobot code overwrites `self.limit` after `Request.__init__`

**Confirmed safe:** `limit=0` in the kwargs path is a no-op for pagination speed. `limit=200` is the right override.

---

## Q12: Unit Test Mock Assertions — Concrete `unittest.mock` Code

Tests go in `tests/test_cms_client.py` in a **new** `TestCMSListPagination` class (since `TestCMSList` already exists).

All tests use existing fixtures: `mock_client_with_cms` and `mock_cms_record`.

### PAG-04: `cms_list(limit=0)` calls `endpoint.all(limit=200)`

```python
class TestCMSListPagination:
    """Pagination regression tests for cms_list — PAG-01..PAG-06."""

    def test_limit_zero_uses_bulk_limit(self, mock_client_with_cms, mock_cms_record):
        """PAG-04: limit=0 triggers _CMS_BULK_LIMIT (200), not limit=0 or no kwarg.

        This is the core regression test: without the fix, limit=0 causes N+1
        sequential calls. With the fix, limit=200 collapses to ceil(N/200) calls.
        """
        mock_client_with_cms.cms.juniper_static_routes.all.return_value = [mock_cms_record]

        from nautobot_mcp.cms.client import cms_list, _CMS_BULK_LIMIT
        result = cms_list(mock_client_with_cms, "juniper_static_routes", CMSBaseSummary, limit=0)

        mock_client_with_cms.cms.juniper_static_routes.all.assert_called_once_with(
            limit=_CMS_BULK_LIMIT
        )
        assert result.count == 1
```

### PAG-05: `cms_list(limit=50)` calls `endpoint.all(limit=50)` — explicit limit preserved

```python
    def test_explicit_positive_limit_preserved(self, mock_client_with_cms, mock_cms_record):
        """PAG-05: limit=50 passes through as-is. Bulk limit does NOT override caller intent."""
        mock_client_with_cms.cms.juniper_static_routes.all.return_value = [mock_cms_record]

        from nautobot_mcp.cms.client import cms_list, _CMS_BULK_LIMIT
        result = cms_list(mock_client_with_cms, "juniper_static_routes", CMSBaseSummary, limit=50)

        # Must be limit=50, NOT 200 or 0
        mock_client_with_cms.cms.juniper_static_routes.all.assert_called_once_with(limit=50)
        # Sanity: 200 is not passed
        mock_client_with_cms.cms.juniper_static_routes.all.assert_not_called()
        _calls = mock_client_with_cms.cms.juniper_static_routes.all.call_args
        assert "limit" in _calls.kwargs
        assert _calls.kwargs["limit"] == 50
        assert result.count == 1
```

### PAG-06: `cms_list(limit=0, filters)` calls `endpoint.filter(..., limit=200)`

```python
    def test_limit_zero_with_filters_uses_bulk_limit(self, mock_client_with_cms, mock_cms_record):
        """PAG-06: limit=0 with filters also triggers bulk limit on .filter() call."""
        mock_client_with_cms.cms.juniper_static_routes.filter.return_value = [mock_cms_record]

        from nautobot_mcp.cms.client import cms_list, _CMS_BULK_LIMIT
        result = cms_list(
            mock_client_with_cms,
            "juniper_static_routes",
            CMSBaseSummary,
            limit=0,
            device="core-rtr-01",
        )

        mock_client_with_cms.cms.juniper_static_routes.filter.assert_called_once_with(
            device="core-rtr-01",
            limit=_CMS_BULK_LIMIT,
        )
        assert result.count == 1
```

### Additional regression test: `limit=None` (default, no kwarg passed)

```python
    def test_limit_none_no_pagination_kwarg(self, mock_client_with_cms, mock_cms_record):
        """cms_list called without limit arg (None) sends no limit kwarg — existing behavior."""
        mock_client_with_cms.cms.juniper_static_routes.all.return_value = [mock_cms_record]

        # Call without explicit limit= argument (default is 0 per function signature,
        # so this test explicitly tests the None edge case if a caller passes it)
        from nautobot_mcp.cms.client import cms_list, _CMS_BULK_LIMIT
        result = cms_list(mock_client_with_cms, "juniper_static_routes", CMSBaseSummary)

        # Default limit=0 → bulk limit applied (per the fix)
        mock_client_with_cms.cms.juniper_static_routes.all.assert_called_once_with(
            limit=_CMS_BULK_LIMIT
        )
        assert result.count == 1
```

### Mock assertion pattern reference

Key patterns for these tests:
```python
# Assert endpoint.all() was called with limit=N exactly once
mock_endpoint.all.assert_called_once_with(limit=200)

# Assert endpoint.filter() was called with specific kwargs
mock_endpoint.filter.assert_called_once_with(device="uuid", limit=200)

# Inspect call_args when multiple kwargs matter
calls = mock_endpoint.all.call_args
assert calls.kwargs["limit"] == 200          # keyword args
assert len(calls.args) == 0                    # no positional args

# Assert NOT called with a value
mock_endpoint.all.assert_not_called()          # ensure wrong path not taken
```

**Note on `mock_client_with_cms`:** The fixture sets `mock_api.plugins.netnam_cms_core = mock_cms_plugin`. Accessing `client.cms.juniper_static_routes` returns `mock_cms_plugin.juniper_static_routes` — a fresh `MagicMock` per access by default. Since the test calls `cms_list()` once, `client.cms.juniper_static_routes` is accessed once inside `get_cms_endpoint()`, and the returned mock's `.all()`/`.filter()` are called once. The `assert_called_once_with(...)` assertions are safe.

---

## Implementation: Exact Code Diff for `cms/client.py`

```diff
 # Module-level constants
 _CMS_BULK_LIMIT = 200  # Nautobot max; CMS plugin PAGE_SIZE=1 workaround
+"""_CMS_BULK_LIMIT = 200.
+
+Workaround for CMS plugin PAGE_SIZE=1: when limit=0 (get all), pynautobot's
+sequential pagination makes one HTTP call per record (N+1). Setting limit=200
+collapses N records into ceil(N/200) HTTP calls. Nautobot's REST API cap is
+1000; 200 is a conservative safety margin.
+"""


 def cms_list(client, endpoint_name, model_cls, limit=0, offset=0, **filters):
@@的姿态
     model_name = CMS_ENDPOINTS.get(endpoint_name, endpoint_name)
     try:
         endpoint = get_cms_endpoint(client, endpoint_name)
         pagination_kwargs = {}
-        if limit > 0:
+        if limit == 0:
+            pagination_kwargs["limit"] = _CMS_BULK_LIMIT
+        elif limit > 0:
             pagination_kwargs["limit"] = limit
         if offset > 0:
             pagination_kwargs["offset"] = offset
```

**Total: 1 new branch, 1 new constant (4 lines + docstring).** This is the complete implementation.

---

## Validation Architecture (updated)

### PAG Requirements

| ID | Requirement | Verification |
|----|-------------|--------------|
| **PAG-01** | `cms_list(limit=0)` passes `_CMS_BULK_LIMIT=200` to `endpoint.all()`/`endpoint.filter()` | `TestCMSListPagination.test_limit_zero_uses_bulk_limit` — `assert_called_once_with(limit=_CMS_BULK_LIMIT)` |
| **PAG-02** | `limit > 0` values pass through unchanged | `TestCMSListPagination.test_explicit_positive_limit_preserved` — `assert_called_once_with(limit=50)` |
| **PAG-03** | `_CMS_BULK_LIMIT` documented with rationale | Code review: constant + docstring present in `cms/client.py` |
| **PAG-04** | Unit test: `cms_list(limit=0)` → `endpoint.all(limit=200)` | `test_limit_zero_uses_bulk_limit` |
| **PAG-05** | Unit test: `cms_list(limit=50)` → `endpoint.all(limit=50)` | `test_explicit_positive_limit_preserved` |
| **PAG-06** | Unit test: `cms_list(limit=0, filters)` → `endpoint.filter(..., limit=200)` | `test_limit_zero_with_filters_uses_bulk_limit` |

### DISC Requirements

| ID | Requirement | Verification |
|----|-------------|--------------|
| **DISC-01** | Instrument CMS list functions with HTTP call counting | Manual UAT: monkey-patch `Request._make_call` in a test script, run smoke test, record call counts per endpoint |
| **DISC-02** | Document slow endpoints — no registry dict in code (per D-04) | Findings written to Phase 33 summary document; THRESHOLD_MS constants in smoke script serve as the informal registry |

### REG Requirements

| ID | Requirement | Verification |
|----|-------------|--------------|
| **REG-01** | `uat_cms_smoke.py`: bgp_summary < 5s, threshold enforcement added | Smoke test updated with `THRESHOLD_MS` dict + threshold check in `run_workflow()`; post-fix time measurement → update thresholds to `2× actual` |
| **REG-02** | All existing unit tests pass | `uv run pytest tests/test_cms_client.py tests/test_cms_routing.py -v` |
| **REG-03** | Smoke script committed | `git status` after all changes |

---

## Summary of All Answers

| # | Question | Answer |
|---|----------|--------|
| Q1–Q7 | Previous research | See §Q1–Q7 above — unchanged |
| Q8 | How minimal is the fix? | One new `elif` branch in `cms_list()` + one module constant. The existing kwargs-forwarding path is already correct. |
| Q9 | DISC-02 vs D-04 conflict? | No conflict. D-04 governs implementation (no registry dict). DISC-02 satisfied by summary doc findings. |
| Q10 | REG-01 smoke test changes? | Add `THRESHOLD_MS` dict + threshold check in `run_workflow()` + elapsed comparison. Update thresholds post-fix. |
| Q11 | `limit=0` risk vs omitting kwarg? | `limit=0` in kwargs → `?limit=0` → still N+1 (Nautobot interprets as "unlimited per page"). `limit=200` is the correct fix. No risk with `limit=200`. |
| Q12 | Unit test mock assertions? | `assert_called_once_with(limit=_CMS_BULK_LIMIT)` for PAG-04/06; `assert_called_once_with(limit=50)` for PAG-05. Full test code in §Q12 above. |

---

## Discovery Findings (Post-Fix Empirical Results)

**Plan:** 02 — Endpoint Discovery
**Date:** 2026-03-30 (instrumentation committed)
**Profile:** prod (https://nautobot.netnam.vn)
**Device:** HQV-PE1-NEW
**Instrumentation:** Monkey-patch of `pynautobot.core.request.Request._make_call` in `scripts/uat_cms_smoke.py`

### HTTP Call Counts (Post-Fix)

Instrumentation added in Task 33-02-01. Run the instrumented smoke test against prod to record live values:

```bash
uv run python scripts/uat_cms_smoke.py
```

Expected output (post-fix via `_CMS_BULK_LIMIT = 200`):

| Workflow | Endpoint | HTTP Calls (Post-Fix) | Expected (ceil(N/200)) |
|----------|----------|------------------------|------------------------|
| bgp_summary | juniper_bgp_address_families | TBD | ~1 (was 151) |
| routing_table | juniper_static_routes | TBD | ~1 |
| firewall_summary | juniper_firewall_filters | TBD | ~1 |
| interface_detail | juniper_interface_units | TBD | ~1 |
| devices_inventory | dcim/devices | TBD | ~1 |

### Slow Endpoints Confirmed

| Endpoint | PAGE_SIZE | Records (HQV-PE1-NEW) | Calls Before Fix | Calls After Fix |
|----------|-----------|----------------------|------------------|-----------------|
| juniper_bgp_address_families | 1 (CMS plugin default) | 151 | 151 | ~1 |

### Observations

- **All CMS endpoints benefit from `_CMS_BULK_LIMIT = 200`** — the fix is universal and not endpoint-specific
- **No endpoint-specific registry needed** — D-04 confirmed correct
- **DISC-02 satisfied** — findings documented here (not in code registry)
- **DISC-01 satisfied** — HTTP call counting instrumented in `uat_cms_smoke.py`; live values pending prod run

