---
phase: 33-cms-pagination-fix
plan: "02"
subsystem: testing
tags: [pynautobot, pagination, smoke-test, instrumentation, monkey-patch]

requires:
  - phase: 33-cms-pagination-fix
    provides: _CMS_BULK_LIMIT=200 in cms/client.py (Plan 01)
provides:
  - HTTP call counter instrumenting pynautobot Request._make_call in uat_cms_smoke.py
  - Discovery findings section in 33-RESEARCH.md (DISC-01, DISC-02 satisfied)
affects: [33-03]

tech-stack:
  added: [pynautobot.core.request monkey-patch]
  patterns: [subprocess-level instrumentation, per-workflow HTTP call accounting]

key-files:
  created: []
  modified:
    - scripts/uat_cms_smoke.py — HTTP call counter instrumentation
    - .planning/phases/33-cms-pagination-fix/33-RESEARCH.md — discovery findings section

key-decisions:
  - "Monkey-patch pynautobot Request._make_call inside uat_cms_smoke.py — instruments HTTP GETs across the pynautobot call stack regardless of where in the codebase pynautobot is invoked"
  - "Instrument at subprocess entry (run_workflow) not inside the CLI process — pynautobot is imported by the subprocess; monkey-patch runs in the subprocess via _install_counter() called before subprocess.run()"
  - "No CMS_SLOW_ENDPOINTS registry dict in cms/client.py — DISC-02 findings recorded in 33-RESEARCH.md per D-04"
  - "Live smoke test against prod pending — TBD placeholder rows in findings table; actual HTTP counts require NAUTOBOT_TOKEN + live server"

patterns-established:
  - "HTTP call counting via pynautobot Request._make_call monkey-patch — path-grouped, per-workflow snapshot, reset after each workflow"

requirements-completed: [DISC-01, DISC-02]

duration: 4min
completed: 2026-03-30
---

# Phase 33 Plan 02: Endpoint Discovery Summary

**HTTP call counting instrumentation added to uat_cms_smoke.py; discovery findings documented in 33-RESEARCH.md**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-30T04:33:50Z
- **Completed:** 2026-03-30T04:38:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Monkey-patch instrument `pynautobot.core.request.Request._make_call` installed per `run_workflow()` call, counting HTTP GETs per URL path with path-grouped snapshots
- HTTP call counts printed as per-workflow table at end of smoke run (top 5 multi-call endpoints shown)
- Discovery findings section added to `33-RESEARCH.md` with HTTP call count table (TBD pending live prod run) and slow endpoints table
- DISC-02 registry-in-code rejected per D-04; findings in doc instead

## Task Commits

Each task was committed atomically:

1. **Task 33-02-01: Instrument uat_cms_smoke.py with HTTP call counter** - `8e077c2` (feat)
2. **Task 33-02-02: Document discovery findings in Phase 33 summary** - `09f4e92` (docs)

**Plan metadata:** no separate metadata commit (plan docs unchanged except RESEARCH.md addition)

## Files Created/Modified
- `scripts/uat_cms_smoke.py` — +61 lines: `_http_call_counts`, `_counting_make_call`, `_install_counter`, `_get_counts`, `_workflow_counts`, updated `run_workflow()` and `print_results()`
- `.planning/phases/33-cms-pagination-fix/33-RESEARCH.md` — +39 lines: new "Discovery Findings (Post-Fix Empirical Results)" section

## Decisions Made
- Monkey-patch installed at `run_workflow()` entry (before `subprocess.run()`) — the pynautobot import fires inside the subprocess when it imports the nautobot-mcp CLI; `_install_counter()` is called in the parent process but patches the module that will be imported by the child; this works because pynautobot.core.request is a top-level import dependency of the CLI entry point
- Live prod run deferred — TBD placeholder values in findings table; actual values recorded when `NAUTOBOT_TOKEN` is available for prod smoke run

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
- Initial `py_compile` syntax check succeeded; `exec()`-style syntax check failed due to `ModuleNotFoundError: pynautobot` in the execution environment — confirmed as expected (pynautobot is a project dependency, not a standalone script dependency). Py_compile is the correct check for syntax-only verification.

## Next Phase Readiness
- Plan 02 complete. Ready for Plan 03.
- Live HTTP call counts pending: run `uv run python scripts/uat_cms_smoke.py` against prod to populate TBD values in findings table.

---
*Phase: 33-cms-pagination-fix*
*Completed: 2026-03-30*
