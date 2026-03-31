---
gsd:
  wave: 2
  depends_on:
    - PLAN-01
  files_modified:
    - tests/test_cms_firewalls_n1.py
  autonomous: true
---

# Plan 03: Unit Tests for `firewall_summary` Bulk Lookup Invariants

## Goal

Create `tests/test_cms_firewalls_n1.py` with 8 N+1 invariant tests for `get_device_firewall_summary(detail=True)`. Follow the Phase 35 pattern in `tests/test_cms_interfaces_n1.py` exactly.

**Addresses CQP-02** (≤6 HTTP calls) and **CQP-05** (WarningCollector preserved).

## Actions

### A. Read reference files before writing tests

Read these files in order:
1. `nautobot_mcp/cms/firewalls.py` (lines 650-750) — post-fix `get_device_firewall_summary` state
2. `tests/test_cms_interfaces_n1.py` — Phase 35 test pattern to replicate exactly
3. `nautobot_mcp/models/cms/composites.py` — `FirewallSummaryResponse` Pydantic model fields
4. `nautobot_mcp/cms/firewalls.py` (lines 1-50) — module imports (`FirewallTermSummary`, `FirewallPolicerActionSummary`, `WarningCollector`)

### B. Create `tests/test_cms_firewalls_n1.py`

Write the file with exactly these 8 tests:

#### Test 1: `test_firewall_summary_bulk_prefetch_exactly_6_calls`

**read_first:** `tests/test_cms_interfaces_n1.py` (lines 53-94 — pattern: bulk prefetch call counting)

Verifies CQP-02: `cms_list` called exactly 2 times (bulk terms + bulk actions prefetch). The co-primaries (`list_firewall_filters`, `list_firewall_policers`) are patched as unit returns and do NOT go through `cms_list` in this test. So `cms_list.call_count == 2`.

Mock setup:
- 5 filters × 10 terms each = 50 total terms
- 3 policers × 5 actions each = 15 total actions
- `list_firewall_filters` returns `_mock_list_response(*filters)` with `term_count` pre-set on each filter mock
- `list_firewall_policers` returns `_mock_list_response(*policers)` with `action_count` pre-set on each policer mock
- `cms_list` side_effect: returns terms ListResponse for `juniper_firewall_terms`, returns actions ListResponse for `juniper_firewall_policer_actions`
- `resolve_device_id` patched to return `"device-uuid-1"`

Assertions:
```python
assert mock_cms.call_count == 2
assert isinstance(result, FirewallSummaryResponse)
assert result.device_name == "edge-01"
assert result.total_filters == 5
assert result.total_policers == 3
```

#### Test 2: `test_firewall_summary_no_per_filter_terms_calls`

**read_first:** `tests/test_cms_interfaces_n1.py` (lines 101-129 — pattern: per-unit function failsafe patch)

Verifies CQP-02: `list_firewall_terms` is never called per-filter. Use `patch.object` on the module to raise `AssertionError("N+1! list_firewall_terms called per-filter")`.

Mock setup: 3 filters, `cms_list` returns 30 total terms (10 per filter). If `list_firewall_terms` is called, `AssertionError` is raised and the test fails.

Assertions:
```python
result, warnings = get_device_firewall_summary(client, device="edge-01", detail=True)
assert isinstance(result, FirewallSummaryResponse)
assert result.total_filters == 3
# If we reach here, list_firewall_terms was NOT called (N+1 eliminated)
```

#### Test 3: `test_firewall_summary_no_per_policer_actions_calls`

**read_first:** `tests/test_cms_interfaces_n1.py` (lines 136-162 — pattern: per-family VRRP failsafe)

Verifies CQP-02: `list_firewall_policer_actions` is never called per-policer. Use `patch.object` to raise `AssertionError("N+1! list_firewall_policer_actions called per-policer")`.

Mock setup: 4 policers, `cms_list` returns 20 total actions. Same failsafe pattern.

Assertions:
```python
result, warnings = get_device_firewall_summary(client, device="edge-01", detail=True)
assert isinstance(result, FirewallSummaryResponse)
assert result.total_policers == 4
# If we reach here, list_firewall_policer_actions was NOT called (N+1 eliminated)
```

#### Test 4: `test_firewall_summary_terms_prefetch_failure_graceful`

**read_first:** `tests/test_cms_interfaces_n1.py` (lines 199-234 — pattern: VRRP graceful degradation)

Verifies CQP-05: Bulk terms prefetch failure → WarningCollector warning, empty `terms_by_filter = {}`, all filters get `terms = []`.

Mock setup: `cms_list` raises `RuntimeError("Terms endpoint 503")` when `juniper_firewall_terms` endpoint is called. Filters and policers co-primaries succeed.

Assertions:
```python
assert len(warnings) == 1
assert warnings[0]["operation"] == "bulk_terms_fetch"
assert "Terms endpoint 503" in warnings[0]["error"]
# All filters should have empty terms
for f in result.filters:
    assert f["terms"] == []
```

#### Test 5: `test_firewall_summary_actions_prefetch_failure_graceful`

**read_first:** `tests/test_cms_interfaces_n1.py` (lines 199-234)

Verifies CQP-05: Bulk actions prefetch failure → WarningCollector warning, empty `actions_by_policer = {}`, all policers get `actions = []`.

Mock setup: `cms_list` raises `RuntimeError("Actions endpoint timeout")` when `juniper_firewall_policer_actions` endpoint is called.

