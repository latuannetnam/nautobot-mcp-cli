---
wave: 1
depends_on: []
files_modified:
  - nautobot_mcp/bridge.py
  - nautobot_mcp/exceptions.py
autonomous: true
---

# Phase 31 Plan: Bridge Param Guard

## Goal

Add `_guard_filter_params()` to `nautobot_mcp/bridge.py` to intercept oversized `__in` list values in filter params before they reach `pynautobot`'s `.filter()`, preventing 414 Request-URI Too Large errors from external callers who pass large UUID lists through the MCP bridge.

## Background

External callers (AI agents, MCP clients) can invoke `nautobot_call_nautobot` with `params` containing `__in`-suffixed keys whose values are lists of 1–10,000+ UUIDs. When pynautobot's `.filter()` receives a list, it serializes each item as a **repeated query parameter**: `?id__in=uuid1&id__in=uuid2&...`. A list of 1,000 UUIDs generates ~18 KB of query string → 414 at scale.

The guard intercepts these lists before `.filter()`, raising `NautobotValidationError` for oversized lists (> 500 items) and converting all `__in` lists ≤ 500 to DRF-native comma-separated strings (e.g., `?id__in=uuid1,uuid2,uuid3`).

---

## Tasks

### Wave 1: Implementation in bridge.py

---

<task>
<read_first>
- nautobot_mcp/bridge.py (the file being modified — lines 1–34 for imports, lines 150–235 for `_execute_core()`, lines 237–321 for `_execute_cms()`)
- nautobot_mcp/exceptions.py (for `NautobotValidationError` signature)
</read_first>

<action>
Add the following module-level helper function to `nautobot_mcp/bridge.py` after the existing helper functions (e.g., after `_parse_core_endpoint()`, before `_execute_core()`).

```python
def _guard_filter_params(params: dict | None) -> dict | None:
    """Guard __in-suffixed filter params against 414 Request-URI Too Large.

    - Raises NautobotValidationError if any __in param has > 500 items.
    - Converts all __in param lists ≤ 500 to comma-separated strings
      (DRF-native format ?key=val1,val2,val3) to reduce query string size.
    - Non-__in list params (e.g., tag=[...], status=[...]) pass through unchanged.

    Args:
        params: Filter params dict, or None.

    Returns:
        Guarded params dict with __in lists converted to strings, or None.

    Raises:
        NautobotValidationError: If any __in param value has > 500 items.
    """
    if not params:
        return None

    result = {}
    for key, value in params.items():
        if key.endswith("__in") and isinstance(value, (list, tuple)):
            if len(value) > 500:
                raise NautobotValidationError(
                    message=f"Parameter '{key}' has {len(value)} items — exceeds "
                            f"maximum of 500. Chunk your query and retry.",
                    hint="Split large 'in' queries into batches of ≤ 500 items. "
                         "E.g., fetch IDs in chunks and merge results.",
                )
            # Convert list to comma-separated string (DRF-native format)
            result[key] = ",".join(str(v) for v in value)
        else:
            result[key] = value
    return result
```

**Placement:** Insert this function at module level in `nautobot_mcp/bridge.py`, immediately before `_execute_core()` (line 150). The file currently has `_parse_core_endpoint()` ending around line 147; insert after line 147 (after its `return app_name, ep_name` line and before the blank line before `_execute_core`).
</action>

<acceptance_criteria>
- `grep -n "_guard_filter_params" nautobot_mcp/bridge.py` shows the new function definition at module level
- The function has docstring with Args/Returns/Raises sections
- `grep -n "endswith.*__in" nautobot_mcp/bridge.py` finds the guard condition inside `_guard_filter_params`
- `grep -n "NautobotValidationError" nautobot_mcp/bridge.py` shows `NautobotValidationError` imported from `nautobot_mcp.exceptions` at line 21 (already imported — no change needed)
- The function uses `",".join(str(v) for v in value)` for list-to-string conversion
</acceptance_criteria>
</task>

---

<task>
<read_first>
- nautobot_mcp/bridge.py (the file being modified — lines 150–235 for `_execute_core()`, specifically lines 186–192 where the filter() call is)
</read_first>

<action>
In `_execute_core()` (around line 186–192), add a call to `_guard_filter_params(params)` before the `if params:` check. The current code is:

```python
        # List operation — pass limit/offset server-side to avoid fetching all records
        if params:
            records = list(endpoint_accessor.filter(**params, **pagination_kwargs))
        else:
            records = list(endpoint_accessor.all(**pagination_kwargs))
```

Change it to:

