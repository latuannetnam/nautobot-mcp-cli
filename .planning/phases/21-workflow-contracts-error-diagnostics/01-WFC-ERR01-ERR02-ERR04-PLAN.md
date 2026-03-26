# Plan 01: Workflow Contract Bugs + Error Diagnostics (client.py + workflows.py fixes)

## must_haves
- `verify_data_model` registry entry has `"parsed_config"` in `required` list (WFC-01)
- `verify_data_model` registry entry has `transforms` mapping `"parsed_config"` to `ParsedConfig.model_validate` (WFC-02)
- Import-time self-check function `_validate_registry()` raises `NautobotValidationError` on registry/signature mismatch (WFC-03)
- `_handle_api_error()` parses DRF 400 body JSON and passes field errors to `NautobotValidationError.errors` (ERR-01)
- `ERROR_HINTS` dict keyed by endpoint path prefix with actionable per-endpoint hint strings (ERR-02)
- `NautobotAPIError` raised with endpoint-specific or status-code-based hint (ERR-04)
- All changes verified by tests

## frontmatter
```yaml
wave: 1
depends_on: []
files_modified:
  - nautobot_mcp/workflows.py
  - nautobot_mcp/catalog/workflow_stubs.py
  - nautobot_mcp/client.py
  - tests/test_workflows.py
  - tests/test_client.py
  - tests/test_exceptions.py
autonomous: false
```

---

## Wave A — WFC-01 + WFC-02 (bug fixes, no new logic)

### Task A1 — Fix `verify_data_model` required list (WFC-01)
**File:** `nautobot_mcp/workflows.py`
**read_first:** `nautobot_mcp/workflows.py` L81–88; `nautobot_mcp/verification.py` L200–204

**Action:** In `WORKFLOW_REGISTRY["verify_data_model"]` (L87), change:
```python
"required": ["device_name"],
```
to:
```python
"required": ["device_name", "parsed_config"],
```

**acceptance_criteria:**
- `workflows.py` contains `"required": ["device_name", "parsed_config"]` in the `verify_data_model` registry entry
- `grep -n '"required".*device_name.*parsed_config' nautobot_mcp/workflows.py` returns a match at the verify_data_model entry

---

### Task A2 — Add `transforms` block to `verify_data_model` (WFC-02)
**File:** `nautobot_mcp/workflows.py`
**read_first:** `nautobot_mcp/workflows.py` L61–72 (`onboard_config` working transform pattern)

**Action:** After the `param_map` block for `verify_data_model` (L86), add:
```python
"transforms": {
    "parsed_config": lambda d: ParsedConfig.model_validate(d),
},
```
Place it before `},` that closes the entry (matching the `onboard_config` indentation pattern).

**acceptance_criteria:**
- `workflows.py` contains `"transforms":` at the verify_data_model registry entry
- `workflows.py` contains `lambda d: ParsedConfig.model_validate(d)` in that block
- `workflows.py` contains `ParsedConfig` import (already at L27)

---

### Task A3 — Update `workflow_stubs.py` verify_data_model params (WFC-03 aligned)
**File:** `nautobot_mcp/catalog/workflow_stubs.py`
**read_first:** `nautobot_mcp/catalog/workflow_stubs.py` L67–71

**Action:** Update `verify_data_model` stub `params` from:
```python
"params": {"device_name": "str (required)"},
```
to:
```python
"params": {
    "device_name": "str (required)",
    "parsed_config": "dict (required, ParsedConfig schema)",
},
```

**acceptance_criteria:**
- `workflow_stubs.py` contains `parsed_config` in the `verify_data_model` params dict
- `workflow_stubs.py` contains `ParsedConfig schema` in that param description
- `grep "verify_data_model" tests/test_workflows.py` confirms tests cover this workflow

---

## Wave B — WFC-03 (import-time registry self-check)

### Task B1 — Add `_validate_registry()` function (WFC-03)
**File:** `nautobot_mcp/workflows.py`
**read_first:** `nautobot_mcp/workflows.py` L1–110 (full WORKFLOW_REGISTRY); Python `inspect` module docs

