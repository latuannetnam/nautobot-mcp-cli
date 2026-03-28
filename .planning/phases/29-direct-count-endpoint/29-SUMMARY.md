---
phase: 29-direct-count-endpoint
plan: 1
subsystem: perf
tags: [count, performance, latency, bridge, client]

requires: []
provides:
  - NautobotClient.count() — O(1) /count/ endpoint method with 404→pynautobot fallback
  - All 8 .count() call sites in devices.py replaced with client.count()
  - latency_ms in every call_nautobot response envelope
affects: [v1.6-query-perf, phases-30-plus]

tech-stack:
  added: []
  patterns:
    - Direct HTTP GET to /count/ endpoint for O(1) counts
    - Wall-clock latency instrumentation in bridge response
    - 404-fallback pattern for endpoints lacking /count/ support

key-files:
  created: []
  modified:
    - nautobot_mcp/client.py
    - nautobot_mcp/devices.py
    - nautobot_mcp/bridge.py

key-decisions:
  - "Direct /count/ via http_session.get() — pynautobot's .count() auto-paginates through ALL records; calling the Nautobot /count/ endpoint directly is O(1)"
  - "404 fallback to pynautobot — some plugin endpoints don't expose /count/; 404 is not an error, it's a signal to use the O(n) fallback"
  - "Full-call latency in bridge — wrapping the entire call_nautobot try block captures routing + execution + serialization time in one number"

patterns-established:
  - "count() replacement: client.count(app, endpoint, **filters) replaces all raw .count() calls"
  - "latency_ms envelope: result['latency_ms'] = round((time.time() - t_start) * 1000, 1) on success and in NautobotMCPError handler"

requirements-completed: [PERF-03, PERF-04, OBS-02]

duration: ~3 min
completed: 2026-03-28
---

# Phase 29: Direct /count/ Endpoint Summary

**O(1) /count/ via direct HTTP, latency instrumentation in bridge, all 8 call sites migrated**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-28T10:20:58Z
- **Completed:** 2026-03-28T10:24:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- `NautobotClient.count(app, endpoint, **filters)` — O(1) via `GET /api/{app}/{endpoint}/count/`, with HTTP 404 fallback to pynautobot's O(n) `.count()`
- All 8 `client.api.{app}.{endpoint}.count(...)` calls in `devices.py` replaced with `client.count("app", "endpoint", ...)`
- `latency_ms` added to every `nautobot_call_nautobot` success response and `NautobotMCPError` handler — full-call wall-clock timing visible to agents

## Task Commits

Each task was committed atomically:

1. **Task 1: NautobotClient.count() method** — `67fa39f` (feat)
2. **Task 2: Replace all .count() call sites in devices.py** — `68d40ad` (perf)
3. **Task 3: Add latency_ms to bridge response envelope** — `b78e39e` (obs)

## Files Created/Modified
- `nautobot_mcp/client.py` — Added `count()` method (44 lines) + `import requests`
- `nautobot_mcp/devices.py` — Replaced 8 `.count()` calls with `client.count()` (12 insertions, 13 deletions)
- `nautobot_mcp/bridge.py` — Added `import time`, wrapped `call_nautobot` try block with wall-clock timing + `latency_ms` in response (9 insertions, 2 deletions)

## Decisions Made

- **HTTP 404 → fallback:** When `/count/` is unavailable (plugin endpoints), 404 is a valid signal to fall back to pynautobot's auto-paginating count. Only non-404 errors are propagated via `raise_for_status()`.
- **Latency on error:** `NautobotMCPError` exceptions are re-raised (can't modify exception object), but a `result` dict with `latency_ms` is created before re-raising for observability in logs.
- **Full-call timing:** `t_start` is recorded before the routing decision, capturing the entire call including any `resolve_device_id` overhead in CMS calls.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- Phase 30 next — direct-count-endpoint scope is complete (8 call sites migrated, latency instrumented)
- Unit tests: 478 passed, 0 failed (11 deselected UAT tests require live server)
- All acceptance criteria from all 3 tasks verified before commit

---
*Phase: 29-direct-count-endpoint*
*Completed: 2026-03-28*
