---
phase: 17-workflow-registry-server-consolidation
plan: 2
subsystem: api
tags: [server, fastmcp, bridge, catalog, test]

requires:
  - phase: 17-01
    provides: workflows.py WORKFLOW_REGISTRY and run_workflow dispatch engine
  - phase: 16-rest-bridge
    provides: bridge.py call_nautobot() used in nautobot_call_nautobot tool
  - phase: 15-catalog-engine
    provides: catalog engine get_catalog() used in nautobot_api_catalog tool

provides:
  - server.py with 3-tool interface (nautobot_api_catalog, nautobot_call_nautobot, nautobot_run_workflow)
  - test_workflows.py with 26 tests (registry sync guard, dispatch, transforms, errors)
  - test_server.py rewritten with 20 tests for 3-tool interface

affects: [all tests importing server tools, CLI integration]

tech-stack:
  added: []
  patterns: [3-tool-mcp-server, workflow-func-mock-ctx-manager]

key-files:
  created: [tests/test_workflows.py]
  modified: [nautobot_mcp/server.py, tests/test_server.py]

key-decisions:
  - "workflow_func_mock context manager swaps WORKFLOW_REGISTRY[id]['function'] slot — module-level @patch fails because registry holds bound refs"
  - "server.py import chain: bridge.py, catalog.engine, workflows.py all import cleanly"
  - "handle_error() kept in server.py — not in workflows.py — consistent with Context.md decision"

patterns-established:
  - "workflow_func_mock(wf_id): context manager swapping registry function slot for mock testing"
  - "3-tool MCP pattern: catalog (discovery) + call (CRUD) + workflow (composite)"

requirements-completed: [SVR-01, SVR-02, SVR-03, SVR-04, TST-04, TST-05]

duration: 45min
completed: 2026-03-24
---

# Plan 17-02: Server Consolidation & Test Suites Summary

**server.py reduced from 3,883 lines/165 tools to ~170 lines/3 tools with 46 new tests covering registry, dispatch, and 3-tool interface**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-03-24T13:40:00Z
- **Completed:** 2026-03-24T14:25:00Z
- **Tasks:** 3 (server rewrite, test_workflows.py, test_server.py rewrite)
- **Files modified:** 3

## Accomplishments
- Rewrote `server.py` from 3,883 lines → ~170 lines, removing 165 individual tools
- 3 clean tool definitions delegating to `get_catalog()`, `call_nautobot()`, `run_workflow()`
- Created `test_workflows.py` with 26 tests (registry sync guard, dispatch, transforms, error envelope, serialization)
- Rewrote `test_server.py` with 20 tests for 3-tool interface (registration, singleton, delegation, error handling)
- Full test suite: **397/397 passing, 0 regressions**

## Task Commits

1. **Task 1-3: Server rewrite + test suites** - `9fb87c0` (feat)

## Files Created/Modified
- `nautobot_mcp/server.py` — Rewritten: 3 tools, 170 lines (was 3,883 lines/165 tools)
- `tests/test_workflows.py` — New: 26 tests, `workflow_func_mock` context manager pattern
- `tests/test_server.py` — Rewritten: 20 tests for 3-tool interface

## Decisions Made
- `workflow_func_mock` context manager: module-level `@patch` fails for registry-bound functions; must swap the registry slot directly. Documented as pattern for future registry tests.

## Deviations from Plan
- Initial test implementation used `@patch("nautobot_mcp.workflows.func_name")` — failed because registry holds bound refs at import time. Auto-fixed by implementing `workflow_func_mock` context manager.

## Issues Encountered
- Registry function binding + mock interaction required a non-obvious solution. Resolved cleanly with the context manager approach.

## Next Phase Readiness
- Phase 17 fully complete: both plans done, 397 tests passing
- `server.py` is the new canonical MCP entry point
- `workflows.py` and `bridge.py` are ready for integration testing against live Nautobot instance

---
*Phase: 17-workflow-registry-server-consolidation*
*Completed: 2026-03-24*
