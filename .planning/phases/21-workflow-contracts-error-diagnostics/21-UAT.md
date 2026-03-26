---
status: complete
phase: 21-workflow-contracts-error-diagnostics
source: 01-WFC-ERR01-ERR02-ERR04-SUMMARY.md, 02-ERR03-PLAN-SUMMARY.md
started: 2026-03-26T00:00:00Z
updated: 2026-03-26T11:35:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Import-time registry validation catches drift
expected: |
  When a workflow registry entry has a param_map key that doesn't match the function's actual
  parameter name, or a required param missing from the function signature, the module raises
  NautobotValidationError at import time — before any workflow runs.
result: pass

### 2. DRF 400 errors surface as structured field errors
expected: |
  When Nautobot returns a 400 response with a JSON body like:
    {"name": ["This field is required."], "device": ["Invalid pk \"xxx\"."]}
  The raised NautobotValidationError has an `errors` attribute containing:
    [{"field": "name", "error": "This field is required."},
     {"field": "device", "error": "Invalid pk \"xxx\"."}]
result: pass

### 3. 400 with detail/non_field_errors normalizes to _detail
expected: |
  When Nautobot returns {"detail": "Object not found."} or
  {"non_field_errors": ["Invalid input."]}, the field is "_detail" not "detail" or
  "non_field_errors" — uniform shape regardless of DRF serializer error key.
result: pass

### 4. 500/429 errors include actionable HTTP-status hints
expected: |
  When Nautobot returns HTTP 500, NautobotAPIError.hint is:
    "Nautobot server error — check Nautobot service health and application logs"
  When it returns HTTP 429, hint is:
    "Rate limited — retry after exponential backoff or check Nautobot task schedule"
result: pass

### 5. Endpoint-specific hints guide correct filter usage
expected: |
  When a request to /api/dcim/devices/ fails with 400, the hint is:
    "Device filter accepts 'name', 'slug', or 'id' (UUID). ..."
  When /api/dcim/interfaces/ fails, the hint explains that 'device' requires a UUID.
result: pass

### 6. verify_data_model transforms parsed_config dict to ParsedConfig
expected: |
  Calling run_workflow(client, "verify_data_model", params={
    "device_name": "rtr-01",
    "parsed_config": {"hostname": "rtr-01", "platform": "junos", "interfaces": [],
                      "ip_addresses": [], "vlans": [], "routing_instances": [],
                      "protocols": [], "firewall_filters": []}
  }) works — the dict is transformed to a ParsedConfig instance before being
  passed to the underlying function.
result: pass

### 7. Composite workflow exception includes operation name in warnings
expected: |
  When a composite workflow (e.g. bgp_summary) raises an exception, the error envelope has:
    status: "error", data: null, error: "<string>",
    warnings: [{"operation": "bgp_summary", "error": "<string>"}]
result: pass

### 8. Composite workflow partial failure preserves status=partial (Phase 19)
expected: |
  When a composite workflow returns a partial result (enrichment fails, primary succeeds),
  the envelope has status: "partial" with data and warnings. Phase 19 behavior unchanged.
result: pass

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none]