**Action:** Add this function immediately before `WORKFLOW_REGISTRY` definition (around L35):
```python
def _validate_registry() -> None:
    """Validate WORKFLOW_REGISTRY entries against actual function signatures at import time.

    For each entry, compares the union of required + param_map keys (agent-facing names)
    against the function's actual parameters, excluding 'client' (always injected separately).

    Raises NautobotValidationError on any mismatch — fails fast, preventing a server
    from starting with a broken registry entry.
    """
    import inspect

    for wf_id, entry in WORKFLOW_REGISTRY.items():
        func = entry.get("function")
        if not func:
            continue  # skip entries without functions (shouldn't happen in practice)

        sig = inspect.signature(func)
        func_params = set(sig.parameters.keys())

        required = set(entry.get("required", []))
        param_map_keys = set(entry.get("param_map", {}).keys())
        registry_params = required | param_map_keys

        # client is injected by run_workflow, not an agent-facing param — exclude it
        func_params = func_params - {"client"}

        missing_in_func = registry_params - func_params
        extra_in_func = func_params - registry_params

        if missing_in_func:
            raise NautobotValidationError(
                f"WORKFLOW_REGISTRY['{wf_id}'] lists {sorted(missing_in_func)} as required/mapped "
                f"params but the function signature does not accept them. "
                f"Fix workflows.py entry for '{wf_id}'."
            )
        if extra_in_func:
            raise NautobotValidationError(
                f"WORKFLOW_REGISTRY['{wf_id}'] function accepts {sorted(extra_in_func)} "
                f"but these are not listed in required or param_map. "
                f"Fix workflows.py entry for '{wf_id}'."
            )
```

**acceptance_criteria:**
- `workflows.py` contains `def _validate_registry()` function
- `workflows.py` contains `import inspect` (module-level, near top)
- `workflows.py` contains `func_params = func_params - {"client"}` (excludes client param)
- `workflows.py` contains `NautobotValidationError` raised for missing_in_func case
- `python -c "import nautobot_mcp.workflows"` exits 0 with no errors (after Task A1+A2 done)

---

### Task B2 — Call `_validate_registry()` at module level (WFC-03)
**File:** `nautobot_mcp/workflows.py`
**read_first:** `nautobot_mcp/workflows.py` L110 (bottom of WORKFLOW_REGISTRY)

**Action:** After the closing `}` of `WORKFLOW_REGISTRY`, add:
```python
# Validate registry entries against function signatures at import time.
# Fails fast with NautobotValidationError if any entry is misconfigured.
_validate_registry()
```

**acceptance_criteria:**
- `workflows.py` contains `_validate_registry()` called at module level (after WORKFLOW_REGISTRY definition)
- Comment mentions "import time" or "startup"
- `python -c "from nautobot_mcp.workflows import run_workflow"` exits 0

---

## Wave C — ERR-01 + ERR-02 + ERR-04 (client.py error enrichment)

### Task C1 — Add `ERROR_HINTS` and `STATUS_CODE_HINTS` dicts (ERR-02 + ERR-04)
**File:** `nautobot_mcp/client.py`
**read_first:** `nautobot_mcp/client.py` L1–27 (imports); `nautobot_mcp/client.py` L119–170 (`_handle_api_error`)

**Action:** After the logger definition (L27) and before the `class NautobotClient` (L30), add:
```python
# Per-endpoint hint map for ERR-02: actionable hints keyed by URL path prefix.
# Longest-match wins (sorted by key length descending at lookup time).
ERROR_HINTS: dict[str, str] = {
    "/api/dcim/devices/": "Device filter accepts 'name', 'slug', or 'id' (UUID). "
        "Avoid partial name matches — use exact name or UUID.",
    "/api/dcim/interfaces/": "Interface filter requires 'device' set to device UUID, "
        "not device name. Use /api/dcim/devices/ to look up the UUID first.",
    "/api/dcim/locations/": "Location filter: use 'name' for exact match, "
        "'slug' for URL-safe match, or 'id' for UUID.",
    "/api/dcim/devices/<uuid>/interfaces/": "Device interfaces: filter by 'device' UUID only. "
        "Interface names are not valid filter values at this endpoint.",
    "/api/ipam/ip-addresses/": "IP address filter: use 'address' for exact, "
        "'family' for inet/inet6, 'device' for device UUID. "
        "Interface name is not a valid filter — use interface_id instead.",
    "/api/ipam/vlans/": "VLAN filter: use 'vid' (integer) or 'name'. "
        "Scope to a location with 'location' UUID for accuracy.",
    "/api/ipam/prefixes/": "Prefix filter: use 'prefix' for CIDR, "
        "'vlan_vid' for VLAN number, 'location' UUID to scope results.",
    "/api/tenancy/tenants/": "Tenant filter: use 'name' or 'slug'. "
        "Tenant groups are filtered via 'group' name, not group UUID.",
    "/api/extras/jobs/": "Job filter: use 'name' or 'slug'. "
        "Jobs may require appropriate permissions to appear in results.",
    "/api/plugins/golden_config/": "Golden Config plugin endpoints: ensure the "
        "plugin is installed and the service account has plugin permissions.",
}

# Status-code fallback hints for ERR-04: unknown endpoints get generic guidance
# keyed by HTTP status code.
STATUS_CODE_HINTS: dict[int, str] = {
    429: "Rate limited — retry after exponential backoff or check Nautobot task schedule",
    500: "Nautobot server error — check Nautobot service health and application logs",
    502: "Nautobot gateway error — check Nautobot service health and reverse proxy logs",
    503: "Nautobot unavailable — check service status and network connectivity",
    504: "Nautobot request timed out — try a narrower filter or smaller query",
    422: "Unprocessable entity — field values don't match Nautobot API schema; check data types",
}
```

