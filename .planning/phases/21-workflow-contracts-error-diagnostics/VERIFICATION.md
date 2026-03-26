---
status: passed
---

# Phase 21 Verification Report

**Phase:** 21-workflow-contracts-error-diagnostics
**Verified:** 2026-03-26
**Result:** ✅ All 7 must_haves ACHIEVED

---

## Requirement → Implementation Cross-Reference

| Requirement | Description | File(s) | Status |
|-------------|-------------|---------|--------|
| WFC-01 | `verify_data_model` has `"parsed_config"` in `required` | `workflows.py` L139 | ✅ |
| WFC-02 | `verify_data_model` maps `parsed_config` to `ParsedConfig.model_validate` | `workflows.py` L140–142 | ✅ |
| WFC-03 | `_validate_registry()` raises `NautobotValidationError` on mismatch | `workflows.py` L40–89, L169 | ✅ |
| ERR-01 | `_handle_api_error()` parses DRF 400 body → `NautobotValidationError.errors` | `client.py` L240–278 | ✅ |
| ERR-02 | `ERROR_HINTS` dict keyed by endpoint path prefix | `client.py` L32–54 | ✅ |
| ERR-03 | `run_workflow()` catches composite exceptions → `warnings=[{"operation", "error"}]` | `workflows.py` L343–360 | ✅ |
| ERR-04 | `NautobotAPIError` uses status-code-derived hint | `exceptions.py` L101–121, `client.py` L280–286 | ✅ |

---

## Must_Have Verification

### WFC-01 ✅
**Requirement:** `verify_data_model` registry entry has `"parsed_config"` in `required` list.

**Evidence — `workflows.py` L133–143:**
```python
"verify_data_model": {
    "function": verify_data_model,
    "param_map": {
        "device_name": "device_name",
        "parsed_config": "parsed_config",
    },
    "required": ["device_name", "parsed_config"],   ← WFC-01
    "transforms": {
        "parsed_config": lambda d: ParsedConfig.model_validate(d),
    },
},
```

---

### WFC-02 ✅
**Requirement:** `verify_data_model` registry entry has `transforms` mapping `"parsed_config"` to `ParsedConfig.model_validate`.

**Evidence — `workflows.py` L140–142:**
```python
"transforms": {
    "parsed_config": lambda d: ParsedConfig.model_validate(d),   ← WFC-02
},
```

`ParsedConfig` is imported at L27: `from nautobot_mcp.models.parser import ParsedConfig`.

---

### WFC-03 ✅
**Requirement:** Import-time self-check `_validate_registry()` raises `NautobotValidationError` on registry/signature mismatch.

**Evidence — `workflows.py` L40–89:**
- `_validate_registry()` defined at L40, called at module level L169 (`_validate_registry()`)
- Validates mapped func param names against actual function signatures (L61–77)
- Raises `NautobotValidationError` for `missing_in_func` (L79–83) and `extra_no_defaults` (L84–88)
- Import test: `python -c "from nautobot_mcp.workflows import run_workflow"` → `import ok`
- Intentional-mismatch test: injecting `fake_missing` param triggers `NautobotValidationError` at import time
- `workflow_stubs.py` L67–71 updated to document `parsed_config` as required param

---

### ERR-01 ✅
**Requirement:** `_handle_api_error()` parses DRF 400 body JSON and passes field errors to `NautobotValidationError.errors`.

**Evidence — `client.py` L240–278:**
```python
# ERR-01: Parse DRF 400 body — handle None req by using effective_status=400
if status_code == 400 or (req_obj is None and not isinstance(error, RequestsConnectionError)):
    effective_status = status_code if status_code == 400 else 400
    field_errors: list[dict[str, str]] = []                          ← ERR-01

    if req_obj is not None:
        raw_body = getattr(req_obj, "text", None)
        if raw_body:
            import json as _json
            try:
                body = _json.loads(raw_body)
                if isinstance(body, dict):
                    for field, messages in body.items():
                        normalized_field = "_detail" if field in ("detail", "non_field_errors") else field
                        if isinstance(messages, list):
                            for msg in messages:
                                field_errors.append({"field": normalized_field, "error": str(msg)})
                        elif isinstance(messages, str):
                            field_errors.append({"field": normalized_field, "error": messages})
                        else:
                            field_errors.append({"field": normalized_field, "error": str(messages)})
                elif isinstance(body, str):
                    field_errors.append({"field": "_detail", "error": body})
            except (ValueError, TypeError):
                pass

    raise NautobotValidationError(
        message=f"Validation error during {operation} on {model_name}: {error}",
        hint=hint,
        errors=field_errors if field_errors else None,               ← ERR-01
    ) from error
```

