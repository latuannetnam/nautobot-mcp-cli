---
phase: 17-workflow-registry-server-consolidation
plan: 1
subsystem: api
tags: [workflows, registry, dispatch, pydantic, cms, drift]

requires:
  - phase: 15-catalog-engine
    provides: workflow_stubs.py with agent-facing metadata
  - phase: 16-rest-bridge
    provides: bridge.py REST dispatcher pattern for reference

provides:
  - 10-entry WORKFLOW_REGISTRY mapping workflow IDs to domain functions
  - run_workflow() dispatch engine with param validation and response envelope
  - Updated workflow_stubs.py with corrected parameter names/types

affects: [17-02, test_workflows.py, test_server.py]

tech-stack:
  added: []
  patterns: [workflow-registry, response-envelope, param-transform]

key-files:
  created: [nautobot_mcp/workflows.py]
  modified: [nautobot_mcp/catalog/workflow_stubs.py]

key-decisions:
  - "Use get_device_routing_table (not get_routing_table) — actual function name in cms/routing.py"
  - "verify_data_model exposed with device_name only; parsed_config optional via param_map"
  - "config_data transform: lambda d: ParsedConfig.model_validate(d) in registry"
  - "Separate WORKFLOW_REGISTRY (importable) from WORKFLOW_STUBS (zero-import metadata)"

patterns-established:
  - "Registry entry: {function, param_map, required, transforms(optional)}"
  - "Envelope: {workflow, device, status, data, error, timestamp}"
  - "_serialize_result: Pydantic -> model_dump, dataclass -> asdict, dict -> passthrough, else -> str"

requirements-completed: [WFL-01, WFL-02, WFL-03, WFL-04, WFL-05, WFL-06]

duration: 30min
completed: 2026-03-24
---

# Plan 17-01: Workflow Registry & Dispatch Engine Summary

**10-entry WORKFLOW_REGISTRY with run_workflow() dispatch, param validation, transforms, and standard response envelope wrapping all 10 composite domain functions**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-03-24T13:10:00Z
- **Completed:** 2026-03-24T13:40:00Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- Updated `workflow_stubs.py` with 6 param corrections (config_json→config_data, device→device_name in compare_bgp/compare_routes, added detail/include_arp, fixed routing_table param)
- Created `workflows.py` with 10-entry WORKFLOW_REGISTRY mapping all composite domain functions
- Implemented `run_workflow()` with required-param validation, param_map routing, ParsedConfig transform, and standard envelope
- Verified `routing_table` correctly references `get_device_routing_table` (not `get_routing_table`)
- 23 catalog tests passing, module imports cleanly

## Task Commits

1. **Task 1: Update workflow_stubs.py** - `769fdae` (feat)
2. **Tasks 2-3: Create workflows.py** - `4be0288` (feat)

## Files Created/Modified
- `nautobot_mcp/workflows.py` — Workflow registry + dispatch engine (235 lines)
- `nautobot_mcp/catalog/workflow_stubs.py` — Updated param names/types

## Decisions Made
- `routing_table` uses `get_device_routing_table` with `detail: bool` (matches actual composite function)
- `verify_data_model` exposes `device_name` only in public param_map; `parsed_config` optional

## Deviations from Plan
None — plan executed exactly as written. `get_routing_table` turned out to be `get_device_routing_table` (Task 3 check handled this).

## Issues Encountered
None

## Next Phase Readiness
- Wave 2 (Plan 17-02) can proceed: `workflows.py` provides `run_workflow` for import into new `server.py`
- `WORKFLOW_REGISTRY` has 10 entries matching `WORKFLOW_STUBS` keys (sync guard will be checked in test_workflows.py)

---
*Phase: 17-workflow-registry-server-consolidation*
*Completed: 2026-03-24*
