---
phase: 28-adaptive-count-fast-pagination
plan: 01
subsystem: api
tags: [pynautobot, pagination, performance, timing, mcp, cli]

# Dependency graph
requires:
  - phase: [prior phases built the 3-tool API bridge and device inventory foundation]
    provides: "DeviceInventoryResponse model, get_device_inventory(), CLI device inventory command"
provides:
  - "Adaptive count skipping — skip_count=True or limit=0 bypasses all count() calls"
  - "has_more inference from len(results)==limit when count is skipped"
  - "Per-section timing metadata: *_latency_ms fields in DeviceInventoryResponse"
  - "Parallel counts via ThreadPoolExecutor when detail=all and counts needed"
  - "skip_count param plumbed through CLI, MCP tool, bridge, and workflow registry"
affects: ["phase 29 — replace all pynautobot count() with direct /count/ endpoint"]

# Tech tracking
tech-stack:
  added: [concurrent.futures.ThreadPoolExecutor, time.time()]
  patterns: [adaptive count strategy, has_more inference, per-section timing, parallel fan-out]

key-files:
  created: []
  modified:
    - nautobot_mcp/models/device.py
    - nautobot_mcp/devices.py
    - nautobot_mcp/cli/devices.py
    - nautobot_mcp/bridge.py
    - nautobot_mcp/server.py
    - nautobot_mcp/workflows.py

key-decisions:
  - "D-01: has_more = len(results) == limit when count skipped — exact limit means more exist"
  - "D-02: Null totals when count skipped — honest signal, agents check for null"
  - "D-03: skip_count added to CLI, workflow, bridge, MCP tool — unified across all interfaces"
  - "D-04: Per-section timing granularity — *_latency_ms per section + total_latency_ms wall-clock"
  - "D-05: Parallel counts for detail=all — ThreadPoolExecutor(max_workers=3) with sequential fallback"
  - "D-06: limit=0 implies skip_count — unlimited mode never fetches counts"

patterns-established:
  - "Adaptive count strategy: skip_count=True bypasses all count() calls; null totals signal this"
  - "has_more inference: len == limit → has_more=True; len < limit → has_more=False"
  - "Per-section timing: each section timed independently via time.time() around API calls"
  - "Parallel fan-out with fallback: ThreadPoolExecutor for 3 concurrent ops, sequential on failure"

requirements-completed: [PERF-01, PERF-02, OBS-01, UX-01, UX-02]

# Metrics
duration: 5min
completed: 2026-03-28
---

# Phase 28: Adaptive Count & Fast Pagination — Plan 01 Summary

**Adaptive count skipping with has_more inference, per-section timing, and parallel counts for detail=all**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-28T09:40:54Z
- **Completed:** 2026-03-28T09:45:00Z
- **Tasks:** 6/6
- **Files modified:** 6

## Accomplishments
- `get_device_inventory()` now skips all `count()` calls when `skip_count=True` or `limit==0` — O(1) vs O(n) for large devices
- `has_more` correctly inferred from `len(results) == limit` when counts are skipped
- Per-section timing fields (`interfaces_latency_ms`, `ips_latency_ms`, `vlans_latency_ms`, `total_latency_ms`) added to `DeviceInventoryResponse`
- `--no-count` CLI flag plumbed through to `get_device_inventory()`; `limit=0` auto-enables it
- Parallel counts via `ThreadPoolExecutor` when `detail=all` and counts ARE needed (with sequential fallback)
- `skip_count` accepted by `call_nautobot()` bridge and `nautobot_call_nautobot` MCP tool (Phase 29 wires it)
- `WORKFLOW_REGISTRY['devices_inventory']['param_map']` extended with `skip_count` for agent workflows

## Task Commits

Each task was committed atomically:

1. **Task 1: DeviceInventoryResponse model update** - `92cb90f` (feat/fix)
2. **Task 2: get_device_inventory rewrite** - `27ea778` (feat/fix)
3. **Task 3: CLI --no-count flag** - `c68e5ed` (feat/fix)
4. **Task 4: bridge.py skip_count param** - `78620b3` (feat/fix)
5. **Task 5: server.py MCP tool skip_count** - `498fe80` (feat/fix)
6. **Task 6: workflows.py param_map** - `c7206bd` (feat/fix)

**Plan metadata:** `28-01-PLAN.md` (docs: complete plan)

## Files Created/Modified

- `nautobot_mcp/models/device.py` — `total_*` fields changed to `Optional[int]`, added 4 timing fields
- `nautobot_mcp/devices.py` — complete `get_device_inventory()` rewrite with skip_count, timing, parallel counts
- `nautobot_mcp/cli/devices.py` — `--no-count` flag + null-safe text output
- `nautobot_mcp/bridge.py` — `skip_count` param added to `call_nautobot()` (stub, Phase 29 wires it)
- `nautobot_mcp/server.py` — `skip_count` param in `nautobot_call_nautobot` MCP tool
- `nautobot_mcp/workflows.py` — `skip_count` added to `devices_inventory` param_map

## Decisions Made

- D-01 through D-06 all applied exactly as specified in 28-CONTEXT.md
- No deviations from plan — all 6 tasks executed as written

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

Phase 29 (Replace count() with /count/ endpoint) is fully unblocked:
- `skip_count` param accepted at all layers (CLI, MCP, bridge, workflow)
- Phase 29 needs to wire `skip_count` through to `_execute_core()` and `_execute_cms()` in `bridge.py`
- Phase 29 should replace `client.api.dcim.interfaces.count(...)` with `client.api.dcim.interfaces.count(...)` hitting the `/count/` endpoint directly (pynautobot's `.count()` auto-paginates — the root cause)

---
*Phase: 28-adaptive-count-fast-pagination*
*Completed: 2026-03-28*
