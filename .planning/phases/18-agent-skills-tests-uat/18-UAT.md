---
status: complete
phase: 18-agent-skills-tests-uat
source:
  - .planning/phases/18-agent-skills-tests-uat/18-01-SUMMARY.md
  - .planning/phases/18-agent-skills-tests-uat/18-02-SUMMARY.md
started: 2026-03-25T07:48:00+07:00
updated: 2026-03-25T07:56:00+07:00
---

## Current Test

[testing complete]

## Tests

### 1. cms-device-audit skill — discovery step
expected: Step 0 calls nautobot_api_catalog(domain="cms"). No legacy tool names remain.
result: pass

### 2. cms-device-audit skill — workflow calls
expected: BGP comparison uses nautobot_run_workflow(workflow_id="compare_bgp"), route comparison uses nautobot_run_workflow(workflow_id="compare_routes"), interface detail uses nautobot_run_workflow(workflow_id="interface_detail"), firewall uses nautobot_run_workflow(workflow_id="firewall_summary").
result: pass

### 3. onboard-router-config skill — workflow calls
expected: Onboarding step calls nautobot_run_workflow(workflow_id="onboard_config", params={"config_data": ..., "device_name": ...}), verification step calls nautobot_run_workflow(workflow_id="verify_data_model", ...). Parameter name is config_data (not config_json).
result: pass

### 4. verify-compliance skill — workflow calls
expected: Compliance check uses nautobot_run_workflow(workflow_id="verify_compliance"), data model check uses nautobot_run_workflow(workflow_id="verify_data_model"), interface drift uses nautobot_run_workflow(workflow_id="compare_device"). No old nautobot_verify_* or nautobot_compare_* tool names.
result: pass

### 5. UAT test suite — normal pytest run excludes live tests
expected: Running `python -m pytest tests/ -q` shows "11 deselected". test_uat.py tests do not run without -m live flag.
result: pass
note: Verified — 397 passed, 11 deselected (addopts = "-m 'not live'" in pyproject.toml)

### 6. UAT test suite — live tests pass against dev server
expected: Running `python -m pytest tests/test_uat.py -m live -v` with NAUTOBOT_TOKEN set shows "11 passed" against http://101.96.85.93.
result: pass
note: 11 passed in 156.57s — TestCatalogUAT (3), TestBridgeUAT (3), TestWorkflowUAT (4), TestIdempotentWriteUAT (1)

### 7. Smoke script — runs and passes
expected: Running `python scripts/uat_smoke_test.py` prints [PASS] for each of the 9 checks and exits with code 0.
result: pass
note: 9 passed, 0 failed — also fixed Windows CP1252 UnicodeEncodeError (replaced ✓/✗ with [PASS]/[FAIL])

### 8. README and CHANGELOG accuracy
expected: README describes exactly 3 MCP tools, no legacy tool listings, no (v1.2) tags. CHANGELOG has [v1.3] with API Bridge release notes.
result: pass

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
