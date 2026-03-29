# Phase 32: VLANs 500 Fix + Regression Tests - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix VLANs 500 by passing location UUID instead of name to `/count/`. Add structured warning field to response models. Add regression tests. Live verification against prod.

This phase covers: (1) resolving location name to UUID before calling `client.count("ipam", "vlans", location=...)`, (2) propagating 500 errors through the call chain with structured warnings, (3) CLI null display, (4) unit tests for count behavior and error path.

</domain>

<decisions>
## Implementation Decisions

### Location Resolution (VLAN-01 Override)

- **D-01:** Location name → UUID resolution happens at call sites in `devices.py`, not inside `client.count()`. Each of the 3 call sites resolves `device.location.name` → `device.location.id` before calling `count()`. Uses the UUID already available on the device object — no extra HTTP call needed.
- **D-02:** Call sites: `get_device_stats()` L255-256, `get_device_inventory()` L340-341 (single section), L351-360 and L381-382 (parallel and sequential fallback in `detail="all"`).

### 500 Error Behavior (VLAN-02 Override)

- **D-03:** `client.count()` propagates HTTP 500 as `NautobotAPIError` — does NOT catch 500 and return None. The original VLAN-02 requirement is overridden.
- **D-04:** Call sites in `devices.py` wrap `client.count("ipam", "vlans", location=...)` in try/except, catching `NautobotAPIError` and setting `total_vlans = None` when the call fails.

### Warning Field

- **D-05:** `DeviceStatsResponse` and `DeviceInventoryResponse` get a new optional `warnings: list[dict[str, str]] | None` field. When VLAN count fails, a warning dict is appended: `{"section": "vlans", "message": "VLAN count unavailable: <error detail>", "recoverable": True}`.
- **D-06:** The warning field pattern is consistent with `WarningCollector` used in composite workflows (`workflows.py` L223).

### CLI Null Display (VLAN-03)

- **D-07:** `vlan_count=None` appears as `null` in JSON output.
- **D-08:** In human-readable table output (CLI), `vlan_count=None` displays as `N/A`.

### Regression Tests (TEST-01)

- **D-09:** New test class `TestVLANCount500` in `tests/test_client.py` covering:
  - `count()` with `location=<uuid>` (valid UUID) succeeds and returns int
  - `count()` with `location=<uuid>` against VLAN endpoint returns 500 → propagates `NautobotAPIError`
- **D-10:** `tests/test_devices.py` (new file) covering:
  - `get_device_inventory()` catches VLAN count 500 error → sets `total_vlans=None`, appends warning
  - `get_device_stats()` same pattern
  - `vlan_count=None` serializes to `null` in JSON response
- **D-11:** All existing unit tests continue to pass (TEST-01: no regression).

### Boundary Notes

- Phase 30 (direct HTTP bulk fetch) and Phase 31 (bridge param guard) are already complete — both address 414 errors at different entry points. Phase 32 addresses the VLANs 500 error only.
- VLANs `/count/` does not use `__in` params — bridge param guard (Phase 31) does not apply here.
- `devices inventory` with `detail=vlans` may also call VLAN count — same fix applies.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §"VLANs 500 Mitigation (VLAN)" — VLAN-01, VLAN-02, VLAN-03, VLAN-04
- `.planning/REQUIREMENTS.md` §"Regression (TEST)" — TEST-01, TEST-02, TEST-03
- `.planning/REQUIREMENTS.md` §"Traceability" — VLAN-01..VLAN-04, TEST-01..TEST-03

### Source files
- `nautobot_mcp/client.py` — `count()` method L343-383 (propagates 500 as NautobotAPIError)
- `nautobot_mcp/devices.py` — `get_device_stats()` L254-256, `get_device_inventory()` L340-341 and L346-382 (VLAN count call sites)
- `nautobot_mcp/models/device.py` — `DeviceStatsResponse` (L73-79), `DeviceInventoryResponse` L83-121 (add `warnings` field here)
- `nautobot_mcp/cli/formatters.py` — Table formatting for device output (add `N/A` for None vlan_count)
- `tests/test_client.py` — Existing test patterns; add `TestVLANCount500` here
- `tests/conftest.py` — Test fixtures (mock_device_record already has `location.id` and `location.name`)

### Prior Phase Decisions
- `.planning/phases/30-direct-http-bulk-fetch/30-CONTEXT.md` — Phase 30 decisions, direct HTTP patterns
- `.planning/phases/31-bridge-param-guard/31-CONTEXT.md` — Phase 31 decisions, error propagation pattern
- `.planning/phases/29-direct-count-endpoint/29-CONTEXT.md` — `client.count()` pattern, direct `/count/` endpoint

### Workflow Patterns
- `nautobot_mcp/workflows.py` — `WarningCollector` usage (L223, L267) — pattern for structured warnings

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `device.location.id` — Already available on device object fetched in `get_device_stats()` and `get_device_inventory()`. No extra API call needed.
- `NautobotAPIError` — Already used throughout for API errors. Propagation pattern proven.
- `WarningCollector` dataclass in `workflows.py` — Pattern for `{"section", "message", "recoverable"}` warning dicts.

### Established Patterns
- Location resolution: device objects already carry `location.id` (UUID) and `location.name` (string)
- `count()` method already uses direct HTTP + `http_session.get` + `resp.json()["count"]` (L366-370)
- Error propagation: `_handle_api_error` translates HTTP errors into `NautobotAPIError` (L375)
- Response models use `Optional[int]` for nullable counts (already in device.py L101)

### Integration Points
- `get_device_stats()` calls `client.count()` at L248, L252, L256 — VLAN count is L256
- `get_device_inventory()` has 3 VLAN count call sites across different detail branches
- CLI formatter reads `vlan_count` from response dict (CLI L140: `data['vlan_count']`)
- No changes needed to workflows.py, server.py, or bridge.py

### Key Observations
- `device.location.id` is already a UUID string — can be passed directly to `client.count()` as `location=<uuid>`
- No extra HTTP call is needed to resolve the location UUID — it's already on the fetched device object
- `DeviceInventoryResponse.vlans_latency_ms` already exists — warning can be added alongside it
- Phase 31 tests (18 tests) use `TestParamGuard` and `TestParamGuardIntegration` patterns in test_bridge.py

</code_context>

<specifics>
## Specific Ideas

- Warning message format: `"VLAN count unavailable: HTTP 500"` or the parsed error message from `NautobotAPIError`
- Test device for TEST-02/03: HQV-PE1-NEW (700+ interfaces, likely 1000+ IPs) — already used for v1.6/v1.7 validation
- Consider adding `location_id` as a named parameter to `count()` calls for clarity, but UUID string works as-is

</specifics>

<deferred>
## Deferred Ideas

- `list_vlans()` device VLAN fetch using `client.api.ipam.vlans.filter(id__in=chunk)` — same 414 pattern as Phase 30 but different function. Not in Phase 32 scope — noted since Phase 30.
- VLAN-02 originally specified count() catching 500 and returning None — overridden by user decision to propagate 500.

---

*Phase: 32-vlans-500-fix-regression-tests*
*Context gathered: 2026-03-29*