**acceptance_criteria:**
- `client.py` contains `ERROR_HINTS: dict[str, str] = {` near top of file
- `client.py` contains at least 10 entries in ERROR_HINTS
- `client.py` contains `STATUS_CODE_HINTS: dict[int, str] = {`
- `client.py` contains `429:` and `500:` and `503:` entries in STATUS_CODE_HINTS

---

### Task C2 — Add `_get_hint_for_request()` helper (ERR-02 + ERR-04)
**File:** `nautobot_mcp/client.py`
**read_first:** `nautobot_mcp/client.py` L119–170 (`_handle_api_error`)

**Action:** Add as a module-level function before or after `ERROR_HINTS` / `STATUS_CODE_HINTS`:
```python
def _get_hint_for_request(
    req: Any,
    operation: str,
    model_name: str,
    status_code: int,
) -> str:
    """Resolve the best available hint for a failed API request.

    Strategy (in priority order):
    1. Longest-match ERROR_HINTS entry for the request URL path
    2. STATUS_CODE_HINTS entry for the HTTP status code
    3. Generic fallback string

    Args:
        req: requests.Response object (or Any from pynautobot RequestError.req).
             May be None if the error has no associated response.
        operation: Operation name (e.g., "list", "create", "filter").
        model_name: Model name (e.g., "Device", "Interface").
        status_code: HTTP status code integer.

    Returns:
        A hint string — always non-empty.
    """
    # 1. Try endpoint-specific hint from ERROR_HINTS
    if req is not None and hasattr(req, "url"):
        url = getattr(req, "url", "") or ""
        # Longest-match: sort keys by length descending, pick first match
        for hint_key in sorted(ERROR_HINTS.keys(), key=len, reverse=True):
            if hint_key in url:
                return ERROR_HINTS[hint_key]

    # 2. Try status-code fallback
    if status_code in STATUS_CODE_HINTS:
        return STATUS_CODE_HINTS[status_code]

    # 3. Generic fallback derived from operation + model
    fallbacks = {
        "list": f"Check that {model_name.lower()} objects exist in Nautobot and the filter parameters are valid",
        "get": f"Verify the {model_name.lower()} ID or name is correct",
        "create": f"Check required fields for {model_name.lower()} match the Nautobot API schema",
        "update": f"Verify the {model_name.lower()} exists and the update data is valid",
        "delete": f"Verify the {model_name.lower()} exists and is not protected",
    }
    return fallbacks.get(
        operation,
        f"Check {model_name.lower()} data and Nautobot server health",
    )
```

**acceptance_criteria:**
- `client.py` contains `def _get_hint_for_request(`
- `client.py` contains `for hint_key in sorted(ERROR_HINTS.keys(), key=len, reverse=True)`
- `client.py` contains `if status_code in STATUS_CODE_HINTS`
- `client.py` contains fallback `return` for when no hint matches
- `client.py` has `from typing import TYPE_CHECKING` and `Any` in TYPE_CHECKING or direct import

---

### Task C3 — Update `_handle_api_error()` for ERR-01 (400 body parsing)
**File:** `nautobot_mcp/client.py`
**read_first:** `nautobot_mcp/client.py` L119–170 (full `_handle_api_error`)

