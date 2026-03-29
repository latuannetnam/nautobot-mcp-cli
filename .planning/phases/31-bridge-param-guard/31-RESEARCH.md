# Phase 31: Bridge Param Guard — Research

**Phase:** 31-bridge-param-guard
**Date:** 2026-03-29
**Status:** Research complete

---

## 1. What Problem Are We Solving?

**Root cause:** External callers (AI agents, MCP clients) can pass `params` with `__in`-suffixed keys whose values are lists of 1–10,000+ UUIDs. When `bridge.py`'s `_execute_core()` or `_execute_cms()` passes these to `endpoint_accessor.filter(**params)`, pynautobot serializes each list item as a **repeated query parameter**: `?id__in=uuid1&id__in=uuid2&...`. A list of 1,000 UUIDs generates ~18 KB of query string, and at ~5,000 items the URI hits common web server limits → **414 Request-URI Too Large**.

The fix: intercept `__in`-suffixed param values before they reach `.filter()`, raise for oversized lists, and convert smaller lists to DRF-native comma-separated strings (e.g., `?id__in=uuid1,uuid2,uuid3`).

---

## 2. Requirements to Implement

From `.planning/REQUIREMENTS.md` §"Bridge Param Guard (BRIDGE)":

| ID | Requirement | Implementation note |
|----|-------------|--------------------|
| BRIDGE-01 | `_execute_core()` raises `NautobotValidationError` when any `__in` param has > 500 items | Guard placed before `endpoint_accessor.filter()` at L188 |
| BRIDGE-02 | `_execute_cms()` raises `NautobotValidationError` for the same condition | Guard placed before `endpoint_accessor.filter()` at L270 |
| BRIDGE-03 | Lists ≤ 500 in `__in` params are converted to comma-separated strings before `.filter()` | `",".join(items)` on the value |
| BRIDGE-04 | Non-`__in` list params (`tag=[foo, bar]`) pass through unchanged | Only keys ending with `__in` are transformed |
| BRIDGE-05 | Unit tests cover: small list works, large list raises, non-`__in` lists pass through | New `TestParamGuard` class in `tests/test_bridge.py` |

From `.planning/REQUIREMENTS.md` §"Regression (TEST)":

| ID | Requirement | Implementation note |
|----|-------------|--------------------|
| TEST-01 | All existing unit tests pass after changes — no behavioral regression | Guard must not break existing `filter()` call patterns |

---

## 3. User Decisions (from 31-CONTEXT.md)

| Decision | Selected | Rationale |
|----------|----------|-----------|
| Error behavior | **Raise `NautobotValidationError`** | Fast-fail; consistent with bridge error model |
| Comma-separation strategy | **Convert ALL `__in` lists ≤ 500** to comma-separated strings | DRF-native; proactively eliminates 414 risk for mid-size lists; matches BRIDGE-03 |
| Guard scope | **ALL `__in`-suffixed keys** | Generic pattern — `id__in`, `interface__in`, `device__in`, `vlan__in`, etc. Future-proof |
| Non-`__in` list params | **Pass through unchanged** | Small (1–5 items), not 414 sources |

---

## 4. Source Code Analysis

### 4.1 Where `.filter()` is called in bridge.py

**`_execute_core()` — L187–188:**
```python
# L187-188
if params:
    records = list(endpoint_accessor.filter(**params, **pagination_kwargs))
```

**`_execute_cms()` — L269–270:**
```python
# L269-270
if effective_params:
    records = list(endpoint_accessor.filter(**effective_params, **pagination_kwargs))
```

The guard must be applied **before** these calls, on the `params` / `effective_params` dicts.

### 4.2 `_execute_core()` params flow

```
call_nautobot(params=...)
    → _execute_core(params, ...)
        → L187: if params:   ← params is the original dict
        → L188: filter(**params, **pagination_kwargs)
```

The guard should be called just before the `if params:` check, producing a guarded version of `params`.

