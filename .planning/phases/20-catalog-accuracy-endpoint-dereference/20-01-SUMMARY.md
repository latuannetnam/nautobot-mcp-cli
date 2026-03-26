---
plan: 20-01
title: Per-Endpoint Filter Registry
status: complete
completed: 2026-03-25
commit: 8061a6c
---

## Summary

Replaced domain-level `CMS_DOMAIN_FILTERS` with per-endpoint `CMS_ENDPOINT_FILTERS` dict in `cms_discovery.py`. Each of the 33 CMS endpoints now advertises accurate primary FK filter(s). Updated `discover_cms_endpoints()` to look up filters by endpoint name. Added `TestCMSFilterAccuracy` class with 6 tests.

## Key Files

### Modified
- `nautobot_mcp/catalog/cms_discovery.py` — removed `CMS_DOMAIN_FILTERS`, added `CMS_ENDPOINT_FILTERS` (43 entries covering all CMS endpoints), updated `discover_cms_endpoints()` line to use per-endpoint lookup
- `tests/test_catalog.py` — added `TestCMSFilterAccuracy` class with 6 test methods

## Self-Check: PASSED

- `cms_discovery.py` does NOT contain `CMS_DOMAIN_FILTERS` ✓
- `cms_discovery.py` contains `CMS_ENDPOINT_FILTERS` with all 43 entries ✓
- `discover_cms_endpoints()` uses `CMS_ENDPOINT_FILTERS.get(endpoint_name` ✓
- `CMS_ENDPOINT_FILTERS["juniper_bgp_neighbors"]` equals `["group"]` ✓
- `CMS_ENDPOINT_FILTERS["juniper_firewall_terms"]` equals `["firewall_filter"]` ✓
- `pytest tests/test_catalog.py` → **29 passed in 0.09s** ✓
