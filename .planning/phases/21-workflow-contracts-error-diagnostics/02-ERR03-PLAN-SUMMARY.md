---
phase: 21-workflow-contracts-error-diagnostics
plan: 02
subsystem: api
tags: [workflows, error-handling, envelopes, mcp]

# Dependency graph
requires:
  - phase: 21-plan-01-WFC-ERR01-ERR02-ERR04
    provides: >
      WFC-01/WFC-02/WFC-03 fixes in workflows.py (run_workflow registry
      self-check, verify_data_model required+transform), ERR-01/ERR-02
      fixes in client.py and exceptions.py
provides:
  - ERR-03 implemented in run_workflow() except block
  - 7 new tests in TestRunWorkflowCompositeErrorOrigin
affects:
  - Phase 22 (Response Ergonomics & UAT)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Exception-as-warning envelope pattern: when a composite workflow raises,
      capture the exception in the warnings list (with operation+error keys)
      while preserving status=error and data=None

key-files:
  created: []
  modified:
    - nautobot_mcp/workflows.py
    - tests/test_workflows.py

key-decisions:
  - "ERR-03 uses same {operation, error} dict shape as Phase 19 WarningCollector"
  - "Preserved error field for backward compatibility — exception appears in both
     the 'error' string and as a structured warning dict"
  - "Phase 19 partial-failure (tuple return) path is untouched — ERR-03 only
     modifies the except Exception handler"

patterns-established:
  - "Exception → warning envelope: run_workflow() catch block builds exception_warning
     dict and passes it as warnings=[exception_warning] to _build_envelope()"

requirements-completed: [ERR-03]

# Metrics
duration: ~5min
completed: 2026-03-26
---

# Phase 21: Workflow Contracts & Error Diagnostics — Plan 02 (ERR-03) Summary

**Composite workflow exceptions now surface as structured warning entries in the error envelope, enabling agents to identify which top-level workflow failed.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-26
- **Completed:** 2026-03-26
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `run_workflow()` exception handler updated to capture exception as `{"operation": workflow_id, "error": str(e)}` in the `warnings` list while preserving `status: "error"` and `data: None`
- 7 new tests covering all 5 composite workflows (bgp_summary, routing_table, firewall_summary, interface_detail, verify_data_model) plus backward-compat and Phase 19 preservation assertions
- All 48 workflow tests pass (41 pre-existing + 7 new)

## Task Commits

Each task committed atomically:

1. **Task E1: Add composite workflow exception → warning conversion (ERR-03)** - `e590454` (fix)
2. **Task E2: Add tests for ERR-03 (composite workflow exception → warning in envelope)** - `4059bc1` (test)

## Files Created/Modified

- `nautobot_mcp/workflows.py` - Replaced bare `return _build_envelope(workflow_id, params, error=e)` with structured `exception_warning` dict + `warnings=[exception_warning]`; preserves `error=e` for backward compat
- `tests/test_workflows.py` - Added `TestRunWorkflowCompositeErrorOrigin` class (7 tests, 154 lines)

## Decisions Made

- Used the same `{"operation", "error"}` dict shape as `WarningCollector.add()` from Phase 19 — consistent envelope format across both error types
- Passed `error=e` to `_build_envelope()` alongside `warnings=[exception_warning]` — `error` field retains exception string for backward compatibility with any code parsing it directly
- `status: "error"` is preserved (data is None) — ERR-03 adds provenance information, not a status change

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- ERR-03 complete. Phase 22 (Response Ergonomics & UAT) can proceed with full confidence that all Phase 21 workflow contracts and error diagnostics are in place.
- No blockers.

---
*Phase: 21-workflow-contracts-error-diagnostics (plan 02)*
*Completed: 2026-03-26*