**Action:** Replace the `if status_code == 400:` branch (L152–156) with:
```python
            if status_code == 400:
                # ERR-01: Parse DRF 400 body for field-level errors
                import json as _json

                field_errors: list[dict[str, str]] = []
                req_obj = getattr(error, "req", None)
                raw_body = getattr(req_obj, "text", None) if req_obj else None

                if raw_body:
                    try:
                        body = _json.loads(raw_body)
                        # Handle DRF error shapes:
                        # {"field": ["msg"]}  or  {"field": "msg"}  or  {"detail": "string"}
                        if isinstance(body, dict):
                            for field, messages in body.items():
                                if isinstance(messages, list):
                                    for msg in messages:
                                        field_errors.append({"field": field, "error": str(msg)})
                                elif isinstance(messages, str):
                                    field_errors.append({"field": field, "error": messages})
                                else:
                                    field_errors.append({"field": field, "error": str(messages)})
                        elif isinstance(body, str):
                            # Non-dict body (e.g. plain "Invalid input.") — treat as detail
                            field_errors.append({"field": "_detail", "error": body})
                    except (ValueError, TypeError):
                        pass  # Non-JSON body — fall through to generic message

                hint = _get_hint_for_request(req_obj, operation, model_name, status_code)

                raise NautobotValidationError(
                    message=f"Validation error during {operation} on {model_name}: {error}",
                    hint=hint,
                    errors=field_errors if field_errors else None,
                ) from error
```

**acceptance_criteria:**
- `client.py` contains `field_errors: list[dict[str, str]] = []` for 400 handling
- `client.py` contains `_json.loads(raw_body)` parsing logic
- `client.py` contains `field_errors.append({"field": field, "error":` for both list and str message types
- `client.py` contains `errors=field_errors if field_errors else None` in NautobotValidationError

---

### Task C4 — Update `_handle_api_error()` for ERR-02 + ERR-04 (NautobotAPIError hints)
**File:** `nautobot_mcp/client.py`
**read_first:** `nautobot_mcp/client.py` L158–161 (NautobotAPIError raise)

**Action:** Update the `raise NautobotAPIError(...)` at L158–161 to use `_get_hint_for_request()`:
```python
            req_obj = getattr(error, "req", None)
            hint = _get_hint_for_request(req_obj, operation, model_name, status_code)

            raise NautobotAPIError(
                message=f"API error during {operation} on {model_name}: {error}",
                status_code=status_code,
                hint=hint,
            ) from error
```

**acceptance_criteria:**
- `client.py` contains `hint = _get_hint_for_request(req_obj, operation, model_name, status_code)` before NautobotAPIError
- `client.py` contains `hint=hint` in the NautobotAPIError constructor
- `client.py` no longer contains `"Check Nautobot server logs for details"` as a hardcoded default for NautobotAPIError

---

## Wave D — Tests

### Task D1 — Add WFC-03 registry self-check tests (WFC-03)
**File:** `tests/test_workflows.py`
**read_first:** `tests/test_workflows.py` L31–62 (TestRegistryMatchesStubs); `nautobot_mcp/workflows.py` L40–110

**Action:** Add new test class to `tests/test_workflows.py`:
```python
# ---------------------------------------------------------------------------
# WFC-03: Registry self-check (import-time signature validation)
# ---------------------------------------------------------------------------


class TestRegistrySelfCheck:
    """Test _validate_registry() import-time signature validation (WFC-03)."""

    def test_validate_registry_passes_for_correct_entry(self):
        """verify_data_model entry should pass validation after WFC-01/WFC-02 fixes."""
        # _validate_registry() is called at module import time.
        # If this import succeeds, the self-check passed.
        # (NautobotValidationError raised at import time = test fails)
        import nautobot_mcp.workflows  # noqa: F401
        assert True  # import succeeded = no validation error

    def test_validate_registry_catches_missing_required(self):
        """Entry with required param not in function signature raises NautobotValidationError."""
        from nautobot_mcp.exceptions import NautobotValidationError
        import inspect

        # Temporarily break an entry to trigger the check
        # We use onboard_config (has a valid function) but add a fake required param
        from nautobot_mcp import workflows as wf_module
        import copy

        original = wf_module.WORKFLOW_REGISTRY["onboard_config"].copy()
        wf_module.WORKFLOW_REGISTRY["onboard_config"]["required"] = ["fake_missing_param"]
        # Also need param_map entry so it's in registry_params
        wf_module.WORKFLOW_REGISTRY["onboard_config"]["param_map"]["fake_missing_param"] = "fake_missing_param"

        try:
            with pytest.raises(NautobotValidationError, match="fake_missing_param"):
                wf_module._validate_registry()
        finally:
            wf_module.WORKFLOW_REGISTRY["onboard_config"] = original

    def test_validate_registry_catches_extra_func_param(self):
        """Entry where function accepts param not listed in required or param_map raises."""
        from nautobot_mcp.exceptions import NautobotValidationError
        from nautobot_mcp import workflows as wf_module

        original = wf_module.WORKFLOW_REGISTRY["bgp_summary"].copy()
        # bgp_summary function: get_device_bgp_summary(client, device, detail=None)
        # Add 'fake_extra' as required — not in function signature
        wf_module.WORKFLOW_REGISTRY["bgp_summary"]["required"] = ["device", "fake_extra"]

        try:
            with pytest.raises(NautobotValidationError, match="fake_extra"):
                wf_module._validate_registry()
        finally:
            wf_module.WORKFLOW_REGISTRY["bgp_summary"] = original
```

