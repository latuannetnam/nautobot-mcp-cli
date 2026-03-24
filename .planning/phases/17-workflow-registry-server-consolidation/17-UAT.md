---
status: complete
phase: 17-workflow-registry-server-consolidation
source: [17-01-SUMMARY.md, 17-02-SUMMARY.md]
started: 2026-03-24T21:05:21+07:00
updated: 2026-03-24T21:08:00+07:00
---

## Current Test

[testing complete]

## Tests

### 1. Registry Sync Guard
expected: WORKFLOW_REGISTRY has 10 entries, all keys match WORKFLOW_STUBS, all entries have function/required/param_map
result: pass

### 2. Server Exposes Exactly 3 Tools
expected: `mcp.list_tools()` returns exactly 3 tools: nautobot_api_catalog, nautobot_call_nautobot, nautobot_run_workflow — all with nautobot_ prefix
result: pass

### 3. Workflow Validation — Unknown Workflow
expected: `run_workflow(client, "bad_id", {})` raises NautobotValidationError with message listing available workflows
result: pass

### 4. Workflow Validation — Missing Required Params
expected: `run_workflow(client, "bgp_summary", {})` raises NautobotValidationError mentioning "missing required params"
result: pass

### 5. Workflow Dispatch with Param Mapping
expected: All 7 dispatch tests pass — bgp_summary, routing_table, firewall_summary, interface_detail, compare_bgp, compare_routes, verify_compliance
result: pass

### 6. ParsedConfig Transform
expected: onboard_config workflow transforms config_data dict into ParsedConfig.model_validate() call before dispatch
result: pass

### 7. Response Envelope Structure
expected: Envelope has {workflow, device, status, data, error, timestamp}. Error envelope has status=error and error message. device_name param fallback works.
result: pass

### 8. Full Test Suite — Zero Regressions
expected: `pytest --tb=short -q` passes 397 tests with 0 failures and 0 errors
result: pass

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
