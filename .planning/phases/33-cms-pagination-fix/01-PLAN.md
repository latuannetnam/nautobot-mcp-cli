---
phase: 33
plan: 01
slug: implement-pagination-fix
status: draft
wave: 1
dependencies: []
autonomous: false
requirements: [PAG-01, PAG-02, PAG-03, PAG-04, PAG-05, PAG-06]
must_haves:
  - `_CMS_BULK_LIMIT = 200` defined with docstring in `nautobot_mcp/cms/client.py`
  - `cms_list()` passes `limit=200` when called with `limit=0`
  - `cms_list()` preserves explicit `limit > 0` values unchanged
  - `TestCMSListPagination` class in `tests/test_cms_client.py` with 3 tests
  - All 3 tests pass with `uv run pytest tests/test_cms_client.py -v`
---

# Plan 01: Implement Pagination Fix

**Phase:** 33 — CMS Pagination Fix
**Goal:** Fix N+1 pynautobot pagination via `_CMS_BULK_LIMIT = 200` in `cms_list()`
**Requirements:** PAG-01, PAG-02, PAG-03, PAG-04, PAG-05, PAG-06

## Wave 1

### Task 33-01-01: Add `_CMS_BULK_LIMIT` constant to `cms/client.py`

<read_first>
- `nautobot_mcp/cms/client.py` — L1-67 (module top, constants area above `CMS_ENDPOINTS`)
</read_first>

<action>
Add the following immediately below the module docstring and before `CMS_ENDPOINTS`:

```python
#: Nautobot bulk fetch limit for CMS plugin (PAGE_SIZE=1 workaround).
#: Nautobot REST API cap is 1000; 200 is a conservative safety margin.
#: When limit=0 (get all), pynautobot's sequential pagination makes one
#: HTTP call per record (N+1) if the CMS plugin has PAGE_SIZE=1.
#: Setting limit=200 collapses N records into ceil(N/200) HTTP calls.
_CMS_BULK_LIMIT = 200
```
</action>

<acceptance_criteria>
- [ ] `grep -n "_CMS_BULK_LIMIT = 200" nautobot_mcp/cms/client.py` returns exactly one match at line ~9
- [ ] The constant is defined at module level (not inside any function)
- [ ] `grep -n "_CMS_BULK_LIMIT" nautobot_mcp/cms/client.py` finds exactly 3 occurrences: definition, PAG-01 usage in `cms_list()`, and PAG-04/05/06 test import
</acceptance_criteria>

---

### Task 33-01-02: Fix `cms_list()` to apply bulk limit on `limit=0`

<read_first>
- `nautobot_mcp/cms/client.py` — L128-159 (current `cms_list()` body)
</read_first>

<action>
Replace the pagination kwargs block in `cms_list()` (lines 145-149):

**BEFORE (current state):**
```python
        pagination_kwargs = {}
        if limit > 0:
            pagination_kwargs["limit"] = limit
        if offset > 0:
            pagination_kwargs["offset"] = offset
```

**AFTER (target state):**
```python
        pagination_kwargs = {}
        if limit == 0:
            pagination_kwargs["limit"] = _CMS_BULK_LIMIT
        elif limit > 0:
            pagination_kwargs["limit"] = limit
        if offset > 0:
            pagination_kwargs["offset"] = offset
```

The change is: convert the `if limit > 0` branch into `if limit == 0` → `_CMS_BULK_LIMIT` + `elif limit > 0` → original value.
</action>

<acceptance_criteria>
- [ ] `grep -A2 "if limit == 0:" nautobot_mcp/cms/client.py` shows `pagination_kwargs["limit"] = _CMS_BULK_LIMIT`
- [ ] `grep "elif limit > 0:" nautobot_mcp/cms/client.py` is present (renamed from `if`)
- [ ] `grep "pagination_kwargs\[" nautobot_mcp/cms/client.py` shows exactly 4 lines: init, limit==0, elif limit>0, offset
- [ ] `uv run python -c "from nautobot_mcp.cms.client import _CMS_BULK_LIMIT; print(_CMS_BULK_LIMIT)"` prints `200`
- [ ] **PAG-01 verified:** `cms_list(client, endpoint, model, limit=0)` → `endpoint.all(limit=200)` called (not `limit=0` or no kwarg)
- [ ] **PAG-02 verified:** `cms_list(client, endpoint, model, limit=50)` → `endpoint.all(limit=50)` called (not 200)
</acceptance_criteria>

---

