# Phase 32: VLANs 500 Fix + Regression Tests - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 32-vlans-500-fix-regression-tests
**Mode:** discuss
**Areas discussed:** Location Resolution, HTTP 500 Error Behavior, Warning Display, Regression Tests, CLI Null Handling

---

## Location Resolution

| Option | Description | Selected |
|--------|-------------|----------|
| At call sites in devices.py | Resolve device.location.name → device.location.id before count(). Preserves O(1). No extra HTTP. | ✓ |
| Inside client.count() (centralized) | client.count() auto-resolves location names. Cleaner callers. | |
| New client._resolve_location helper | Dedicated helper method. Single place to maintain. | |

**User's choice:** At call sites in devices.py
**Notes:** No extra HTTP call needed — `device.location.id` is already available on the device object.

---

## HTTP 500 Error Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Catch 500 in count() → return None | client.count() catches 500 specifically and returns None. Graceful degradation. | |
| Propagate 500 as NautobotAPIError | count() propagates 500. devices.py catches it and sets VLAN count to None. Fail loud. | ✓ |
| Retries then None fallback | count() retries 3x on 500, then returns None if persistent. | |

**User's choice:** Propagate 500 as NautobotAPIError
**Notes:** Overrides VLAN-02 requirement which specified catching 500 and returning None. User prefers fail-loud approach. Conflict resolved: user confirmed override.

---

## Warning Display

| Option | Description | Selected |
|--------|-------------|----------|
| CLI warning via Click (typer.echo yellow) | CLI echoes a yellow warning when VLAN count fails. Simple, visible. | |
| Warning field in response model (structured) | Add warnings field to DeviceStatsResponse/DeviceInventoryResponse. Rich warning propagated to MCP callers. | ✓ |
| Both CLI and response warning | Both CLI echo and structured warning field. Most visibility. Most effort. | |

**User's choice:** Structured warning field in response model
**Notes:** Warns both CLI and MCP callers. Consistent with WarningCollector pattern in workflows.py.

---

## Regression Tests

| Option | Description | Selected |
|--------|-------------|----------|
| Both count success path AND error-path tests | Test count() with UUID working AND count() propagating 500. Complete coverage. | ✓ |
| Count success path only | Only test that count() with UUID works. | |
| devices.py error handling only | Only test that devices.py catches count() error and sets None. | |

**User's choice:** Both count success path AND error-path tests
**Notes:** Test location: test_client.py (TestVLANCount500 class). Plus new test_devices.py for device-level error handling.

---

## CLI Null Handling

| Option | Description | Selected |
|--------|-------------|----------|
| null in JSON, "N/A" in table | JSON: null. Human table: 'N/A'. Consistent with other missing counts. | ✓ |
| null in both JSON and table | JSON: null. Human: null (literal text). | |
| 0 in table | JSON: null. Human table: 0. | |

**User's choice:** null in JSON, "N/A" in table
**Notes:** Consistent with how other unavailable data is displayed.

---

## Override Summary

| Requirement | Original | Override | Reason |
|-------------|----------|----------|--------|
| VLAN-02 | Catch 500 in count(), return None | Propagate 500 as NautobotAPIError | User prefers fail-loud: operation continues via catch in devices.py, but error is surfaced as warning |

---

## Claude's Discretion

- Exact warning message format ("VLAN count unavailable: <error>" vs. more structured format) — left to planner
- `warnings` field placement within the response model (before or after latency fields) — left to planner
- Exact test fixture setup for mocking 500 responses in test_client.py

## Deferred Ideas

- `list_vlans()` device VLAN fetch using `client.api.ipam.vlans.filter(id__in=chunk)` — same 414 pattern, different function. Phase 32 scope is VLANs 500 fix only.