```python
        # Guard __in params: raise for oversized lists, convert small lists to CSV
        params = _guard_filter_params(params)
        # List operation — pass limit/offset server-side to avoid fetching all records
        if params:
            records = list(endpoint_accessor.filter(**params, **pagination_kwargs))
        else:
            records = list(endpoint_accessor.all(**pagination_kwargs))
```

This replaces `if params:` with an assignment from `_guard_filter_params()` and keeps the existing `if params:` check as-is.
</action>

<acceptance_criteria>
- `grep -n "_guard_filter_params" nautobot_mcp/bridge.py` shows at least 2 occurrences: the function definition AND the call inside `_execute_core`
- `grep -n "_guard_filter_params" nautobot_mcp/bridge.py` shows the call appears after line 185 (inside `_execute_core`)
- The filter call at line 188 (`endpoint_accessor.filter(**params,`) still uses `params` as the variable passed to `.filter()` — the guard transforms the dict in place by rebinding the name
</acceptance_criteria>
</task>

---

<task>
<read_first>
- nautobot_mcp/bridge.py (the file being modified — lines 237–274 for `_execute_cms()`, specifically lines 241–270 where device resolution and the filter() call are)
</read_first>

<action>
In `_execute_cms()` (around lines 241–270), add a call to `_guard_filter_params()` after device resolution (line 245) and before the `if effective_params:` check (line 269). The current code structure is:

```python
    # Resolve device name to UUID if device param provided
    effective_params = dict(params) if params else {}
    if "device" in effective_params:
        device_val = effective_params["device"]
        effective_params["device"] = resolve_device_id(client, device_val)

    # Get CMS endpoint accessor
    endpoint_accessor = get_cms_endpoint(client, cms_key)

    # Build server-side pagination kwargs
    ...

    if method == "GET":
        ...
        if effective_params:
            records = list(endpoint_accessor.filter(**effective_params, **pagination_kwargs))
```

Change it to:

```python
    # Resolve device name to UUID if device param provided
    effective_params = dict(params) if params else {}
    if "device" in effective_params:
        device_val = effective_params["device"]
        effective_params["device"] = resolve_device_id(client, device_val)

    # Guard __in params: raise for oversized lists, convert small lists to CSV
    effective_params = _guard_filter_params(effective_params) or {}

    # Get CMS endpoint accessor
    endpoint_accessor = get_cms_endpoint(client, cms_key)
```

The `effective_params or {}` ensures that if `_guard_filter_params` returns `None` (when input was `None`/`{}`), the result is still a dict and `effective_params` stays truthy or falsy as expected. The existing `if effective_params:` check at line 269 handles the remaining logic correctly.
</action>

<acceptance_criteria>
- `grep -n "_guard_filter_params" nautobot_mcp/bridge.py` shows 3 occurrences total: function definition, call in `_execute_core`, call in `_execute_cms`
- The CMS call uses `effective_params = _guard_filter_params(effective_params) or {}` — the `or {}` fallback is present
- `grep -n "effective_params.*_guard_filter_params" nautobot_mcp/bridge.py` confirms the assignment is present
- The guard call appears after `effective_params["device"] = resolve_device_id(...)` (device resolution) and before `endpoint_accessor = get_cms_endpoint(...)`
</acceptance_criteria>
</task>

---

### Wave 2: Unit Tests in tests/test_bridge.py

---

<task>
<read_first>
- tests/test_bridge.py (the file being modified — lines 1–25 for imports, lines 586+ for where to add new test classes)
- nautobot_mcp/bridge.py (to verify `_guard_filter_params` is in the imports after implementation)
</read_first>

<action>
**Step 1 — Update imports in `tests/test_bridge.py`:**

In the `from nautobot_mcp.bridge import (...)` block (lines 10–20), add `_guard_filter_params`, `_execute_core`, and `_execute_cms` to the imports. The import block currently ends at line 20 with `DEFAULT_LIMIT,`. Change it to:

```python
from nautobot_mcp.bridge import (
    call_nautobot,
    _validate_endpoint,
    _suggest_endpoint,
    _parse_core_endpoint,
    _validate_method,
    _build_valid_endpoints,
    _strip_uuid_from_endpoint,
    _guard_filter_params,
    _execute_core,
    _execute_cms,
    MAX_LIMIT,
    DEFAULT_LIMIT,
)
```

**Step 2 — Add `TestParamGuard` class at end of file:**

After line 586 (end of `TestCallNautobotWithUUID`), add the following test classes:

