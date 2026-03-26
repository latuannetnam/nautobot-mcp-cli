# Phase 21: Workflow Contracts & Error Diagnostics — Research

**Research date:** 2026-03-26
**Covers:** WFC-01, WFC-02, WFC-03, ERR-01, ERR-02, ERR-03, ERR-04

---

## 1. The `verify_data_model` Bug (WFC-01, WFC-02)

### Current state

`workflows.py` L81–88:

```python
"verify_data_model": {
    "function": verify_data_model,
    "param_map": {
        "device_name": "device_name",
        "parsed_config": "parsed_config",   # ← key IS present
    },
    "required": ["device_name"],           # ← BUG: "parsed_config" missing
},
```

`verification.py` L200–204 — actual function signature:

```python
def verify_data_model(
    client: NautobotClient,
    device_name: str,
    parsed_config: ParsedConfig,   # ← required parameter
) -> DriftReport:
```

### Key facts

- `param_map` is **already correct** (has `"parsed_config": "parsed_config"`)
- Only the `required` list is wrong — it's missing `"parsed_config"`
- `onboard_config` (L61–72 of `workflows.py`) is the **working reference pattern** for how `transforms` should look:
  ```python
  "transforms": {
      "config_data": lambda d: ParsedConfig.model_validate(d),
  }
  ```
- `workflow_stubs.py` L67–71: `verify_data_model` stub `params` is `{"device_name": "str (required)"}` — needs `parsed_config` added

### What WFC-01 and WFC-02 require fixing

| File | Change |
|------|--------|
| `workflows.py` L87 | `"required": ["device_name", "parsed_config"]` |
| `workflows.py` L86 | Add `"transforms"` block (mirror `onboard_config` pattern) |
| `workflow_stubs.py` L68 | Update `params` to include `parsed_config` entry |

### What `ParsedConfig.model_validate` does

`parser.py` L102 — Pydantic v2 `BaseModel`. `model_validate(data: dict)` is a **classmethod** that validates a dict against the model's field schema and returns a `ParsedConfig` instance (or raises `ValidationError` if the dict doesn't match).

The agent-facing input is a raw `dict` (the `ParsedConfig` schema as JSON). The `model_validate` transform converts it to a typed `ParsedConfig` object before passing to `verify_data_model`.

---

## 2. WFC-03: Import-Time Self-Check

### The mechanism

`WORKFLOW_REGISTRY` is a plain `dict`. The self-check function should be a module-level function in `workflows.py` that:
1. Uses Python's `inspect` module to introspect each registered function's signature
2. Compares `inspect.signature(func).parameters.keys()` against the union of `entry["required"]` and `entry.get("param_map", {}).keys()`
3. Raises `NautobotValidationError` with a descriptive message on mismatch

**No `inspect` usage exists anywhere in `nautobot_mcp/` yet** — this is net-new but standard Python.

### What to check

For every registry entry:
```
func_params   = set(inspect.signature(entry["function"]).parameters.keys())
registry_params = set(entry["required"]) ∪ set(entry["param_map"].keys())

func_params must include every item in registry_params
```

`verify_data_model(client, device_name, parsed_config)` → `func_params = {"client", "device_name", "parsed_config"}`
Registry params = `{"device_name"} ∪ {"parsed_config"}` = `{"device_name", "parsed_config"}` → `"parsed_config"` missing from function → **catch it at import time**.

### Where to call it

Two options:
1. **Module-level call** at the bottom of `workflows.py` — runs immediately when module is imported. Simple, effective. Fails fast on `python -c "import nautobot_mcp.workflows"`.
2. **Lazy call** in `run_workflow()` — first invocation validates. More lenient but delays discovery.

Decision D-04 in 21-CONTEXT.md says "import-time validation". Use **module-level call**.

### Call chain

`nautobot_mcp/workflows.py` → import → `_validate_registry()` runs → `NautobotValidationError` propagates → MCP server startup fails with clear message.

### Interaction with WFC-01/WFC-02

WFC-01 and WFC-02 fixes must happen **before** the self-check is added, or the self-check will immediately fire on the current broken state. Best order: fix WFC-01 + WFC-02 first, then add WFC-03 self-check.

---

## 3. ERR-03: Composite Workflow Error → `origin` in Envelope

