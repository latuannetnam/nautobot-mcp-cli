# Phase 36 Plan 03 Summary — `firewall_summary` N+1 Invariant Tests

**Commit:** `683ff5c`
**Date:** 2026-03-31
**Status:** ✅ SHIPPED

## What was done

Created `tests/test_cms_firewalls_n1.py` with 8 N+1 invariant tests for `get_device_firewall_summary(detail=True)`. Pattern follows `tests/test_cms_interfaces_n1.py` (Phase 35) exactly.

## Tests added

| # | Test | Verifies |
|---|------|----------|
| 1 | `test_firewall_summary_bulk_prefetch_exactly_2_calls` | CQP-02: exactly 2 `cms_list` calls (bulk terms + bulk actions); 5 filters × 10 terms + 3 policers × 5 actions |
| 2 | `test_firewall_summary_no_per_filter_terms_calls` | CQP-02: `list_firewall_terms` never called per-filter (failsafe `AssertionError`) |
| 3 | `test_firewall_summary_no_per_policer_actions_calls` | CQP-02: `list_firewall_policer_actions` never called per-policer (failsafe `AssertionError`) |
| 4 | `test_firewall_summary_terms_prefetch_failure_graceful` | CQP-05: bulk terms prefetch failure → WarningCollector warning, all filters get `terms = []` |
| 5 | `test_firewall_summary_actions_prefetch_failure_graceful` | CQP-05: bulk actions prefetch failure → WarningCollector warning, all policers get `actions = []` |
| 6 | `test_firewall_summary_terms_enriched_from_prefetch_map` | CQP-02: filter-A (3 terms) and filter-B (0 terms) correctly resolved from prefetch map |
| 7 | `test_firewall_summary_actions_enriched_from_prefetch_map` | CQP-02: policer-X (2 actions) and policer-Y (0 actions) correctly resolved from prefetch map |
| 8 | `test_firewall_summary_detail_false_unaffected` | CQP-02: `detail=False` path makes no `cms_list` calls (prefetch block inside `if detail:`) |

## Key implementation detail

The bulk prefetch uses `cms_list(..., device=device_id)` internally — NOT `list_firewall_terms` or `list_firewall_policer_actions` directly. Tests 2 and 3 use `patch.object(fw_module, "list_firewall_terms/...")` as failsafes to prove the per-filter/per-policer N+1 loops are gone from the call path.

## Bug fixed during test creation

`_mock_filter()` and `_mock_policer()` helpers prefixed string IDs with `filter-`/`policer-`, causing e.g. `"filter-A"` → `"filter-filter-A"`. Fixed with `isinstance(idx, str)` guard to pass through string IDs unchanged.

## Result

```
tests/test_cms_firewalls_n1.py: 8 passed in 0.09s
```

## Files created

- `tests/test_cms_firewalls_n1.py` (517 lines)
