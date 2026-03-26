---
status: complete
phase: 20-catalog-accuracy-endpoint-dereference
source: 20-01-SUMMARY.md, 20-02-SUMMARY.md
started: 2026-03-26T00:00:00Z
updated: 2026-03-26T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Endpoint Catalog Shows Correct Filters Per-Endpoint
expected: Running `call_nautobot("/api/dcim/devices/")` with the catalog response shows
each endpoint's primary FK filter(s) correctly. For example:
  - juniper_bgp_neighbors -> filter: ["group"]
  - juniper_firewall_terms -> filter: ["firewall_filter"]
  - Interface on a device -> filter: ["device"]
Previously domain-level filters applied to all endpoints; now each endpoint
advertises only its relevant filter(s).
result: pass

### 2. UUID in Device URL Path
expected: Passing a URL with a device UUID like `/api/dcim/devices/abc12300-0000-0000-0000-000000000000/` to `call_nautobot()` succeeds -- the UUID is stripped and the call is made to `/api/dcim/devices/` with `id` parameter set. The response contains the correct device data.
result: pass

### 3. Nested UUID Path Raises Clear Error
expected: Passing a path with nested UUIDs like `/api/dcim/devices/<uuid1>/config-contexts/<uuid2>/` raises `NautobotValidationError` with message containing "Nested UUID paths not supported" or similar. Does not silently return wrong data.
result: pass

### 4. Catalog Filter Registry Covers All CMS Endpoints
expected: The CMS filter registry (CMS_ENDPOINT_FILTERS) has entries for all CMS endpoints. Querying the catalog for a CMS endpoint returns its correct filter key(s). No CMS endpoints are missing from the registry.
result: pass

### 5. Cold Start Smoke Test
expected: Kill any running server/service. Clear ephemeral state. Start the application from scratch. Server boots without errors, all tests pass, and catalog discovery initializes correctly.
result: pass

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