### 4.3 `_execute_cms()` params flow

```
call_nautobot(params=...)
    → _execute_cms(params, ...)
        → L242: effective_params = dict(params) if params else {}
        → L243-245: resolve "device" in effective_params
        → L269: if effective_params:
        → L270: filter(**effective_params, **pagination_kwargs)
```

Guard must be applied **after** device resolution (L242-245) but **before** the `filter()` call (L270).

### 4.4 `NautobotValidationError` signature

From `nautobot_mcp/exceptions.py` L78–88:
```python
class NautobotValidationError(NautobotMCPError):
    def __init__(
        self,
        message: str = "Validation failed",
        hint: str = "Check required fields and data formats",
        errors: Optional[list[dict]] = None,
    ) -> None:
        super().__init__(message=message, code="VALIDATION_ERROR", hint=hint)
        self.errors = errors or []
```

Usage pattern in bridge.py (e.g., L80–84, L111–114):
```python
raise NautobotValidationError(
    message=f"Unknown endpoint: '{endpoint}'",
    hint="Use nautobot_api_catalog() to see available endpoints",
)
```

### 4.5 Existing module-level helpers in bridge.py

Pattern to follow for `_guard_filter_params()`:
```python
# Pattern (from _validate_endpoint, _parse_core_endpoint, etc.):
# - Module-level function
# - Takes params dict as input
# - Returns transformed dict OR raises
# - Called from both _execute_core and _execute_cms
```

---

## 5. Design: `_guard_filter_params()`

### 5.1 Signature

```python
def _guard_filter_params(params: dict | None) -> dict | None:
    """Guard __in-suffixed filter params against 414 Request-URI Too Large.

    - Raises NautobotValidationError if any __in param has > 500 items.
    - Converts all __in param lists ≤ 500 to comma-separated strings
      (DRF-native format ?key=val1,val2,val3) to reduce query string size.
    - Non-__in list params pass through unchanged.

    Args:
        params: Filter params dict, or None.

    Returns:
        Guarded params dict with __in lists converted to strings, or None.

    Raises:
        NautobotValidationError: If any __in param value has > 500 items.
    """
```

### 5.2 Implementation details

**Step 1 — Fast path for None:**
```python
if not params:
    return None
```

**Step 2 — Iterate and guard:**
```python
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

**Step 3 — Integration in `_execute_core()` (before L187):**
```python
# L187 — replace:
if params:
# with:
params = _guard_filter_params(params)
if params:
```

**Step 4 — Integration in `_execute_cms()` (before L269):**
```python
# L269 — effective_params already has device resolved.
# Apply guard after resolution:
# (existing code at L242-245 stays)
effective_params = dict(params) if params else {}
if "device" in effective_params:
    effective_params["device"] = resolve_device_id(client, effective_params["device"])

# ADD: guard __in params (after device resolution, before filter)
effective_params = _guard_filter_params(effective_params) or {}

# L269 — no change needed if _guard_filter_params returns dict
if effective_params:
    records = list(endpoint_accessor.filter(**effective_params, **pagination_kwargs))