**acceptance_criteria:**
- `test_workflows.py` contains `class TestRegistrySelfCheck`
- `test_workflows.py` contains `_validate_registry` in test code
- `pytest tests/test_workflows.py::TestRegistrySelfCheck -v` passes

---

### Task D2 — Add verify_data_model dispatch test (WFC-01 + WFC-02)
**File:** `tests/test_workflows.py`
**read_first:** `tests/test_workflows.py` L247–286 (TestRunWorkflowTransforms)

**Action:** Add to `TestRunWorkflowTransforms` class or add new class:
```python
    def test_verify_data_model_transforms_parsed_config(self):
        """parsed_config dict should be transformed to ParsedConfig via model_validate."""
        from unittest.mock import patch, MagicMock
        from nautobot_mcp.workflows import run_workflow, WORKFLOW_REGISTRY

        config_dict = {
            "hostname": "test-rtr",
            "platform": "junos",
            "interfaces": [],
            "ip_addresses": [],
            "vlans": [],
            "routing_instances": [],
            "protocols": [],
            "firewall_filters": [],
        }

        mock_parsed = MagicMock()
        mock_parsed.model_dump.return_value = {}

        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"interfaces": [], "ip_addresses": [], "vlans": []}

        # Save original
        orig = WORKFLOW_REGISTRY["verify_data_model"]["function"]

        def fake_verify(client, device_name, parsed_config):
            # parsed_config should be a ParsedConfig instance after transform
            from nautobot_mcp.models.parser import ParsedConfig
            assert isinstance(parsed_config, ParsedConfig)
            return mock_result

        WORKFLOW_REGISTRY["verify_data_model"]["function"] = fake_verify
        try:
            client = MagicMock()
            result = run_workflow(
                client,
                workflow_id="verify_data_model",
                params={"device_name": "test-rtr", "parsed_config": config_dict},
            )
            assert result["status"] == "ok"
        finally:
            WORKFLOW_REGISTRY["verify_data_model"]["function"] = orig
```

**acceptance_criteria:**
- `test_workflows.py` contains `test_verify_data_model_transforms_parsed_config`
- Test passes after Task A1 + A2 are complete

---

### Task D3 — Create `tests/test_client.py` (ERR-01 + ERR-02 + ERR-04)
**File:** `tests/test_client.py` (new file)
**read_first:** `nautobot_mcp/client.py` L119–170 (`_handle_api_error`); `nautobot_mcp/exceptions.py` L78–114

