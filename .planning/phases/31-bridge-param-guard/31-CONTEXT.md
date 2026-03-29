# Phase 31: Bridge Param Guard - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Add `_guard_filter_params()` in `bridge.py` to intercept oversized `__in` list values in `params` before they reach `.filter()`. Guards both `_execute_core()` and `_execute_cms()`. Prevents 414 Request-URI Too Large errors from external callers who supply large `__in` lists through the bridge.

</domain>

<decisions>
## Implementation Decisions

### Error Behavior

- **D-01:** `NautobotValidationError` is raised when any `__in`-suffixed param value has > 500 items. Fast-fail — caller must fix their query. Consistent with bridge's existing error model.

### Comma-Separation Strategy

- **D-02:** ALL `__in`-suffixed param values ≤ 500 items are converted to comma-separated strings before passing to `.filter()`. DRF-native format: `?id__in=uuid1,uuid2,uuid3` replaces repeated query params. This also eliminates 414 risk for mid-size lists (100-500 UUIDs).

### Guard Scope

- **D-03:** The guard targets ALL `__in`-suffixed keys generically — `id__in`, `interface__in`, `device__in`, `vlan__in`, and any future `__in` patterns. Not limited to specific known keys. Future-proof.

### Non-`__in` List Params

- **D-04:** Non-`__in` list params (e.g., `tag=[foo, bar]`, `status=[active, planned]`) pass through unchanged. These are typically small (1-5 items) and not 414 sources.

### Implementation Location

- **D-05:** `_guard_filter_params()` is a standalone helper function at module level in `bridge.py`, called inside both `_execute_core()` and `_execute_cms()` before the `.filter()` call.

### Boundary Notes

- Direct HTTP bulk fetch (Phase 30) is the SOURCE fix for `ipam.py get_device_ips()`. Bridge Param Guard is the GATEKEEPER for external callers through the MCP bridge. Both are needed — they address different 414 entry points.
- The initial interface fetch (`client.api.dcim.interfaces.filter(device=device_name)`) is OUT of scope — not a 414 source.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §"Bridge Param Guard (BRIDGE)" — BRIDGE-01, BRIDGE-02, BRIDGE-03, BRIDGE-04, BRIDGE-05
- `.planning/REQUIREMENTS.md` §"Regression (TEST)" — TEST-01, TEST-02, TEST-03

### Source files
- `nautobot_mcp/bridge.py` — `_execute_core()` (L149-235), `_execute_cms()` (L237-321), `NautobotValidationError` usage patterns
- `nautobot_mcp/exceptions.py` — `NautobotValidationError` definition
- `tests/test_bridge.py` — Existing test structure (586 lines), test patterns for error raising

### Prior Phase Decisions
- `.planning/phases/30-direct-http-bulk-fetch/30-CONTEXT.md` — Phase 30 decisions on direct HTTP + comma-separated format for `get_device_ips()`
- `.planning/phases/16-rest-bridge-universal-crud/16-CONTEXT.md` — Bridge architecture, pynautobot accessor pattern, error handling conventions

### Root Cause Context
- `.planning/STATE.md` — Root cause: external callers through bridge can inject `id__in=[uuid1..uuid10000]` → 414 on any endpoint

</canonical_refs>

<codebase_context>
## Existing Code Insights

### Reusable Assets
- `NautobotValidationError` in `exceptions.py` — already imported in bridge.py, used throughout for validation errors
- `MAX_LIMIT = 200` constant in `bridge.py` — existing hard cap constant; 500-item threshold is specific to `__in` param guard
- `tests/test_bridge.py` — existing test patterns: `TestEndpointValidation`, `TestFuzzyMatching`, `TestMethodValidation` classes

### Established Patterns
- Error raising pattern: `raise NautobotValidationError(message=..., hint=...)` — same pattern used for unknown endpoints, invalid methods, missing params
- Guard placement: intercept before `.filter()` call in both `_execute_core()` (L188) and `_execute_cms()` (L270)
- Module-level helper functions in bridge.py: `_validate_endpoint()`, `_suggest_endpoint()`, `_strip_uuid_from_endpoint()`, `_parse_core_endpoint()`

### Integration Points
- `_guard_filter_params()` is called inside `_execute_core()` (before L188) and `_execute_cms()` (before L270)
- No changes to `call_nautobot()` signature or to `server.py`
- Unit tests added to `tests/test_bridge.py` under a new test class (e.g., `TestParamGuard`)

### Key Observations
- `_execute_core()` L187-188: `endpoint_accessor.filter(**params, **pagination_kwargs)` — the exact call site where oversized `__in` lists cause 414
- `_execute_cms()` L269-270: `endpoint_accessor.filter(**effective_params, **pagination_kwargs)` — same pattern for CMS
- The guard must convert `__in` param values from `List[str]` to comma-separated `str` BEFORE the `.filter()` call so pynautobot sends them as `?key=val1,val2,val3` not repeated `?key=val1&key=val2`

</codebase_context>

<specifics>
## Specific Ideas

- Error message should include: param key name, item count, threshold (500)
- Unit test cases: small list (≤ 500) works correctly, large list (> 500) raises `NautobotValidationError`, non-`__in` list params pass through unchanged, mixed params (some `__in`, some not) handled correctly
- BRIDGE-05 tests should cover both `_execute_core()` and `_execute_cms()` paths

</specifics>

<deferred>
## Deferred Ideas

- Extending the guard to `__iexact`, `__icontains`, or other filter suffixes — future phase if needed
- Adding a CLI-level warning when a bridge call hits the guard (for visibility without crashing)

</deferred>

---

*Phase: 31-bridge-param-guard*
*Context gathered: 2026-03-29*