**Test coverage (`tests/test_client.py::TestHandleApiError400`, 5 tests):**
- `test_400_with_field_errors_parsed` — `{"name": ["required"], "device": ["Invalid pk"]}` → 2 entries
- `test_400_with_non_field_errors` — `{"non_field_errors": [...]}` → `field="_detail"`
- `test_400_with_detail_string` — `{"detail": "..."}` → `field="_detail"`
- `test_400_with_non_json_body` — graceful fallback (no crash)
- `test_400_with_none_req` — `req=None` handled safely

---

### ERR-02 ✅
**Requirement:** `ERROR_HINTS` dict keyed by endpoint path prefix with actionable per-endpoint hint strings.

**Evidence — `client.py` L32–54:**
```python
ERROR_HINTS: dict[str, str] = {
    "/api/dcim/devices/": "Device filter accepts 'name', 'slug', or 'id' (UUID). ...",
    "/api/dcim/interfaces/": "Interface filter requires 'device' set to device UUID, ...",
    "/api/dcim/locations/": "Location filter: use 'name' for exact match, ...",
    "/api/dcim/devices/<uuid>/interfaces/": "Device interfaces: filter by 'device' UUID only. ...",
    "/api/ipam/ip-addresses/": "IP address filter: use 'address' for exact, ...",
    "/api/ipam/vlans/": "VLAN filter: use 'vid' (integer) or 'name'. ...",
    "/api/ipam/prefixes/": "Prefix filter: use 'prefix' for CIDR, ...",
    "/api/tenancy/tenants/": "Tenant filter: use 'name' or 'slug'. ...",
    "/api/extras/jobs/": "Job filter: use 'name' or 'slug'. ...",
    "/api/plugins/golden_config/": "Golden Config plugin endpoints: ensure the plugin is installed ...",
}
```
- **10 entries** (plan required ≥ 10)
- Longest-match lookup: `for hint_key in sorted(ERROR_HINTS.keys(), key=len, reverse=True)` at L95
- Test: `tests/test_client.py::TestGetHintForRequest::test_longest_match_wins` — `/api/dcim/devices/abc-123/interfaces/` matches device-specific hint

---

### ERR-03 ✅
**Requirement:** `run_workflow()` catches composite function exceptions and adds `{"operation": "<function_name>", "error": "<exception_string>"}` to `warnings` in the error envelope.

**Evidence — `workflows.py` L343–360:**
```python
except Exception as e:
    # ERR-03: Composite workflow exceptions are captured as warnings in the
    # envelope rather than a bare error string. This gives agents visibility
    # into which child operation failed without losing the error status.
    exception_warning = {
        "operation": workflow_id,    ← ERR-03
        "error": str(e),             ← ERR-03
    }
    return _build_envelope(
        workflow_id,
        params,
        error=e,
        warnings=[exception_warning],   ← ERR-03
    )
```

**Envelope structure confirmed:**
- `status: "error"` preserved (data is None) ✓
- `warnings: [{"operation": "...", "error": "..."}]` added ✓
- `error` field retains exception string for backward compatibility ✓

**Runtime verification:**
```
status: error
warnings: [{'operation': 'bgp_summary', 'error': 'Nautobot API timeout'}]
```

**Test coverage (`tests/test_workflows.py::TestRunWorkflowCompositeErrorOrigin`, 7 tests):**
- `test_workflow_exception_includes_operation_in_warnings` — bgp_summary
- `test_routing_table_exception_includes_operation_origin` — routing_table
- `test_firewall_summary_exception_includes_operation_origin` — firewall_summary
- `test_interface_detail_exception_includes_operation_origin` — interface_detail
- `test_verify_data_model_exception_includes_operation_origin` — verify_data_model
- `test_error_string_still_present_in_envelope` — backward compat
- `test_partial_failure_from_composite_still_returns_partial_not_error` — Phase 19 preserved

---

### ERR-04 ✅
**Requirement:** `NautobotAPIError` raised with endpoint-specific or status-code-based hint.

**Evidence — two-part implementation:**

