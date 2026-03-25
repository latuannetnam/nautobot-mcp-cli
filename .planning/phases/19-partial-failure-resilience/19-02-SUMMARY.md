---
plan: 19-02
phase: 19
title: Composite Function Partial Failure Refactor
status: complete
wave: 2
timestamp: 2026-03-25T15:58:00+07:00
---

# Summary: Plan 19-02 — Composite Function Partial Failure Refactor

## What Was Built

### Task 1: `get_device_bgp_summary` (routing.py)
- Added `WarningCollector` import
- Each per-neighbor enrichment call (`list_bgp_address_families`, `list_bgp_policy_associations`) wrapped inin individual `try/except` with `collector.add()`
- Returns `(BGPSummaryResponse, collector.warnings)`

### Task 2: `get_device_routing_table` (routing.py)
- Added `WarningCollector` (currently no sub-calls — ready for future nexthop enrichment)
- Returns `(RoutingTableResponse, collector.warnings)`

### Task 3: `get_device_firewall_summary` (firewalls.py)
- **Independent co-primaries pattern**: filters and policers are fetched independently
- If only one fails → other's data returned with a warning
- If **both** fail → `RuntimeError` raised (produces `error` envelope)
- Detail-mode enrichment (`list_firewall_terms`, `list_firewall_policer_actions`) also captured
- Returns `(FirewallSummaryResponse, collector.warnings)`

### Task 4: `get_interface_detail` (interfaces.py)
- Per-family VRRP enrichment failures captured with `collector.add()`
- Optional ARP enrichment failure captured with `collector.add()`
- Returns `(InterfaceDetailResponse, collector.warnings)`

### Task 5: Integration tests (test_cms_composites.py)
- Updated 8 existing tests to unpack `(result, warnings)` tuples
- Added 7 new partial failure integration tests:
  - `test_bgp_summary_detail_address_family_enrichment_failure`
  - `test_bgp_summary_detail_policy_enrichment_failure`
  - `test_firewall_summary_filters_failure_policers_partial`
  - `test_firewall_summary_both_fail_raises`
  - `test_firewall_summary_detail_term_enrichment_failure`
  - `test_interface_detail_vrrp_enrichment_failure`
  - `test_interface_detail_arp_enrichment_failure`

## Test Results

- `pytest tests/` → **415 passed, 11 deselected** (0 failures, 0 regressions)
- New tests: 7 partial failure integration tests (all pass)

## Self-Check: PASSED

All Phase 19-02 acceptance criteria met:
- [x] All 4 composites return `(result, warnings)` tuples
- [x] Independent co-primaries in `get_device_firewall_summary` — one failure does not block the other
- [x] Both-fail guard in `get_device_firewall_summary` raises `RuntimeError`
- [x] All enrichment `except Exception` blocks use `collector.add()` instead of `pass` / `except Exception: pass`
- [x] 7 new integration tests for partial failure paths
- [x] All 415 tests pass