```python


class TestParamGuard:
    """Test _guard_filter_params() guard logic."""

    def test_none_params_returns_none(self):
        """None input returns None (passthrough)."""
        assert _guard_filter_params(None) is None

    def test_empty_dict_returns_empty_dict(self):
        """Empty dict returns empty dict."""
        assert _guard_filter_params({}) == {}

    # --- Small list (≤ 500): converted to comma-separated string ---

    def test_id_in_small_list_converted_to_string(self):
        """Small __in list is converted to comma-separated string."""
        params = {"id__in": ["uuid1", "uuid2", "uuid3"]}
        guarded = _guard_filter_params(params)
        assert guarded == {"id__in": "uuid1,uuid2,uuid3"}

    def test_interface_in_small_list_converted(self):
        """interface__in list converted."""
        params = {"interface__in": ["iface1", "iface2"]}
        guarded = _guard_filter_params(params)
        assert guarded == {"interface__in": "iface1,iface2"}

    def test_exactly_500_items_converted(self):
        """Exactly 500 items is allowed and converted."""
        items = [f"uuid-{i}" for i in range(500)]
        params = {"id__in": items}
        guarded = _guard_filter_params(params)
        assert len(guarded["id__in"].split(",")) == 500
        assert isinstance(guarded["id__in"], str)

    def test_mixed_in_and_regular_params(self):
        """Mixed __in and non-__in params: __in converted, others passed through."""
        params = {"id__in": ["a", "b"], "status": "active", "name": "router1"}
        guarded = _guard_filter_params(params)
        assert guarded == {"id__in": "a,b", "status": "active", "name": "router1"}

    # --- Large list (> 500): raises NautobotValidationError ---

    def test_id_in_501_items_raises(self):
        """501 items in id__in raises NautobotValidationError."""
        params = {"id__in": [f"uuid-{i}" for i in range(501)]}
        with pytest.raises(NautobotValidationError, match="id__in.*501.*500"):
            _guard_filter_params(params)

    def test_interface_in_600_items_raises(self):
        """600 items in interface__in raises."""
        params = {"interface__in": [f"iface-{i}" for i in range(600)]}
        with pytest.raises(NautobotValidationError, match="interface__in.*600"):
            _guard_filter_params(params)

    def test_error_message_includes_param_key(self):
        """Error message names the offending parameter key."""
        params = {"custom__in": [f"val-{i}" for i in range(600)]}
        with pytest.raises(NautobotValidationError, match="custom__in"):
            _guard_filter_params(params)

    def test_error_message_includes_count(self):
        """Error message includes the actual item count."""
        params = {"id__in": [f"uuid-{i}" for i in range(750)]}
        with pytest.raises(NautobotValidationError, match="750"):
            _guard_filter_params(params)

    # --- Non-__in list params: pass through unchanged ---

    def test_tag_list_passed_through_unchanged(self):
        """Non-__in list params pass through as-is (list objects)."""
        params = {"tag": ["foo", "bar", "baz"]}
        guarded = _guard_filter_params(params)
        assert guarded == {"tag": ["foo", "bar", "baz"]}  # list unchanged

    def test_status_list_passed_through_unchanged(self):
        """status=[active, planned] passed through unchanged."""
        params = {"status": ["active", "planned"]}
        guarded = _guard_filter_params(params)
        assert guarded == {"status": ["active", "planned"]}

    def test_location_list_passed_through_unchanged(self):
        """location=[uuid1, uuid2] passed through unchanged (no __in suffix)."""
        params = {"location": ["loc-uuid-1", "loc-uuid-2"]}
        guarded = _guard_filter_params(params)
        assert guarded == {"location": ["loc-uuid-1", "loc-uuid-2"]}

    def test_non_list_params_passed_through(self):
        """Scalar params pass through unchanged."""
        params = {"name": "router1", "status": "active", "limit": 50}
        guarded = _guard_filter_params(params)
        assert guarded == {"name": "router1", "status": "active", "limit": 50}

    def test_tuple_converted_to_string(self):
        """Tuple __in value is converted to string (same as list)."""
        params = {"id__in": ("uuid-1", "uuid-2")}
        guarded = _guard_filter_params(params)
        assert guarded == {"id__in": "uuid-1,uuid-2"}


class TestParamGuardIntegration:
    """Test _execute_core() and _execute_cms() raise for oversized __in lists."""

    def _mock_client_core(self):
        """Set up mock for _execute_core path."""
        client = MagicMock()
        endpoint = MagicMock()
        endpoint.filter.return_value = []
        app = MagicMock()
        setattr(app, "devices", endpoint)
        client.api.dcim = app
        return client, endpoint

    def test_execute_core_large_id_in_raises(self):
        """_execute_core raises when params contains id__in > 500 items."""
        client, _ = self._mock_client_core()
        params = {"id__in": [f"uuid-{i}" for i in range(600)]}
        with pytest.raises(NautobotValidationError, match="id__in.*600.*500"):
            _execute_core(client, "dcim", "devices", "GET", params, None, None, 50)

    def test_execute_core_small_id_in_works(self):
        """_execute_core works when id__in ≤ 500 (converted to string)."""
        client, endpoint = self._mock_client_core()
        params = {"id__in": ["uuid-1", "uuid-2", "uuid-3"]}
        _execute_core(client, "dcim", "devices", "GET", params, None, None, 50)
        # pynautobot accepts string for __in — verify filter called with CSV string
        call_kwargs = endpoint.filter.call_args
        assert call_kwargs[1]["id__in"] == "uuid-1,uuid-2,uuid-3"

    def test_execute_core_non_in_list_unchanged(self):
        """_execute_core passes non-__in list params through unchanged."""
        client, endpoint = self._mock_client_core()
        params = {"tag": ["foo", "bar"]}
        _execute_core(client, "dcim", "devices", "GET", params, None, None, 50)
        # tag=[...] stays as a list; filter call does not crash
        call_kwargs = endpoint.filter.call_args
        assert call_kwargs[1]["tag"] == ["foo", "bar"]

    def test_execute_cms_large_interface_in_raises(self):
        """_execute_cms raises when params contains interface__in > 500 items."""
        client = MagicMock()
        mock_endpoint = MagicMock()
        mock_endpoint.filter.return_value = []
        with patch("nautobot_mcp.bridge.get_cms_endpoint", return_value=mock_endpoint):
            params = {"interface__in": [f"iface-{i}" for i in range(501)]}
            with pytest.raises(NautobotValidationError, match="interface__in.*501.*500"):
                _execute_cms(client, "juniper_static_routes", "GET", params, None, None, 50)

    def test_execute_cms_small_in_works(self):
        """_execute_cms works when __in ≤ 500 (converted to string)."""
        client = MagicMock()
        mock_endpoint = MagicMock()
        mock_endpoint.filter.return_value = []
        with patch("nautobot_mcp.bridge.get_cms_endpoint", return_value=mock_endpoint):
            params = {"id__in": ["uuid-1", "uuid-2"]}
            _execute_cms(client, "juniper_static_routes", "GET", params, None, None, 50)
            call_kwargs = mock_endpoint.filter.call_args
            assert call_kwargs[1]["id__in"] == "uuid-1,uuid-2"
```
</action>

