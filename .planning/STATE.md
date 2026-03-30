---
gsd_state_version: 1.0
milestone: v1.9
milestone_name: CMS Performance Fix
status: defining_requirements
last_updated: "2026-03-30T12:00:00.000Z"
last_activity: 2026-03-30
progress:
  total_phases: 34
  completed_phases: 33
  total_plans: 62
  completed_plans: 62
---

# Project State: nautobot-mcp-cli

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-30)

**Core value:** AI agents can discover, read, write, and orchestrate Nautobot data through 3 tools instead of 165
**Current focus:** Phase 33 — cms-pagination-fix

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-30 — v1.9 CMS Performance Fix started

## Context

**Root cause from v1.8 UAT (2026-03-30):**

Two workflows in `uat_cms_smoke.py` exceeded thresholds:

1. **`bgp_summary`: 85,796ms (threshold: 5,000ms)** — `get_device_bgp_summary()` in `cms/routing.py` unconditionally calls `list_bgp_address_families(limit=0)` and `list_bgp_policy_associations(limit=0)` even when `detail=False`. HQV-PE1-NEW has **0 BGP groups** — these fetches serve no purpose. Both endpoints **timeout at `limit=1`** (>60s) on prod server — likely unindexed global scans. Fix: gate behind `if detail:`.

2. **`devices_inventory`: 25,829ms (threshold: 15,000ms)** — CLI default `--limit 50` fetches 709 interfaces serially. `limit=0` (all) times out entirely. `list_interfaces()` doesn't use `_CMS_BULK_LIMIT`. Fix: apply `_CMS_BULK_LIMIT` to `list_interfaces()` when `limit=0`; adjust CLI default.

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Gate AF/policy fetches behind `detail=True` | These endpoints are only used in detail mode; unconditional calls cause 60s+ timeouts even at limit=1 |
| Apply `_CMS_BULK_LIMIT` to interface fetches | Same PAGE_SIZE=1 N+1 issue as other CMS endpoints; consistent treatment |
| No research needed | Scope is well-understood from UAT timing data |

## Accumulated Context

- v1.0 shipped 2026-03-18 with core MCP + CLI + parsing/onboarding foundations
- v1.1 shipped 2026-03-20 with agent-native tools and file-free drift
- v1.2 shipped 2026-03-21 with Juniper CMS CRUD + composite tools + CMS drift
- v1.3 shipped 2026-03-25 with 165→3 API Bridge consolidation
- v1.4 shipped 2026-03-26 with robustness, diagnostics, and response ergonomics
- v1.6 shipped 2026-03-28 with query performance optimizations
- v1.7 shipped 2026-03-29 with URI limit fixes, VLANs 500 fix, and UAT smoke script
- v1.8 started 2026-03-30 to fix CMS N+1 pagination in composite functions

## Blockers

None.

## Validated (v1.8 — CMS Pagination Fix)

- ✓ `_CMS_BULK_LIMIT = 200` constant in `cms/client.py` — collapses 151 sequential HTTP calls into 1 for CMS endpoints with PAGE_SIZE=1 — v1.8 Phase 33 Plan 01
- ✓ `cms_list()` updated: `limit=0 → limit=200` via kwarg; explicit `limit > 0` preserved via `elif` branch — v1.8 Phase 33 Plan 01
- ✓ `TestCMSListPagination` regression suite (3 tests, 29/29 total passing) — v1.8 Phase 33 Plan 01
- ✓ Rule 1 auto-fix: `test_list_with_filters` corrected to expect `limit=200` on `.filter()` — pre-existing test encoded the exact bug being fixed — v1.8 Phase 33 Plan 01
- ✓ `uat_cms_smoke.py` regression gate with per-workflow HTTP call counting via pynautobot monkey-patch — v1.8 Phase 33 Plan 02
- ✓ Live verified: routing_table, firewall_summary, interface_detail pass within thresholds — v1.8 Phase 33 Plan 03
- ✓ bgp_summary fails UAT: 85,796ms > 5,000ms threshold (root cause: AF/policy endpoints timeout at >60s) — v1.9 trigger
- ✓ devices_inventory fails UAT: 25,829ms > 15,000ms threshold (root cause: no bulk limit on interface fetches) — v1.9 trigger

## Validated (v1.7 — Phase 31: Bridge Param Guard)

- ✓ `_guard_filter_params()` guard function in bridge.py — intercepts `__in`-suffixed filter params before `.filter()` calls — v1.7 Phase 31
- ✓ Raises `NautobotValidationError` for `__in` lists > 500 items — prevents 414 Request-URI Too Large from external callers — v1.7 Phase 31
- ✓ Converts `__in` lists ≤ 500 to DRF-native comma-separated strings — reduces query string size for large-but-valid lists — v1.7 Phase 31
- ✓ Non-`__in` list params (tag, status, location) pass through unchanged — no regression on existing callers — v1.7 Phase 31
- ✓ Guard wired into `_execute_core()` and `_execute_cms()` — covers both Nautobot core and CMS plugin endpoints — v1.7 Phase 31
- ✓ 18 unit tests: `TestParamGuard` (13) + `TestParamGuardIntegration` (5) — full coverage of guard logic and integration — v1.7 Phase 31

## Validated (v1.7 — Phase 30: Direct HTTP Bulk Fetch)

- ✓ `_bulk_get_by_ids()` helper — single direct HTTP call with DRF comma-separated UUIDs, auto-follows `next` links, wraps via `endpoint.return_obj()` — v1.7 Phase 30
- ✓ `get_device_ips()` Pass 2 & 3 refactored: chunked `.filter()` loops → `_bulk_get_by_ids()` — no 414 for large devices — v1.7 Phase 30
- ✓ Stale IP detection: `fetched_ids - requested_ids` surfaces deleted IPs as `unlinked_ips` stubs — v1.7 Phase 30
- ✓ 11 new unit tests in `tests/test_ipam.py` — 29 total tests pass — v1.7 Phase 30

## Validated (v1.7 — Phase 32: VLANs 500 Fix)

- ✓ VLAN count graceful degradation: `vlan_count → Optional[int]`, `warnings: Optional[list[dict]]` in `DeviceStatsResponse` and `DeviceInventoryResponse` — v1.7 Phase 32
- ✓ `device.location.id` (UUID) used at all VLAN count call sites instead of `location.name` — v1.7 Phase 32
- ✓ `NautobotAPIError` caught in all 4 VLAN count paths: summary, inventory sequential, inventory parallel, inventory fallback — v1.7 Phase 32
- ✓ `RetryError` catch in `client.count()` — HTTP retries exhaust on 500 → pynautobot fallback works cleanly — v1.7 Phase 32
- ✓ `N/A` display in CLI when `vlan_count` is null — v1.7 Phase 32
- ✓ Live verified: `devices summary HQV-PE1-NEW` → `"vlan_count": 2381` (was 500) — v1.7 Phase 32
- ✓ 11 new unit tests: `TestVLANCount500` (3) + `TestDeviceVLANCountErrorHandling` (8) — v1.7 Phase 32
- ✓ 443 total unit tests pass — no regression — v1.7 Phase 32

---
*State initialized: 2026-03-28*
*Last updated: 2026-03-30 — v1.9 CMS Performance Fix milestone started*
