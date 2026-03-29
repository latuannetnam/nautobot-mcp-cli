---
phase: 30-direct-http-bulk-fetch
plan: "30-PLAN"
subsystem: ipam
tags: [nautobot, pynautobot, http, bulk-fetch, testing, m2m]

# Dependency graph
requires:
  - phase: 29-direct-http-count
    provides: direct HTTP session usage pattern + profile.url access
provides:
  - _bulk_get_by_ids() helper: DRF comma-separated bulk fetch with pagination
  - get_device_ips() refactored to O(3) direct HTTP calls (was O(3*N/chunk_size))
  - Partial failure detection: stale IPs → unlinked_ips stubs
affects:
  - 31-bridge-guard-uri-limit
  - 32-vlans-count-fix

# Tech tracking
tech-stack:
  added: [unittest.mock]
  patterns:
    - Direct HTTP with comma-separated UUIDs: ?id__in=a,b,c (avoids 414)
    - Next-link pagination: while data["next"]: resp = get(data["next"]); collect
    - return_obj wrapping: pynautobot Record from raw dict (no HTTP call)
    - Side-effect mock chain: sequential HTTP responses for multi-pass functions

key-files:
  created: [tests/test_ipam.py]
  modified: [nautobot_mcp/ipam.py]

key-decisions:
  - "DRF comma-separated: ?interface=uuid1,uuid2,uuid3 — ~3x shorter than repeated ?interface=uuid1&interface=uuid2"
  - "return_obj side_effect: nested .ip_address.id must return string UUID, not MagicMock internal int"
  - "Sequential mock via side_effect list: both _mock_pass2 and _mock_pass3 append to http_session.get side_effect"
  - "Empty ip_ids early return: Pass 3 skipped when M2M returns no IP IDs"
  - "Stale UUID detection: fetched_ids vs requested_ids → missing_ip_ids → IPAddressSummary stubs"

patterns-established:
  - "Pattern: _bulk_get_by_ids(client, endpoint, ids, id_param) — module-level helper for any endpoint"
  - "Pattern: return_obj(d, client.api, endpoint) — wraps raw dict to pynautobot Record without HTTP"

requirements-completed: [URI-01, URI-02, URI-03, URI-04, URI-05, URI-06]

# Metrics
duration: 8min
completed: 2026-03-29
---

# Phase 30 Plan 30: Direct HTTP Bulk Fetch for get_device_ips() Summary

**Direct HTTP bulk fetch replaces O(3N/chunk_size) chunked .filter() loops in get_device_ips() with O(3) comma-separated UUID calls, plus partial failure detection for stale IPs**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-29T02:37:04Z
- **Completed:** 2026-03-29T02:44:38Z
- **Tasks:** 3 completed
- **Files:** 2 (1 modified, 1 created)

## Accomplishments
- `_bulk_get_by_ids()` helper: single direct HTTP call with DRF comma-separated UUIDs, auto-follows next links, wraps via `endpoint.return_obj()`
- `get_device_ips()` Pass 2 & 3 refactored: chunked `.filter()` loops → `_bulk_get_by_ids()`, no chunking at all (single bulk call)
- Empty `ip_ids` early return: Pass 3 skipped when M2M returns zero IP IDs
- Partial failure detection: stale/deleted IPs detected via `fetched_ids vs requested_ids`, surfaced in `unlinked_ips` as `IPAddressSummary` stubs
- 11 new unit tests (5 for `_bulk_get_by_ids`, 6 for `get_device_ips`) — 29 total tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Extract _bulk_get_by_ids() helper** - `15676b5` (feat)
2. **Task 2: Replace Pass 2 and Pass 3 in get_device_ips()** - `15676b5` (same commit as Task 1)
3. **Task 3: Add unit tests** - `5686f48` (test)

**Plan metadata:** `N/A` (no metadata commit — STATE.md updated in-plan)

## Files Created/Modified
- `nautobot_mcp/ipam.py` — Added `_bulk_get_by_ids()` helper; replaced Pass 2 & 3 chunked loops with direct HTTP; added stale IP detection
- `tests/test_ipam.py` — New test file: `TestBulkGetByIds` (5 tests) + `TestGetDeviceIPs` (6 tests)

## Decisions Made

- **DRF comma-separated over repeated params:** `?interface=uuid1,uuid2,uuid3` avoids the `414 Request-URI Too Large` error that repeated `?interface=uuid1&interface=uuid2` triggers on large device inventories
- **`return_obj` side_effect for mock chain:** pynautobot's `return_obj()` wraps raw dicts into Records — nested `.ip_address.id` must return a string UUID (not MagicMock's internal int), so mock `return_obj.side_effect` is set to a lambda that builds structured records
- **Sequential mock via side_effect list:** Both `_mock_pass2` and `_mock_pass3` configure different HTTP responses — appending to `http_session.get.side_effect` ensures correct order (Pass 2 → Pass 3)
- **Empty `ip_ids` early return:** When M2M finds no IP IDs, skip Pass 3 entirely (returns empty `DeviceIPsResponse` immediately)
- **Stale UUID detection:** Computing `requested_ids - fetched_ids` catches IPs that were deleted from Nautobot between the M2M query and the IP detail query — surfaced in `unlinked_ips` as `IPAddressSummary(id=missing_id, address="<deleted>")`

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

1. **Mock chain bug (fixed):** Both `_mock_pass2` and `_mock_pass3` set `http_session.get.return_value` — only the last assignment survived. Fixed by using `side_effect=[existing, mock_resp]` to append sequential responses. Root cause: two independent helper methods each overwriting the other's response.

2. **`return_obj` nested attribute issue:** `pynautobot`'s `return_obj()` creates Record objects where nested attributes (`.ip_address`, `.interface`) return MagicMock's internal int when accessed as `.id` on a nested mock. Fixed by setting `return_obj.side_effect` lambda to build properly structured mock records with explicit string UUID fields.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `_bulk_get_by_ids()` helper is available for reuse in other modules (e.g., bridge guard in phase 31)
- Partial failure pattern (`fetched_ids - requested_ids → unlinked_ips`) is proven — can apply to other bulk operations
- `tests/test_ipam.py` covers the core bulk fetch path; ready for additional test cases

---
*Phase: 30-direct-http-bulk-fetch*
*Completed: 2026-03-29*
