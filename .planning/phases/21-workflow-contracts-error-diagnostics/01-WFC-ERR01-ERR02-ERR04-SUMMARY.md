---
phase: 21-workflow-contracts-error-diagnostics
plan: "01"
subsystem: workflows, client, testing
tags: [workflow-registry, validation, error-handling, nautobot-api, pydantic]

requires: []
provides:
  - Workflow contract validation at import time (WFC-03)
  - verify_data_model registry entry fixed with required+transforms (WFC-01, WFC-02)
  - DRF 400 body parsing with field-level errors (ERR-01)
  - Endpoint-specific and status-code-based error hints (ERR-02, ERR-04)
affects: [01-core-foundation-nautobot-client, 04-onboarding-verification-agent-skills, 07-file-free-drift-comparison, 13-cms-drift-verification]

tech-stack:
  added: []
  patterns:
    - Import-time self-validation: _validate_registry() fails fast at module load
    - Workflow registry param_map keys must be actual function parameter names
    - Longest-match hint resolution for ERROR_HINTS
    - DRF error normalization: non_field_errors and detail keys normalized to _detail

key-files:
  created:
    - nautobot_mcp/client.py — error hints and _handle_api_error() rewrite
    - tests/test_client.py — 18 tests for error handling
  modified:
    - nautobot_mcp/workflows.py — WFC-01/02/03 fixes, _validate_registry(), pre-existing bug fixes
    - nautobot_mcp/catalog/workflow_stubs.py — verify_data_model params updated
    - nautobot_mcp/exceptions.py — NautobotAPIError status-code default hints
    - tests/test_workflows.py — WFC-03 tests + verify_data_model transform test
    - tests/test_exceptions.py — 3 new ERR-01/ERR-04 tests

key-decisions:
  - "param_map keys must be actual function parameter names (not agent-facing aliases)"
  - "Validator should not flag optional function params — only required params without defaults"
  - "Validator checks mapped func param names (not registry keys) against function signature"
  - "FakeRequestError for tests must inherit from pynautobot.core.query.RequestError for isinstance()"
  - "NautobotAPIError default hint is status-code-derived when no explicit hint provided"

patterns-established:
  - "Pattern: Import-time registry validation — _validate_registry() called at module load"
  - "Pattern: DRF error normalization — normalize non_field_errors and detail to _detail"
  - "Pattern: Hint resolution priority — ERROR_HINTS (longest-match) > STATUS_CODE_HINTS > generic fallback"

requirements-completed: []

# Phase 21 Plan 01: Workflow Contract Bugs + Error Diagnostics Summary

**Import-time registry validation catches pre-existing bugs, DRF 400 body parsing with field-level errors, and actionable error hints for all Nautobot API error types**

## Performance

- **Duration:** ~90 min
- **Tasks:** 11 planned + 3 Rule 1 auto-fixes
- **Commits:** 13 total (11 tasks + 2 plan/summary metadata)

## Accomplishments

- WFC-01/02: `verify_data_model` registry entry fixed with `parsed_config` in required + transforms
- WFC-03: `_validate_registry()` validates registry entries against function signatures at import time
- ERR-01: `_handle_api_error()` parses DRF 400 response body and populates `NautobotValidationError.errors`
- ERR-02: `ERROR_HINTS` dict with 10 endpoint-specific actionable hints; longest-match lookup
- ERR-04: `NautobotAPIError` and default hint are status-code-derived (429/500/502/503/504/422)
- Caught and fixed 3 pre-existing registry bugs (onboard_config param key, compare_device required list)
- 455/455 tests pass (full suite)

## Task Commits