<acceptance_criteria>
- `grep -n "_guard_filter_params" tests/test_bridge.py` shows the import AND at least 10 test function references
- `grep -n "class TestParamGuard" tests/test_bridge.py` shows two classes: `TestParamGuard` and `TestParamGuardIntegration`
- `grep -n "501.*raises\|600.*raises" tests/test_bridge.py` finds at least 2 test cases that expect `NautobotValidationError`
- `grep -n "tag.*foo.*bar\|status.*active.*planned" tests/test_bridge.py` finds at least 2 test cases that verify non-`__in` lists pass through unchanged
- `grep -n "_execute_core\|_execute_cms" tests/test_bridge.py` shows `_execute_core` and `_execute_cms` imported and used in `TestParamGuardIntegration`
</acceptance_criteria>
</task>

---

## Verification

Run the test suite to confirm all tests pass (including the new ones) and no regressions:

```bash
# Run param guard tests only
uv run pytest tests/test_bridge.py::TestParamGuard -v
uv run pytest tests/test_bridge.py::TestParamGuardIntegration -v

# Full test suite — must all pass (TEST-01)
uv run pytest tests/test_bridge.py -v
```

Expected output:
- `TestParamGuard`: 13 passed (13 test methods)
- `TestParamGuardIntegration`: 5 passed (5 test methods)
- All existing tests: still pass (no regression)

---

## must_haves

These are the verifiable conditions that prove the phase goal was achieved:

1. `nautobot_mcp/bridge.py` contains `_guard_filter_params()` function at module level
2. `_execute_core()` calls `_guard_filter_params(params)` before `endpoint_accessor.filter(**params, ...)`
3. `_execute_cms()` calls `_guard_filter_params(effective_params) or {}` after device resolution, before `endpoint_accessor.filter(**effective_params, ...)`
4. `NautobotValidationError` is raised when `len(value) > 500` for any `__in`-suffixed key
5. `__in` lists ≤ 500 are converted to comma-separated strings: `["uuid1","uuid2"]` → `"uuid1,uuid2"`
6. Non-`__in` list params (e.g., `tag=["foo","bar"]`) pass through unchanged
7. `tests/test_bridge.py` has `TestParamGuard` (unit tests for the helper) and `TestParamGuardIntegration` (integration tests for both `_execute_*` paths)
8. All 18 new tests pass
9. All existing tests in `tests/test_bridge.py` continue to pass (no regression)
10. `grep -c "_guard_filter_params" nautobot_mcp/bridge.py` returns `3` (1 definition + 2 call sites)