### What the code currently does

`workflows.py` L284–285:

```python
except Exception as e:
    return _build_envelope(workflow_id, params, error=e)
```

Any exception from a workflow function → `status: "error"` envelope with the exception string.

### What ERR-03 requires

Composite workflows (`bgp_summary`, `routing_table`, `firewall_summary`, `interface_detail`) already return `(result, warnings_list)` tuples. The ERR-03 requirement applies to **non-composite** workflows or the outer dispatch level: when a composite workflow function itself raises (not returns partial data), capture the exception as a warning entry rather than an error envelope.

**Correction from Phase 19 context:** The ERR-03 requirement is about the `run_workflow()` exception handler. When a composite function raises an exception mid-execution (instead of returning `partial`), catch it and add it to `warnings` rather than returning `status: "error"`.

However, Phase 19's decision (D-07) explicitly says: "Error is caught at the `run_workflow()` level, not inside composite functions." And D-17: composite functions return `(result, warnings)` tuples. The existing `_build_envelope()` already handles the `partial` case.

The ERR-03 `{"operation": "<function_name>", "error": "<exception_string>"}` format is **identical** to the `WarningCollector` warning format from Phase 19. No new format needed.

### Implementation approach

When `run_workflow()` catches an exception from a composite function, it should add it to a `warnings` list and return `status: "partial"` instead of `status: "error"`. However, this has a semantic problem: if the primary query fails (not enrichment), returning `partial` is misleading. The distinction between "primary failure" and "enrichment failure" needs to be preserved.

Decision: **ERR-03 applies to composite function exceptions caught at the dispatch level** — when the function raises before returning any data. These become `status: "partial"` with the exception as the only warning. This mirrors the Phase 19 PFR semantics: any data is better than no data.

### `WarningCollector` as reference

`warnings.py` L31–41:

```python
def add(self, operation: str, error: str) -> None:
    logger.warning("Partial failure in %s: %s", operation, error)
    self._warnings.append({"operation": operation, "error": error})
```

ERR-03 warnings use the same `{"operation": ..., "error": ...}` shape.

---

## 4. ERR-01: 400 Body Parsing in `_handle_api_error()`

### Current code

`client.py` L152–156:

```python
if status_code == 400:
    raise NautobotValidationError(
        message=f"Validation error during {operation} on {model_name}: {error}",
        hint=f"Check required fields for {model_name}",
    ) from error
```

`error` here is a pynautobot `RequestError`. The message string contains the parsed DRF response if available.

### pynautobot RequestError structure (pynautobot 3.0.0)

```python
class RequestError(Exception):
    def __init__(self, message):
        self.req = req                      # requests.Response object
        self.request_body = req.request.body
        self.base = req.url
        self.error = req.text               # RAW response body (string)
```

`error.req` is a `requests.Response` object. `error.req.text` is the raw response body (JSON string for DRF 400s).

### DRF 400 response body shape

Django REST Framework returns 400 responses with this structure:

```json
{
  "field_name": ["error message 1", "error message 2"],
  "other_field": ["another error"]
}
```

Or nested:
```json
{
  "non_field_errors": ["Object with name='foo' already exists."]
}
```

For Nautobot specifically (based on typical DRF patterns):
```json
{
  "name": ["This field is required."],
  "device": ["Invalid pk 'abc' — object does not exist."]
}
```

### ERR-01 implementation

```python
import json

if status_code == 400:
    field_errors = []
    try:
        body = json.loads(error.req.text)  # error.req is requests.Response
        # Flatten DRF error structure to list[dict]
        for field, messages in (body.items() if isinstance(body, dict) else []):
            for msg in (messages if isinstance(messages, list) else [messages]):
                field_errors.append({"field": field, "error": str(msg)})
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass  # fallback to generic message

    raise NautobotValidationError(
        message=f"Validation error during {operation} on {model_name}: {error}",
        hint=f"Check required fields for {model_name}",
        errors=field_errors if field_errors else None,
    ) from error
```

### Key pitfalls

- `error.req` might be `None` if pynautobot raises a malformed `RequestError` — guard with `getattr(error, "req", None)`
- DRF sometimes returns a plain string `"Invalid input."` for non-field errors — handle non-dict bodies gracefully
- The raw `str(error)` is already informative — `NautobotValidationError` `to_dict()` will include `validation_errors` only if `errors` is non-empty
- **Do not** overwrite the hint — the hint enrichment (ERR-02) happens at a different level

