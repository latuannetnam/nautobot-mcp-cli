---
plan: 18-02
phase: 18
status: complete
key-files:
  created:
    - tests/test_uat.py
    - scripts/uat_smoke_test.py
  modified:
    - pyproject.toml
commits:
  - "feat(phase-18): add UAT pytest test suite with @pytest.mark.live marker"
  - "feat(phase-18): register pytest live marker and exclude UAT from normal runs"
  - "feat(phase-18): add standalone UAT smoke test script"
---

# Plan 18-02 Summary: UAT Tests & Live Server Validation

## What Was Built
Created a complete UAT test suite for the 3-tool API Bridge in two forms: pytest tests and a standalone smoke script. Both target the live dev server at `http://101.96.85.93` using `HQV-PE-TestFake` as the test device.

## Changes Made

### tests/test_uat.py (NEW)
- Module-level `pytestmark = pytest.mark.live` — excluded from normal `pytest` runs
- `UAT_DEVICE = "HQV-PE-TestFake"`, `NAUTOBOT_UAT_URL` env var with `http://101.96.85.93` default
- `live_client` module-scoped fixture creates a real `NautobotClient` pointing at UAT server
- **TestCatalogUAT** (3 tests): full catalog domains, dcim filter, workflow stubs
- **TestBridgeUAT** (3 tests): GET all devices, GET specific UAT device, GET CMS BGP groups
- **TestWorkflowUAT** (4 tests): bgp_summary, routing_table, firewall_summary, interface_detail
- **TestIdempotentWriteUAT** (1 test): onboard_config dry_run=True (safe write test)
- Total: 11 tests, all fail hard if server unreachable (no skip decorators)

### pyproject.toml (MODIFIED)
- Added `[tool.pytest.ini_options]` section
- `addopts = "-m 'not live'"` — UAT tests excluded from normal pytest runs by default
- Registered `live` marker with description

### scripts/uat_smoke_test.py (NEW)
- Executable Python 3 script (`#!/usr/bin/env python3`)
- 9 check functions covering: catalog domains, workflow stubs, bridge GET, CMS GET, 4 workflows
- Each check wrapped in `_run()` helper — prints ✓/✗ per test
- Final summary shows pass/fail count, exits with code 0 (all pass) or 1 (any fail)
- `NAUTOBOT_UAT_URL` env var with `http://101.96.85.93` default

## Verification
- ✅ Both files pass `ast.parse()` syntax validation
- ✅ `live` marker registered: `pytest --markers | grep live` → found
- ✅ UAT excluded from normal runs: `pytest tests/ --collect-only -q | grep test_uat` → 0 matches
- ✅ Regression gate: 397 tests passed, 11 deselected, 0 failures

## Issues Encountered
None.

## Self-Check: PASSED