**Action:** Create `tests/test_client.py`:
```python
"""Tests for NautobotClient error handling (ERR-01, ERR-02, ERR-04)."""

from __future__ import annotations

from unittest.mock import MagicMock
import json

import pytest

from nautobot_mcp.client import (
    NautobotClient,
    _get_hint_for_request,
    ERROR_HINTS,
    STATUS_CODE_HINTS,
)
from nautobot_mcp.exceptions import NautobotValidationError, NautobotAPIError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_fake_response(status_code: int, text: str, url: str) -> MagicMock:
    """Build a fake requests.Response-like object for mocking pynautobot RequestError."""
    fake = MagicMock()
    fake.status_code = status_code
    fake.text = text
    fake.url = url
    fake.json = lambda: json.loads(text) if text else {}
    return fake


def make_request_error(status_code: int, text: str, url: str) -> MagicMock:
    """Build a fake pynautobot RequestError with a nested fake response."""
    fake = MagicMock()
    fake.req = make_fake_response(status_code, text, url)
    fake.__str__ = lambda self: f"{status_code} error"
    return fake


# ---------------------------------------------------------------------------
# _get_hint_for_request
# ---------------------------------------------------------------------------


class TestGetHintForRequest:
    """Test hint resolution in _get_hint_for_request (ERR-02 + ERR-04)."""

    def test_endpoint_hint_returns_device_hint(self):
        """Device endpoint should return the device-specific hint."""
        fake_req = make_fake_response(400, "{}", "/api/dcim/devices/")
        hint = _get_hint_for_request(fake_req, "list", "Device", 400)
        assert "name" in hint.lower() or "uuid" in hint.lower()
        assert "Check Nautobot server logs" not in hint

    def test_interface_endpoint_hint(self):
        """Interface endpoint should return interface-specific hint."""
        fake_req = make_fake_response(400, "{}", "/api/dcim/interfaces/")
        hint = _get_hint_for_request(fake_req, "filter", "Interface", 400)
        assert "UUID" in hint or "device" in hint.lower()

    def test_ip_address_endpoint_hint(self):
        """IP addresses endpoint should return IP-specific hint."""
        fake_req = make_fake_response(400, "{}", "/api/ipam/ip-addresses/")
        hint = _get_hint_for_request(fake_req, "list", "IPAddress", 400)
        assert "address" in hint.lower() or "family" in hint.lower()

    def test_longest_match_wins(self):
        """A more specific path should override a less specific one."""
        # /api/dcim/devices/<uuid>/interfaces/ is more specific than /api/dcim/interfaces/
        fake_req = make_fake_response(400, "{}", "/api/dcim/devices/abc-123/interfaces/")
        hint = _get_hint_for_request(fake_req, "list", "Interface", 400)
        # Should match the device-specific interfaces hint, not the generic interfaces hint
        assert "UUID" in hint

    def test_status_code_fallback_500(self):
        """Unknown endpoint with 500 should return 500 hint."""
        fake_req = make_fake_response(500, "Server Error", "/api/unknown/endpoint/")
        hint = _get_hint_for_request(fake_req, "list", "Unknown", 500)
        assert "500" not in hint  # hint should be human-readable, not just the code
        assert "health" in hint.lower() or "server" in hint.lower()

    def test_status_code_fallback_429(self):
        """Unknown endpoint with 429 should return rate-limit hint."""
        fake_req = make_fake_response(429, "Rate Limited", "/api/unknown/")
        hint = _get_hint_for_request(fake_req, "list", "Resource", 429)
        assert "rate" in hint.lower() or "retry" in hint.lower()

    def test_no_response_returns_fallback(self):
        """No response object should fall back to operation-specific generic hint."""
        hint = _get_hint_for_request(None, "list", "Device", 500)
        assert len(hint) > 0
        assert "check" in hint.lower()

    def test_unknown_operation_returns_generic_hint(self):
        """Unknown operation should return generic fallback."""
        fake_req = make_fake_response(404, "Not Found", "/api/dcim/devices/")
        hint = _get_hint_for_request(fake_req, "unknown_op", "Device", 404)
        assert len(hint) > 0


# ---------------------------------------------------------------------------
# ERR-01: 400 body parsing -> NautobotValidationError.errors
# ---------------------------------------------------------------------------


class TestHandleApiError400:
    """Test 400 error body parsing in _handle_api_error (ERR-01)."""

    def test_400_with_field_errors_parsed(self):
        """DRF 400 body with field errors should populate NautobotValidationError.errors."""
        drf_body = {
            "name": ["This field is required."],
            "device": ["Invalid pk 'abc' — object does not exist."],
        }
        fake_error = make_request_error(400, json.dumps(drf_body), "/api/dcim/devices/")

        client = NautobotClient.__new__(NautobotClient)
        client._profile = MagicMock()
        client._api = MagicMock()

        with pytest.raises(NautobotValidationError) as exc_info:
            client._handle_api_error(fake_error, operation="create", model_name="Device")

        assert exc_info.value.errors is not None
        assert len(exc_info.value.errors) == 2

        # Find errors by field name
        errors_by_field = {e["field"]: e["error"] for e in exc_info.value.errors}
        assert "name" in errors_by_field
        assert "This field is required" in errors_by_field["name"]
        assert "device" in errors_by_field
        assert "Invalid pk" in errors_by_field["device"]

        # to_dict() should include validation_errors
        err_dict = exc_info.value.to_dict()
        assert "validation_errors" in err_dict
        assert len(err_dict["validation_errors"]) == 2

    def test_400_with_non_field_errors(self):
        """DRF 400 body with non_field_errors should be included as field="_detail"."""
        drf_body = {"non_field_errors": ["Object with name='foo' already exists."]}
        fake_error = make_request_error(400, json.dumps(drf_body), "/api/dcim/devices/")

        client = NautobotClient.__new__(NautobotClient)
        client._profile = MagicMock()
        client._api = MagicMock()

        with pytest.raises(NautobotValidationError) as exc_info:
            client._handle_api_error(fake_error, operation="create", model_name="Device")

        assert exc_info.value.errors is not None
        errors_by_field = {e["field"]: e["error"] for e in exc_info.value.errors}
        assert "_detail" in errors_by_field
        assert "already exists" in errors_by_field["_detail"]

    def test_400_with_detail_string(self):
        """DRF 400 body with plain string detail should be treated as _detail error."""
        drf_body = {"detail": "Invalid filter parameter"}
        fake_error = make_request_error(400, json.dumps(drf_body), "/api/dcim/devices/")

        client = NautobotClient.__new__(NautobotClient)
        client._profile = MagicMock()
        client._api = MagicMock()

        with pytest.raises(NautobotValidationError) as exc_info:
            client._handle_api_error(fake_error, operation="list", model_name="Device")

        assert exc_info.value.errors is not None
        assert any(e["field"] == "_detail" for e in exc_info.value.errors)

    def test_400_with_non_json_body(self):
        """400 with non-JSON body should not crash — fall back gracefully."""
        fake_error = make_request_error(400, "Internal Server Error", "/api/dcim/devices/")
        fake_error.req.json = MagicMock(side_effect=ValueError("not json"))

        client = NautobotClient.__new__(NautobotClient)
        client._profile = MagicMock()
        client._api = MagicMock()

        with pytest.raises(NautobotValidationError) as exc_info:
            client._handle_api_error(fake_error, operation="list", model_name="Device")

        # Should still raise but with empty errors list (fallback behavior)
        assert exc_info.value.errors == [] or exc_info.value.errors is None

    def test_400_with_none_req(self):
        """400 where error.req is None should not crash."""
        fake_error = MagicMock()
        fake_error.req = None

        client = NautobotClient.__new__(NautobotClient)
        client._profile = MagicMock()
        client._api = MagicMock()

        with pytest.raises(NautobotValidationError):
            client._handle_api_error(fake_error, operation="list", model_name="Device")


# ---------------------------------------------------------------------------
# ERR-02 + ERR-04: NautobotAPIError hint enrichment
# ---------------------------------------------------------------------------


class TestHandleApiErrorHintMap:
    """Test that NautobotAPIError uses endpoint-specific or status-code hints (ERR-02, ERR-04)."""

    def test_500_error_uses_status_code_hint(self):
        """500 error should include status-code-based hint, not generic message."""
        fake_error = make_request_error(500, "Internal Server Error", "/api/dcim/devices/")

        client = NautobotClient.__new__(NautobotClient)
        client._profile = MagicMock()
        client._api = MagicMock()

        with pytest.raises(NautobotAPIError) as exc_info:
            client._handle_api_error(fake_error, operation="list", model_name="Device")

        assert exc_info.value.status_code == 500
        assert exc_info.value.hint != "Check Nautobot server logs for details"
        assert len(exc_info.value.hint) > 0
        assert "health" in exc_info.value.hint.lower() or "server" in exc_info.value.hint.lower()

    def test_429_error_uses_rate_limit_hint(self):
        """429 error should include rate-limit specific hint."""
        fake_error = make_request_error(429, "Rate Limited", "/api/dcim/devices/")

        client = NautobotClient.__new__(NautobotClient)
        client._profile = MagicMock()
        client._api = MagicMock()

        with pytest.raises(NautobotAPIError) as exc_info:
            client._handle_api_error(fake_error, operation="list", model_name="Device")

        assert exc_info.value.status_code == 429
        assert "rate" in exc_info.value.hint.lower() or "retry" in exc_info.value.hint.lower()

    def test_known_endpoint_gets_specific_hint(self):
        """Known endpoint should get endpoint-specific hint, not generic fallback."""
        fake_error = make_request_error(400, "Bad Request", "/api/dcim/interfaces/")

        client = NautobotClient.__new__(NautobotClient)
        client._profile = MagicMock()
        client._api = MagicMock()

        # 400 raises NautobotValidationError, not NautobotAPIError
        with pytest.raises(NautobotValidationError) as exc_info:
            client._handle_api_error(fake_error, operation="filter", model_name="Interface")

        # Hint should be interface-specific, not generic
        assert "UUID" in exc_info.value.hint or "device" in exc_info.value.hint.lower()
        assert exc_info.value.hint != "Check required fields and data formats"

    def test_api_error_to_dict_includes_hint(self):
        """NautobotAPIError.to_dict() should include the hint field."""
        from nautobot_mcp.exceptions import NautobotAPIError
        err = NautobotAPIError(
            message="Server error",
            status_code=500,
            hint="Check Nautobot health",
        )
        d = err.to_dict()
        assert "hint" in d
        assert d["hint"] == "Check Nautobot health"

    def test_validation_error_to_dict_includes_validation_errors(self):
        """NautobotValidationError.to_dict() should include validation_errors when set."""
        from nautobot_mcp.exceptions import NautobotValidationError
        err = NautobotValidationError(
            message="Bad data",
            errors=[{"field": "name", "error": "required"}],
        )
        d = err.to_dict()
        assert "validation_errors" in d
        assert d["validation_errors"][0]["field"] == "name"
```