---

## 5. ERR-02 + ERR-04: Per-Endpoint Hint Map

### Current state

`NautobotAPIError` (exceptions.py L98–114):

```python
def __init__(
    self,
    message: str = "Nautobot API error",
    status_code: int = 0,
    hint: str = "Check Nautobot server logs for details",  # ← generic default
) -> None:
```

`NautobotValidationError` hint is `"Check required fields and data formats"` — already somewhat specific but not endpoint-aware.

### ERR-04 requirement

Replace the generic `NautobotAPIError` default hint with operation-specific guidance based on the **endpoint** and **status code**.

### ERR-02 requirement

Error hints should be contextual per endpoint, not generic "check server logs."

### Hint map strategy

Define `ERROR_HINTS` as a `dict[str, str]` in `client.py`, keyed by URL path prefix. D-06 specifies ~10–15 high-value endpoints.

**Approach A — Exact URL path (from `error.req.url`):**
```python
ERROR_HINTS = {
    "/api/dcim/devices/": "Device filter expects UUID or name; slug fields use device name",
    "/api/dcim/interfaces/": "Interface filter requires 'device' (UUID) not 'device_name'",
    "/api/ipam/ip-addresses/": "IP filter: use 'address' for exact, 'family' for inet/inet6",
    ...
}
```

**Approach B — Operation + model pattern:**
```python
def _derive_hint(operation: str, model_name: str, status_code: int) -> str:
    """Fallback hint derived from operation and model when no endpoint-specific hint."""
    hints = {
        (404, "list", "Device"): "Device not found — verify name or UUID exists in Nautobot",
        (400, "filter", "Interface"): "Interface filter requires device=<uuid>, not device_name",
        ...
    }
    return hints.get((status_code, operation, model_name), _status_code_hint(status_code))
```

D-06 says the hint map is keyed by endpoint path prefix. Use **Approach A for known endpoints, Approach B for unknown**.

### Status code fallback hints (ERR-04)

```python
STATUS_CODE_HINTS = {
    429: "Rate limited — retry after exponential backoff or check Nautobot task schedule",
    500: "Nautobot server error — check Nautobot service health and logs",
    503: "Nautobot unavailable — check service status and network connectivity",
    504: "Nautobot request timed out — try a narrower filter or smaller query",
    502: "Nautobot gateway error — check Nautobot service health",
    422: "Unprocessable entity — check field formats match Nautobot API schema",
}
```

### Where to apply hints

`_handle_api_error()` builds the exceptions. Apply the hint map **inside `_handle_api_error()`** before raising:

```python
# After determining status_code
hint = _get_hint_for_request(getattr(error, "req", None), operation, model_name, status_code)

if status_code == 400:
    raise NautobotValidationError(..., hint=hint) from error

raise NautobotAPIError(
    message=...,
    status_code=status_code,
    hint=hint,
) from error
```

`NautobotAPIError` already accepts a `hint` parameter — no exception class changes needed.

---

## 6. Test Patterns

### `tests/test_workflows.py`

**Existing patterns:**
- `workflow_func_mock()` context manager — temporarily swaps registry function with mock (L70–84)
- `TestRegistryMatchesStubs` class — validates registry structure (L31–62)
- `TestRunWorkflowDispatch` — tests dispatch with mocks
- `TestRunWorkflowTransforms` — tests `ParsedConfig` transform via `@patch`

**What Phase 21 adds:**
- `TestRegistrySelfCheck` — tests WFC-03 import-time validation:
  - Validates a correct registry entry (should not raise)
  - Validates an entry missing required from function signature (should raise `NautobotValidationError`)
  - Validates an entry with extra required param (not in function signature)
- `TestVerifyDataModelDispatch` — tests `verify_data_model` workflow dispatch with `parsed_config` transform

### `tests/test_exceptions.py`

**Existing patterns:**
- `test_validation_error()` (L49–58) — tests `NautobotValidationError` with `errors` list and `to_dict()` includes `validation_errors`
- `test_api_error_status_code()` (L61–69) — tests `NautobotAPIError.to_dict()` includes `status_code`