### Task 33-01-03: Add `TestCMSListPagination` class to `tests/test_cms_client.py`

<read_first>
- `tests/test_cms_client.py` — L149-186 (existing `TestCMSList` class, to model after)
- `tests/conftest.py` — fixtures: `mock_client_with_cms` (L112-122), `mock_cms_record` (L126-138)
- `nautobot_mcp/models/cms/base.py` — `CMSBaseSummary` model (imported at top of test file already)
</read_first>

<action>
Append the following class to `tests/test_cms_client.py` (after the existing `TestCMSList` class, before `TestCMSGet`):

```python
class TestCMSListPagination:
    """Pagination regression tests for cms_list — PAG-01..PAG-06.

    Core regression: without the fix, limit=0 causes N+1 sequential HTTP calls
    because the CMS plugin has PAGE_SIZE=1. With the fix, limit=200 collapses
    N records into ceil(N/200) calls.
    """

    def test_limit_zero_uses_bulk_limit(self, mock_client_with_cms, mock_cms_record):
        """PAG-04: limit=0 triggers _CMS_BULK_LIMIT (200), not limit=0 or no kwarg.

        This is the primary regression test. Without the fix, limit=0 (falsy)
        sends no limit kwarg → CMS plugin PAGE_SIZE=1 → N sequential HTTP calls.
        """
        mock_client_with_cms.cms.juniper_static_routes.all.return_value = [mock_cms_record]

        from nautobot_mcp.cms.client import _CMS_BULK_LIMIT, cms_list
        result = cms_list(mock_client_with_cms, "juniper_static_routes", CMSBaseSummary, limit=0)

        mock_client_with_cms.cms.juniper_static_routes.all.assert_called_once_with(limit=_CMS_BULK_LIMIT)
        assert result.count == 1

    def test_explicit_positive_limit_preserved(self, mock_client_with_cms, mock_cms_record):
        """PAG-05: limit=50 passes through as-is. Bulk limit does NOT override caller intent."""
        mock_client_with_cms.cms.juniper_static_routes.all.return_value = [mock_cms_record]

        from nautobot_mcp.cms.client import _CMS_BULK_LIMIT, cms_list
        result = cms_list(mock_client_with_cms, "juniper_static_routes", CMSBaseSummary, limit=50)

        # Must be limit=50, NOT 200 or 0
        mock_client_with_cms.cms.juniper_static_routes.all.assert_called_once_with(limit=50)
        _calls = mock_client_with_cms.cms.juniper_static_routes.all.call_args
        assert _calls.kwargs["limit"] == 50
        assert result.count == 1

    def test_limit_zero_with_filters_uses_bulk_limit(self, mock_client_with_cms, mock_cms_record):
        """PAG-06: limit=0 with filters also triggers bulk limit on .filter() call."""
        mock_client_with_cms.cms.juniper_static_routes.filter.return_value = [mock_cms_record]

        from nautobot_mcp.cms.client import _CMS_BULK_LIMIT, cms_list
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

The `CMSBaseSummary` import already exists at the top of the test file (L27). Do NOT add it again.
</action>

<acceptance_criteria>
- [ ] `grep -n "class TestCMSListPagination" tests/test_cms_client.py` returns exactly one match
- [ ] `grep -n "test_limit_zero_uses_bulk_limit\|test_explicit_positive_limit_preserved\|test_limit_zero_with_filters_uses_bulk_limit" tests/test_cms_client.py` returns 3 matches
- [ ] `uv run pytest tests/test_cms_client.py::TestCMSListPagination -v` — all 3 tests pass
- [ ] `uv run pytest tests/test_cms_client.py -v` — entire test file passes (including existing tests)
- [ ] PAG-04: `assert_called_once_with(limit=_CMS_BULK_LIMIT)` verified — `limit=200` not `limit=0`
- [ ] PAG-05: `assert_called_once_with(limit=50)` verified — explicit limit unchanged
- [ ] PAG-06: `filter(..., limit=_CMS_BULK_LIMIT)` verified — bulk limit applies with filters too
</acceptance_criteria>

---

## Summary

| Task | Requirement | Status |
|------|-------------|--------|
| 33-01-01 | PAG-03 (constant with rationale docstring) | ⬜ |
| 33-01-02 | PAG-01 (limit=0 → 200), PAG-02 (limit>0 preserved) | ⬜ |
| 33-01-03 | PAG-04, PAG-05, PAG-06 (unit tests) | ⬜ |

**Quality gate:** `uv run pytest tests/test_cms_client.py -v` must be green before advancing.