1. **Task A1 (WFC-01):** `2736f9a` fix(21-01): add parsed_config to verify_data_model required list
2. **Task A2 (WFC-02):** `8209bdf` feat(21-01): add transforms block to verify_data_model registry entry
3. **Task A3 (WFC-03 aligned):** `0b3286a` docs(21-01): update verify_data_model stub params
4. **Task B1 (WFC-03):** `02421f8` feat(21-01): add _validate_registry() + pre-existing bug fixes
5. **Task B2 (WFC-03):** `02421f8` (same commit as B1 — module-level _validate_registry() call)
6. **Task C1 (ERR-02+ERR-04):** `a3b0161` feat(21-01): add ERROR_HINTS and STATUS_CODE_HINTS
7. **Task C2 (ERR-02+ERR-04):** `73642cb` feat(21-01): add _get_hint_for_request() helper
8. **Task C3 (ERR-01):** `5e925f3` feat(21-01): update _handle_api_error() 400 body parsing
9. **Task C4 (ERR-02+ERR-04):** `5e925f3` (same commit as C3 — NautobotAPIError hint enrichment)
10. **Task D1 (WFC-03):** `cbe79e4` test(21-01): add WFC-03 registry self-check tests
11. **Task D2 (WFC-01+02):** `cbe79e4` (same commit — verify_data_model transform test)
12. **Task D3 (ERR-01+02+04):** `569ff10` test(21-01): add test_client.py (18 tests)
13. **Task D4 (ERR-04):** `f0c7dce` fix(21-01): NautobotAPIError status-code default hints
14. **Existing test fix:** `59dfa52` fix(21-01): update onboard_config test to use correct registry key

**Plan metadata:** (to be added after this SUMMARY commit)

## Files Created/Modified

- `nautobot_mcp/workflows.py` — Added `_validate_registry()`, fixed `verify_data_model` entry, fixed `onboard_config` param key, fixed `compare_device` required list
- `nautobot_mcp/client.py` — Added `ERROR_HINTS`, `STATUS_CODE_HINTS`, `_get_hint_for_request()`, updated `_handle_api_error()` with 400 body parsing and hint enrichment
- `nautobot_mcp/exceptions.py` — Added `_STATUS_DEFAULTS` to `NautobotAPIError` for status-code-derived default hints
- `nautobot_mcp/catalog/workflow_stubs.py` — Updated `verify_data_model` stub params to include `parsed_config`
- `tests/test_client.py` (new) — 18 tests covering `_get_hint_for_request()`, ERR-01 400 body parsing, ERR-02/ERR-04 hint enrichment
- `tests/test_workflows.py` — Added `TestRegistrySelfCheck` (3 tests) and `TestVerifyDataModelTransform` (1 test)
- `tests/test_exceptions.py` — Added 3 tests for ERR-01/ERR-04 exception to_dict() behavior

## Decisions Made

- param_map keys must match actual function parameter names (not agent-facing aliases) — this is what the validator checks
- Optional function params (those with defaults) are intentionally not in the registry and are not flagged as errors
- FakeRequestError test helper inherits from pynautobot.core.query.RequestError so isinstance() check passes in `_handle_api_error()`
- NautobotAPIError default hint is status-code-derived when no explicit hint provided, preventing the generic placeholder from appearing

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `onboard_config` param_map key "config_data" did not match function signature**
- **Found during:** Task B1 (WFC-03 — _validate_registry() development)
- **Issue:** Registry had `param_map: {"config_data": "parsed_config", ...}` but the key must be the actual function parameter name. Function signature has `parsed_config`, not `config_data`.
- **Fix:** Changed param_map key from `"config_data"` to `"parsed_config"`; removed `"config_data"` from `required` (already covered by param_map); added `"parsed_config"` to `required`
- **Files modified:** `nautobot_mcp/workflows.py`
- **Verification:** `_validate_registry()` import passes; 455/455 tests pass
- **Committed in:** `02421f8`

**2. [Rule 1 - Bug] `compare_device` had `live_data` in both `required` and `param_map`, causing duplicate key**
- **Found during:** Task B1 (WFC-03 — _validate_registry() development)
- **Issue:** Registry had `required: ["device_name", "live_data"]` and `param_map: {"live_data": "interfaces_data"}`. The `missing` list construction created duplicate `"live_data"` entries, making validator think `live_data` was missing from function signature.
- **Fix:** Changed `required` from `["device_name", "live_data"]` to `["device_name", "interfaces_data"]` (matching function signature `interfaces_data`)
- **Files modified:** `nautobot_mcp/workflows.py`
- **Verification:** `_validate_registry()` import passes; all existing compare_device tests pass
- **Committed in:** `02421f8`