**What Phase 21 adds:**
- Test for `NautobotAPIError` with custom hint (verifies hint is preserved in `to_dict()`)
- Test for `NautobotValidationError` with field-level errors dict (verifies `validation_errors` key in `to_dict()`)

### `tests/test_client.py`

File does not exist — no existing API error handling tests.

**What Phase 21 adds:**
- `TestHandleApiError400` — mocks pynautobot `RequestError` with a 400 DRF response body; verifies `NautobotValidationError` includes parsed field errors
- `TestHandleApiErrorNonJson` — mocks 400 with non-JSON body; verifies graceful fallback
- `TestHandleApiErrorHintMap` — tests that specific endpoints get specific hints via `ERROR_HINTS`

**Mock strategy for `RequestError`:**

```python
class FakeResponse:
    status_code = 400
    text = '{"name": ["This field is required."], "device": ["Invalid pk"]}'
    url = "/api/dcim/devices/"
    reason = "Bad Request"
    def json(self):
        return json.loads(self.text)

fake_request_error = MagicMock()
fake_request_error.req = FakeResponse()
fake_request_error.__str__ = lambda self: "Validation error"

# Then call _handle_api_error(fake_request_error, "create", "Device")
```

---

## 7. File-by-File Change Summary

### `workflows.py`

| Change | Lines | Purpose |
|--------|-------|---------|
| Fix `required` for `verify_data_model` | L87 | WFC-01: add `"parsed_config"` |
| Add `transforms` for `verify_data_model` | L87–89 | WFC-02: add `ParsedConfig.model_validate` |
| Add `_validate_registry()` function | New | WFC-03: import-time signature check |
| Call `_validate_registry()` at module level | Bottom | WFC-03: run on import |
| Update `except Exception` in `run_workflow()` | L284–285 | ERR-03: composite exception → warning entry |

### `catalog/workflow_stubs.py`

| Change | Lines | Purpose |
|--------|-------|---------|
| Update `verify_data_model` `params` | L68 | WFC-03: add `parsed_config` to stubs |

### `client.py`

| Change | Lines | Purpose |
|--------|-------|---------|
| Add `ERROR_HINTS` dict | Near top | ERR-02: per-endpoint hint map |
| Add `STATUS_CODE_HINTS` dict | Near top | ERR-04: status-code fallback hints |
| Add `_get_hint_for_request()` helper | Near `_handle_api_error()` | ERR-02 + ERR-04 |
| Update `status_code == 400` branch | L152 | ERR-01: parse DRF body → `NautobotValidationError.errors` |
| Update `raise NautobotAPIError` call | L158 | ERR-04: apply hint from map |

### `tests/test_workflows.py`

| Addition | Class | Purpose |
|---------|-------|---------|
| `TestRegistrySelfCheck` | New | WFC-03 |
| `TestVerifyDataModelDispatch` | New | WFC-01 + WFC-02 |
| `TestRunWorkflowCompositeErrorOrigin` | New | ERR-03 |

### `tests/test_client.py` (new file)

| Test class | Purpose |
|-----------|---------|
| `TestHandleApiError400` | ERR-01: 400 body parsing |
| `TestHandleApiErrorNonJson` | ERR-01: graceful fallback |
| `TestErrorHintMap` | ERR-02 + ERR-04: hint enrichment |

### `tests/test_exceptions.py`

| Addition | Purpose |
|---------|---------|
| `test_validation_error_with_field_errors_to_dict` | ERR-01: field errors in `to_dict()` |
| `test_api_error_hint_preserved` | ERR-04: custom hint in `to_dict()` |

---

## 8. Potential Pitfalls & Edge Cases