```

### 5.3 Key decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| `__in` detection | `key.endswith("__in")` | Simple, matches all DRF lookup expressions: `id__in`, `name__in`, `device__in`, `interface__in`, `vlan__in`, etc. |
| Type check | `isinstance(value, (list, tuple))` | Handles both list and tuple inputs defensively |
| `> 500` not `>= 500` | `> 500` | Exactly 500 items is fine; 501 raises |
| String conversion | `",".join(str(v) for v in value)` | `str()` handles UUIDs (already strings) and any other serializable values |
| Return `None` for empty | `return None` | Preserves existing `if params:` check semantics |
| Guard after device resolution | CMS path | Device UUID resolution happens before guard; `device__in` would also be guarded if passed |

### 5.4 Why `endswith("__in")` is safe

pynautobot's `.filter()` accepts Django REST Framework (DRF) lookup expressions. The `__in` suffix is the only list-valued filter expression that generates repeated query params. Other list params (e.g., `tag=[...]`) are single-value CSV or handled differently by DRF. The `__in` suffix is unambiguous — no false positives.

### 5.5 Comma-separated format compatibility

Nautobot's DRF-based API accepts both repeated params (`?id__in=a&id__in=b`) and comma-separated (`?id__in=a,b`) for `__in` lookups. Phase 30's `_bulk_get_by_ids()` in `ipam.py` already confirmed this works (L46: `{id_param: ",".join(ids)}`). pynautobot's internal HTTP layer will pass the string value directly as a single query parameter.

---

## 6. Test Plan (BRIDGE-05 / TEST-01)

### 6.1 New test class: `TestParamGuard`

Add to `tests/test_bridge.py`. Imports needed:
```python
from nautobot_mcp.bridge import _guard_filter_params, _execute_core, _execute_cms
```

### 6.2 Test cases for `_guard_filter_params()`

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
```

### 6.3 Integration tests: guard in `_execute_core()` and `_execute_cms()`

```python
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
        # pynautobot accepts string for __in — verify filter called
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

### 6.4 Test execution

```bash
# Run only param guard tests
uv run pytest tests/test_bridge.py::TestParamGuard -v
uv run pytest tests/test_bridge.py::TestParamGuardIntegration -v

# Full test suite (must all pass — TEST-01)
uv run pytest tests/test_bridge.py -v
```

---

## 7. Files to Change

| File | Change |
|------|--------|
| `nautobot_mcp/bridge.py` | Add `_guard_filter_params()` helper; call it in `_execute_core()` (before L188) and `_execute_cms()` (after device resolution, before L270) |
| `tests/test_bridge.py` | Add `TestParamGuard` and `TestParamGuardIntegration` classes; update imports |

**No changes needed to:** `server.py`, `workflows.py`, `client.py`, `exceptions.py`

---

## 8. Compliance Checklist

| Req | What's needed |
|-----|---------------|
| BRIDGE-01 | `_execute_core()` has guard → raises for > 500 |
| BRIDGE-02 | `_execute_cms()` has guard → raises for > 500 |
| BRIDGE-03 | Lists ≤ 500 → `",".join(...)` before `.filter()` |
| BRIDGE-04 | Non-`__in` lists → pass through unchanged |
| BRIDGE-05 | Unit tests: small works, large raises, non-`__in` pass through ✓ (section 6 above) |
| TEST-01 | All existing tests pass — guard is additive, no behavioral change to existing paths |

---

## 9. Open Questions / Risks

| Question | Assessment | Resolution |
|----------|-----------|------------|
| Does pynautobot's `.filter()` accept a string for `__in`? | **Yes** — pynautobot passes kwargs to requests; a string `id__in="uuid1,uuid2"` becomes `?id__in=uuid1,uuid2`. Phase 30's `_bulk_get_by_ids()` confirmed this works with direct HTTP. | Trust this — same pynautobot codepath |
| What if `__in` value is a list of non-string items? | Defensive: `str(v) for v in value` handles ints, UUIDs, etc. | Safe |
| Does the CMS path's device resolution affect `__in` guard? | No — device resolution operates on `effective_params["device"]` (singular scalar). `device__in` (plural) would be a separate key and would also be guarded if present. | Not a conflict |
| Does `__in` guard apply to `call_nautobot()` level or only `_execute_*`? | Only `_execute_*` level. `call_nautobot()` is the public API; it passes params directly to `_execute_*`. Guard at the execution layer covers both internal and external callers. | Correct placement |

---

## 10. Deferred (Future Phases)

- Extending guard to `__iexact`, `__icontains`, or other large-result filter suffixes
- CLI-level warning when a bridge call hits the guard (visibility without crashing)
- Applying the same guard to `list_vlans()` in `ipam.py` (Phase 30 noted this as a future consideration)

---

*Research complete — ready for planning.*