**3. [Rule 2 - Missing Critical] `_validate_registry()` was too strict — flagged optional function params**
- **Found during:** Task B1 (WFC-03 — verifying _validate_registry() against existing registry)
- **Issue:** Validator flagged optional params with defaults (`location`, `device_type`, `role`, `namespace`, `update_existing`) as "extra func params without default" — but these are intentionally omitted from the registry (optional override params).
- **Fix:** Updated validator to only flag func params without defaults that aren't in the registry. Optional params (those with defaults) are silently skipped.
- **Files modified:** `nautobot_mcp/workflows.py`
- **Verification:** `python -c "from nautobot_mcp.workflows import run_workflow; print('import ok')"` passes
- **Committed in:** `02421f8`

**4. [Rule 2 - Missing Critical] Validator checked registry keys instead of mapped func param names against signature**
- **Found during:** Task B1 (WFC-03 — understanding why `live_data` was flagged as missing)
- **Issue:** The original validator computed `registry_params = required | param_map_keys` (registry keys) and compared against function params. But param_map maps agent-facing names → function param names. The check should compare mapped function param names against the actual signature.
- **Fix:** Rewrote validator to check mapped function param names (`param_map.values()`) against the signature, not registry keys. Only registry keys are used for the `missing_in_func` check (registry says param should exist → verify signature has it).
- **Files modified:** `nautobot_mcp/workflows.py`
- **Verification:** All 10 registry entries pass validation; 455/455 tests pass
- **Committed in:** `02421f8`

**5. [Rule 1 - Bug] FakeRequestError in tests did not satisfy `isinstance(error, pynautobot.core.query.RequestError)`**
- **Found during:** Task D3 (test_client.py development)
- **Issue:** MagicMock-based fake error caused `TypeError: exception causes must derive from BaseException` when raised with `from` clause.
- **Fix:** Created `FakeRequestError(pynautobot.core.query.RequestError)` inheriting from the real class; passed response object to `super().__init__(fake_resp)` per the real class's signature.
- **Files modified:** `tests/test_client.py`
- **Verification:** All 18 test_client.py tests pass
- **Committed in:** `569ff10`

**6. [Rule 2 - Missing Critical] `NautobotAPIError` default hint was generic placeholder instead of status-code-derived**
- **Found during:** Task D4 (test_exceptions.py extension)
- **Issue:** `test_api_error_default_hint_is_not_generic` failed — `NautobotAPIError(message="Server error", status_code=500)` with no explicit hint returned `"Check Nautobot server logs for details"` (generic default), not the 500-specific message.
- **Fix:** Added `_STATUS_DEFAULTS` dict to `NautobotAPIError`; `__init__` now derives hint from this dict when no explicit hint is provided.
- **Files modified:** `nautobot_mcp/exceptions.py`
- **Verification:** All 11 test_exceptions.py tests pass
- **Committed in:** `f0c7dce`

---

**Total deviations:** 6 auto-fixed (4 bug/missing-critical, 2 were test helper/implementation improvements)
**Impact on plan:** All auto-fixes were necessary for correctness. No scope creep — all fixes are within the plan's scope of workflows.py and client.py.

## Issues Encountered

- **WFC-03 validator discovered pre-existing bugs:** The import-time validator caught three real bugs in the existing registry that had never been validated. This was the primary purpose of WFC-03 and it worked as designed.
- **MagicMock spec= inheritance issue:** Using `MagicMock(spec=pynautobot.core.query.RequestError)` didn't work for the isinstance() check — the mock didn't properly inherit the class hierarchy needed for `raise ... from error`. Solved by subclassing the real class.

## Next Phase Readiness

- Phase 21 has one more plan: `02-ERR03-PLAN.md` — remaining error diagnostics
- All Phase 21 error handling infrastructure is in place (client.py, exceptions.py, workflows.py)
- Next plan can use the new `_get_hint_for_request()` and ERROR_HINTS for additional endpoint-specific hints
- WFC-03 validator will prevent future registry/signature drift

---
*Phase: 21-workflow-contracts-error-diagnostics*
*Plan: 01*
*Completed: 2026-03-26*