### WFC-03: Self-check must not flag `client` param
The registry `param_map` only maps agent-facing params (not `client` — that's injected). The self-check must compare function params **minus** `client` against the union of `required` + `param_map` keys.

```python
# Extract function params excluding 'client' (always first positional arg)
func_params = set(inspect.signature(func).parameters.keys()) - {"client"}
```

### WFC-03: `param_map` can map agent_name → different func_name
The self-check compares agent-facing keys (the `param_map` keys, not values) against function params. `required` lists also use agent-facing names. So: `func_params ⊇ required ∪ set(param_map.keys())`.

### ERR-01: DRF returns nested non-field errors
Some DRF responses use `{"non_field_errors": ["..."]}` or `{"detail": "..."}`. The parser should handle both `list` and `str` message values:

```python
if isinstance(messages, str):
    field_errors.append({"field": field, "error": messages})
else:
    for msg in messages:
        field_errors.append({"field": field, "error": str(msg)})
```

### ERR-01: DRF detail as plain string (not dict)
Some 400 responses are `{"detail": "Invalid filter parameter"}` (string, not field dict). Handle gracefully — put it as a single `{"field": "_detail", "error": body}` entry.

### ERR-03: Composite vs. non-composite
Only composite workflows should get the exception→warning treatment. Simple workflows that raise should still get `status: "error"`. The self-check should identify composites (functions that return `(result, warnings)` tuple) vs. simples. Alternatively, hardcode which workflows are composite in the self-check.

**Simpler approach (D-07 aligned):** All exceptions caught at `run_workflow()` level are added as warnings to the envelope. The distinction between `status: "partial"` and `status: "error"` is already made by `_build_envelope()`: `error` field is `None` when there's data, non-None when there's no data. A composite exception caught and added to warnings, with no data, would produce `status: "error"` — correct.

### ERR-02: Hint map key collision
If two different endpoints share the same path prefix, the longest-match wins. Sort hint keys by length descending when looking up.

### ERR-04: `NautobotAPIError` raised without `hint`
If `_handle_api_error()` raises `NautobotAPIError` for an unknown status code and the hint lookup fails, use the status-code-based fallback. Never leave `hint` empty.

### Phase ordering constraint
WFC-01 and WFC-02 must be fixed before the WFC-03 self-check is added — otherwise the self-check will immediately fail on the current broken `verify_data_model` entry, blocking server startup. Test the self-check by temporarily introducing a mismatch in a test.

---

## 9. Dependency & Ordering Summary

```
Day 1 (WFC fixes):
  1. Fix workflows.py: add "parsed_config" to required + add transforms block
  2. Fix workflow_stubs.py: add parsed_config to verify_data_model params
  3. Add _validate_registry() + call at module level
  4. Add tests for WFC-01, WFC-02, WFC-03

Day 2 (ERR fixes):
  5. Add ERROR_HINTS + STATUS_CODE_HINTS + _get_hint_for_request() in client.py
  6. Update _handle_api_error() for 400 body parsing (ERR-01) + hint enrichment (ERR-02, ERR-04)
  7. Update run_workflow() except block for ERR-03
  8. Add tests for ERR-01, ERR-02, ERR-03, ERR-04
```

---

## 10. Key Source Code References

| File | Lines | What to read |
|------|-------|--------------|
| `nautobot_mcp/workflows.py` | 61–72 | `onboard_config` registry entry (working transform pattern) |
| `nautobot_mcp/workflows.py` | 81–88 | `verify_data_model` registry entry (bug: missing required + transforms) |
| `nautobot_mcp/workflows.py` | 146–196 | `_build_envelope()` (three-tier status, warnings field) |
| `nautobot_mcp/workflows.py` | 204–286 | `run_workflow()` dispatch + exception handler (ERR-03 target) |
| `nautobot_mcp/verification.py` | 200–204 | `verify_data_model()` function signature |
| `nautobot_mcp/client.py` | 119–170 | `_handle_api_error()` (ERR-01 + ERR-02 + ERR-04 target) |
| `nautobot_mcp/exceptions.py` | 78–95 | `NautobotValidationError` (already has `errors` field) |
| `nautobot_mcp/exceptions.py` | 98–114 | `NautobotAPIError` (hint, status_code) |
| `nautobot_mcp/catalog/workflow_stubs.py` | 67–71 | `verify_data_model` stub (WFC-01 target) |
| `nautobot_mcp/warnings.py` | 11–63 | `WarningCollector` (ERR-03 format reference) |
| `nautobot_mcp/models/parser.py` | 102–119 | `ParsedConfig` Pydantic model |
| `tests/test_workflows.py` | 70–84 | `workflow_func_mock()` pattern |
| `tests/test_workflows.py` | 31–62 | `TestRegistryMatchesStubs` pattern |
| `tests/test_exceptions.py` | 49–58 | `test_validation_error()` pattern |