**Part A — `exceptions.py` L101–121 (`_STATUS_DEFAULTS` class attribute):**
```python
_STATUS_DEFAULTS: dict[int, str] = {
    429: "Rate limited — retry after exponential backoff or check Nautobot task schedule",
    500: "Nautobot server error — check Nautobot service health and application logs",
    502: "Nautobot gateway error — check Nautobot service health and reverse proxy logs",
    503: "Nautobot unavailable — check service status and network connectivity",
    504: "Nautobot request timed out — try a narrower filter or smaller query",
    422: "Unprocessable entity — field values don't match Nautobot API schema; check data types",
}

def __init__(self, ..., hint: Optional[str] = None) -> None:
    if hint is None:
        hint = self._STATUS_DEFAULTS.get(status_code, "Check Nautobot server logs for details")
    ...
```

**Part B — `client.py` L280–286 (all API errors enriched with hint):**
```python
hint = _get_hint_for_request(req_obj, operation, model_name, status_code)
raise NautobotAPIError(
    message=f"API error during {operation} on {model_name}: {error}",
    status_code=status_code,
    hint=hint,          ← ERR-04: endpoint-specific or status-code-derived
) from error
```

**Hint resolution priority (confirmed by tests):**
1. Longest-match `ERROR_HINTS` entry for request URL path
2. `STATUS_CODE_HINTS` entry for HTTP status code
3. Operation-specific generic fallback string

**Runtime verification:**
```
NautobotAPIError(status_code=500) → hint: "Nautobot server error — check Nautobot service health..."
hint != "Check Nautobot server logs for details"  ✓
```

**Test coverage (`tests/test_client.py::TestHandleApiErrorHintMap`, 4 tests):**
- `test_500_error_uses_status_code_hint`
- `test_429_error_uses_rate_limit_hint`
- `test_known_endpoint_gets_specific_hint`
- `test_api_error_to_dict_includes_hint`

---

## Requirements.md Traceability

`REQUIREMENTS.md` (`.planning/REQUIREMENTS.md`) defines Phase 21 requirements as **WFC-01/02/03** and **ERR-01/02/03/04** (7 items). All are satisfied by this phase. The traceability table at L84–90 marks them as "Pending" — phase implementer should update to "Complete."

---

## Test Summary

| Test File | Tests | Result |
|-----------|-------|--------|
| `tests/test_workflows.py` (full) | 48 | ✅ Pass |
| `tests/test_client.py` | 18 | ✅ Pass |
| `tests/test_exceptions.py` | 11 | ✅ Pass |
| **Full suite** | **462 passed, 11 deselected** | ✅ Pass |

### Key test assertions confirmed:
- `pytest tests/test_workflows.py::TestRegistrySelfCheck -v` — 3/3 pass (WFC-03)
- `pytest tests/test_workflows.py::TestRunWorkflowCompositeErrorOrigin -v` — 7/7 pass (ERR-03)
- `pytest tests/test_workflows.py::TestVerifyDataModelTransform -v` — 1/1 pass (WFC-01/02)
- `pytest tests/test_client.py -v` — 18/18 pass (ERR-01/02/04)
- `pytest tests/test_exceptions.py -v` — 11/11 pass (ERR-04)
- `python -c "from nautobot_mcp.workflows import run_workflow"` — `import ok`

---

## Auto-Fixed Pre-existing Bugs (caught by WFC-03)

Three real bugs discovered by `_validate_registry()` during development:

1. **`onboard_config` param_map key `"config_data"`** → corrected to `"parsed_config"` (parameter name mismatch)
2. **`compare_device` had `live_data` in both `required` and `param_map`** → corrected to `"interfaces_data"` in `required` (signature now matches)
3. **Validator originally flagged optional function params** → updated to only flag required params without defaults

---

## Deviations from Plan

None. All plan tasks executed as written. Two plans (01 and 02) both fully completed.

---

## Files Modified

| File | Changes |
|------|---------|
| `nautobot_mcp/workflows.py` | WFC-01/02/03 fixes, ERR-03 composite error handler |
| `nautobot_mcp/client.py` | ERR-01 400 body parsing, ERR-02 ERROR_HINTS, ERR-04 hint enrichment |
| `nautobot_mcp/exceptions.py` | ERR-04 `_STATUS_DEFAULTS` on `NautobotAPIError` |
| `nautobot_mcp/catalog/workflow_stubs.py` | WFC-03 aligned: `verify_data_model` params updated |
| `tests/test_client.py` | New file: 18 tests (ERR-01/02/04) |
| `tests/test_workflows.py` | 11 new tests (WFC-03: 3, WFC-01/02: 1, ERR-03: 7) |
| `tests/test_exceptions.py` | 3 new tests (ERR-01/04) |

---

*Verification completed: 2026-03-26*
*All 7 must_haves ACHIEVED | 462/462 tests passing*