**acceptance_criteria:**
- `tests/test_client.py` file exists
- `pytest tests/test_client.py -v` passes (all green)
- `tests/test_client.py` covers ERR-01 (400 body parsing), ERR-02 (endpoint hints), ERR-04 (status-code hints)

---

### Task D4 — Extend `tests/test_exceptions.py` (ERR-04)
**File:** `tests/test_exceptions.py`
**read_first:** `tests/test_exceptions.py` L49–89

**Action:** Append two tests to `test_exceptions.py`:
```python


def test_validation_error_to_dict_includes_validation_errors():
    """NautobotValidationError.to_dict() must include validation_errors key when errors set."""
    error = NautobotValidationError(
        message="Invalid device data",
        hint="Check required fields",
        errors=[
            {"field": "name", "error": "This field is required."},
            {"field": "device_type", "error": "Invalid pk 'foo' — object does not exist."},
        ],
    )
    result = error.to_dict()
    assert "validation_errors" in result
    assert len(result["validation_errors"]) == 2
    assert result["validation_errors"][0]["field"] == "name"
    assert result["validation_errors"][1]["error"] == "Invalid pk 'foo' — object does not exist."


def test_api_error_hint_preserved_in_to_dict():
    """NautobotAPIError.to_dict() must include the hint field with the correct value."""
    error = NautobotAPIError(
        message="Server error",
        status_code=500,
        hint="Nautobot server error — check Nautobot service health and application logs",
    )
    result = error.to_dict()
    assert "hint" in result
    assert result["hint"] == "Nautobot server error — check Nautobot service health and application logs"
    assert result["status_code"] == 500
    assert result["code"] == "API_ERROR"


def test_api_error_default_hint_is_not_generic():
    """NautobotAPIError created without hint should NOT use generic 'check server logs'."""
    error = NautobotAPIError(message="Server error", status_code=500)
    # The default hint should be derived from status code, not a generic placeholder
    assert error.hint != "Check Nautobot server logs for details"
    assert len(error.hint) > 0
```

**acceptance_criteria:**
- `test_exceptions.py` contains `test_validation_error_to_dict_includes_validation_errors`
- `test_exceptions.py` contains `test_api_error_hint_preserved_in_to_dict`
- `pytest tests/test_exceptions.py -v` passes

---

## Verification
```bash
# WFC-01 + WFC-02: verify_data_model entry correct
grep -A5 '"verify_data_model"' nautobot_mcp/workflows.py | grep -E 'required|transforms|parsed_config'

# WFC-03: module import succeeds (no NautobotValidationError)
python -c "from nautobot_mcp.workflows import run_workflow; print('import ok')"

# ERR-01: 400 body parsing
pytest tests/test_client.py::TestHandleApiError400 -v

# ERR-02 + ERR-04: hint map
pytest tests/test_client.py::TestHandleApiErrorHintMap tests/test_client.py::TestGetHintForRequest -v

# All new tests
pytest tests/test_client.py tests/test_workflows.py::TestRegistrySelfCheck tests/test_exceptions.py -v
```