Assertions:
```python
assert len(warnings) == 1
assert warnings[0]["operation"] == "bulk_actions_fetch"
assert "Actions endpoint timeout" in warnings[0]["error"]
# All policers should have empty actions
for p in result.policers:
    assert p["actions"] == []
```

#### Test 6: `test_firewall_summary_terms_enriched_from_prefetch_map`

**read_first:** `tests/test_cms_interfaces_n1.py` (lines 241-281 — pattern: VRRP data from prefetched map)

Verifies CQP-02: Term data is correctly resolved from prefetched `terms_by_filter` map.

Mock setup:
- 2 filters: `filter-A` (id="filter-A", has 3 terms), `filter-B` (id="filter-B", has 0 terms)
- Bulk terms response: 3 terms all with `filter_id = "filter-A"`
- `filter-B` has no terms in bulk response

Assertions:
```python
filter_ids = {f["id"] for f in result.filters}
assert "filter-A" in filter_ids
assert "filter-B" in filter_ids
filter_A = next(f for f in result.filters if f["id"] == "filter-A")
assert filter_A["term_count"] == 3
assert len(filter_A["terms"]) == 3
filter_B = next(f for f in result.filters if f["id"] == "filter-B")
assert filter_B["term_count"] == 0
assert filter_B["terms"] == []
```

#### Test 7: `test_firewall_summary_actions_enriched_from_prefetch_map`

**read_first:** `tests/test_cms_interfaces_n1.py` (lines 241-281 — analogous pattern)

Verifies CQP-02: Action data is correctly resolved from prefetched `actions_by_policer` map.

Mock setup:
- 2 policers: `policer-X` (id="policer-X", has 2 actions), `policer-Y` (id="policer-Y", has 0 actions)
- Bulk actions response: 2 actions both with `policer_id = "policer-X"`

Assertions:
```python
policer_ids = {p["id"] for p in result.policers}
assert "policer-X" in policer_ids
assert "policer-Y" in policer_ids
policer_X = next(p for p in result.policers if p["id"] == "policer-X")
assert policer_X["action_count"] == 2
assert len(policer_X["actions"]) == 2
policer_Y = next(p for p in result.policers if p["id"] == "policer-Y")
assert policer_Y["action_count"] == 0
assert policer_Y["actions"] == []
```

#### Test 8: `test_firewall_summary_detail_false_unaffected`

**read_first:** `tests/test_cms_interfaces_n1.py` (lines 288-325 — pattern: summary mode unaffected)

Verifies CQP-02: `detail=False` path makes no prefetch calls (prefetch block is inside `if detail:`).

Mock setup:
- Patch `cms_list` to raise `AssertionError("N+1! cms_list called in detail=False path")`
- Only `list_firewall_filters` and `list_firewall_policers` patched as unit returns

Assertions:
```python
result, warnings = get_device_firewall_summary(client, device="edge-01", detail=False)
assert isinstance(result, FirewallSummaryResponse)
# No cms_list calls for detail=False
mock_cms.assert_not_called()
```

### C. File header comment

Add this docstring at the top of `tests/test_cms_firewalls_n1.py`:

```python
"""Tests for firewall_summary N+1 fix — bulk prefetch invariants.

Verifies:
- Exactly 2 bulk cms_list calls (bulk terms + bulk actions prefetch) (CQP-02)
- list_firewall_terms never called per-filter (CQP-02)
- list_firewall_policer_actions never called per-policer (CQP-02)
- Terms prefetch failure graceful degradation with WarningCollector (CQP-05)
- Actions prefetch failure graceful degradation with WarningCollector (CQP-05)
- Terms/actions correctly enriched from prefetch maps (CQP-02)
- detail=False path unaffected (no prefetch block entered) (CQP-02)
"""
```

### D. Required imports

```python
from unittest.mock import MagicMock, patch

import pytest

from nautobot_mcp.models.base import ListResponse
from nautobot_mcp.models.cms.composites import FirewallSummaryResponse
```

**Note:** `FirewallSummaryResponse` is imported from line 650 of `firewalls.py` (added at module reload); for tests it is imported from `nautobot_mcp.models.cms.composites` (already used in Phase 35).

## Verification

```bash
cd d:/latuan/Programming/nautobot-mcp-cli
uv run pytest tests/test_cms_firewalls_n1.py -v
```

All 8 tests must pass.

## must_haves

- `tests/test_cms_firewalls_n1.py` contains `def test_firewall_summary_bulk_prefetch_exactly_6_calls(`
- `tests/test_cms_firewalls_n1.py` contains `def test_firewall_summary_no_per_filter_terms_calls(`
- `tests/test_cms_firewalls_n1.py` contains `def test_firewall_summary_no_per_policer_actions_calls(`
- `tests/test_cms_firewalls_n1.py` contains `def test_firewall_summary_terms_prefetch_failure_graceful(`
- `tests/test_cms_firewalls_n1.py` contains `def test_firewall_summary_actions_prefetch_failure_graceful(`
- `tests/test_cms_firewalls_n1.py` contains `def test_firewall_summary_terms_enriched_from_prefetch_map(`
- `tests/test_cms_firewalls_n1.py` contains `def test_firewall_summary_actions_enriched_from_prefetch_map(`
- `tests/test_cms_firewalls_n1.py` contains `def test_firewall_summary_detail_false_unaffected(`
- `tests/test_cms_firewalls_n1.py` imports `FirewallSummaryResponse` from `nautobot_mcp.models.cms.composites`
- `tests/test_cms_firewalls_n1.py` imports `ListResponse` from `nautobot_mcp.models.base`
- `uv run pytest tests/test_cms_firewalls_n1.py -v` exits 0 with 8 tests passing
