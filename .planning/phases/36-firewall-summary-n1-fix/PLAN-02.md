---
gsd:
  wave: 1
  depends_on: []
  files_modified: []
  autonomous: true
---

# Plan 02: N+1 Verification Gate (No Code Changes)

## Goal

Verify that the N+1 fix in `get_device_firewall_summary(detail=True)` meets CQP-02 (≤6 HTTP calls) and CQP-05 (WarningCollector graceful degradation) by running the test suite produced by Plan 03.

**No code changes** — this plan verifies the fix is correct.

## Prerequisites

Plan 01 must be complete (bulk prefetch code applied to `nautobot_mcp/cms/firewalls.py`).

## Verification

```bash
cd d:/latuan/Programming/nautobot-mcp-cli
uv run pytest tests/test_cms_firewalls_n1.py -v
```

All 8 tests must pass:
- `test_firewall_summary_bulk_prefetch_exactly_6_calls`
- `test_firewall_summary_no_per_filter_terms_calls`
- `test_firewall_summary_no_per_policer_actions_calls`
- `test_firewall_summary_terms_prefetch_failure_graceful`
- `test_firewall_summary_actions_prefetch_failure_graceful`
- `test_firewall_summary_terms_enriched_from_prefetch_map`
- `test_firewall_summary_actions_enriched_from_prefetch_map`
- `test_firewall_summary_detail_false_unaffected`

Also run the full unit suite to confirm no regressions:

```bash
uv run pytest tests/test_cms_firewalls.py -v
```

All tests in `test_cms_firewalls.py` must still pass.

## must_haves

- `uv run pytest tests/test_cms_firewalls_n1.py` exits 0 with 8 tests passing
- `uv run pytest tests/test_cms_firewalls.py` exits 0 (no regression)
- `uv run pytest tests/test_cms_composites.py` exits 0 (firewall_summary response model still correct)
