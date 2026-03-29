# Phase 32: VLANs 500 Fix + Regression Tests — Research

**Phase:** 32-vlans-500-fix-regression-tests
**Date:** 2026-03-29
**Status:** Research complete — ready to plan

---

## 1. Root Cause: VLANViewSet Queryset Analysis

### Why `location=<name>` Causes 500

Nautobot's `VLANViewSet` uses an **annotated queryset** for both list and count operations:

```python
# Nautobot internal (simplified)
class VLANViewSet(ModelViewSet):
    def get_queryset(self):
        return super().get_queryset().annotate(
            prefix_count=Count("prefixes", distinct=True),
            # ... other annotations
        )
```

The queryset is shared between `GET /api/ipam/vlans/` and `GET /api/ipam/vlans/count/`. When the filter `location=HQV` (name string) is applied:

1. Nautobot's `TreeNodeMultipleChoiceFilter` must resolve `"HQV"` → `Location` object(s) for the ManyToMany `locations` field
2. This triggers a JOIN across the ManyToMany `vlans.locations` junction table
3. Combined with the annotation's `COUNT(DISTINCT ...)` on related `prefixes`, the ORM query planner crashes
4. Result: **HTTP 500 Internal Server Error**

### Why `location=<uuid>` Fixes It

When `location=<uuid>` (the UUID string) is passed:

- Nautobot filters directly on `vlans.locations_id = <uuid>` — a simple FK comparison on the junction table
- No name→object resolution required
- No ManyToMany JOIN amplification with the annotated `Count`
- The query is: `WHERE vlans_locations.location_id = '5555-6666-8888'` → succeeds

### Why UUID Is Available at Call Sites

`get_device()` returns a `DeviceSummary` Pydantic model populated by `DeviceSummary.from_nautobot()` at `models/device.py` L58-69. The device object fetched from Nautobot carries `device.location.id` (UUID string) and `device.location.name` (display name). Both are available without any extra API call — the device was already fetched in the preceding step.

**Key conclusion:** Call sites in `devices.py` already have `device.location.id` available. No extra HTTP call is needed. Resolution is free.

---

## 2. count() Method Analysis

### Current Behavior (client.py L343-383)

```python
def count(self, app: str, endpoint: str, **filters) -> int:
    url = f"{self._profile.url}/api/{app}/{endpoint}/count/"
    try:
        resp = self.api.http_session.get(url, params=filters)
        if resp.ok:
            return resp.json()["count"]
        if resp.status_code == 404:
            pass  # → fallback
        else:
            resp.raise_for_status()  # raises HTTPError for 5xx
    except requests.exceptions.HTTPError:
        pass  # swallow → fallback

    # Fallback: pynautobot O(n) .count()
    app_obj = getattr(self.api, app)
    ep_obj = getattr(app_obj, endpoint)
    return ep_obj.count(**filters)  # may also raise NautobotAPIError
```

### Error Propagation Chain for VLANs 500

```
client.count("ipam", "vlans", location="HQV")   # ← name, triggers 500
  └─ direct HTTP GET /api/ipam/vlans/count/?location=HQV
       └─ HTTP 500
            └─ resp.raise_for_status() → requests.exceptions.HTTPError
                 └─ caught by except: pass
                      └─ pynautobot .count(location="HQV")
                           └─ pynautobot RequestError(500)
                                └─ _handle_api_error()
                                     └─ NautobotAPIError(status_code=500)
```

**What changes:** None in `count()` itself. Per D-03 from 32-CONTEXT: `count()` propagates 500 as `NautobotAPIError` — it is the caller's responsibility to catch it.

### With UUID Fix

```
client.count("ipam", "vlans", location="5555-6666-8888")   # ← UUID
  └─ direct HTTP GET /api/ipam/vlans/count/?location=5555-6666-8888
       └─ HTTP 200 → returns count integer  ✓
```

---

## 3. All Call Sites Requiring Change

### devices.py — get_device_summary() L254-256

```python
# BEFORE (name → 500 on prod)
device_location = device.location.name if device.location else None
vlan_count = client.count("ipam", "vlans", location=device_location) if device_location else 0

# AFTER (UUID → 200)
device_location_id = device.location.id if device.location else None
try:
    vlan_count = client.count("ipam", "vlans", location=device_location_id) if device_location_id else 0
except NautobotAPIError:
    vlan_count = None
    # append warning
```

**File:** `nautobot_mcp/devices.py`
**Lines:** 254-256 (current), return at 258-263

### devices.py — get_device_inventory() Sequential "vlans" branch L340-342

```python
# BEFORE
elif detail == "vlans":
    t_vlans = time.time()
    loc_name = device_obj.location.name if device_obj.location else None
    total_vlans = client.count("ipam", "vlans", location=loc_name) if loc_name else 0
    vlans_latency_ms = (time.time() - t_vlans) * 1000

# AFTER: use UUID + try/except
```

**File:** `nautobot_mcp/devices.py`
**Lines:** 338-342

### devices.py — get_device_inventory() Parallel block L346-349

```python
# BEFORE (inside ThreadPoolExecutor)
def _count_vlans_by_loc(client_: NautobotClient, loc: str | None) -> int:
    if loc:
        return client_.count("ipam", "vlans", location=loc)
    return 0

# AFTER: resolve UUID before passing to thread
def _count_vlans_by_loc(client_: NautobotClient, loc_id: str | None) -> int | None:
    if loc_id:
        try:
            return client_.count("ipam", "vlans", location=loc_id)
        except NautobotAPIError:
            return None
    return 0
```

**File:** `nautobot_mcp/devices.py`
**Lines:** 346-349 (parallel block), 351-365 (result collection), 371-383 (sequential fallback)

### devices.py — Sequential Fallback L380-383

```python
# BEFORE
t_vlans = time.time()
loc_name = device_obj.location.name if device_obj.location else None
total_vlans = client.count("ipam", "vlans", location=loc_name) if loc_name else 0
vlans_latency_ms = (time.time() - t_vlans) * 1000

# AFTER: same UUID + try/except pattern
```

**File:** `nautobot_mcp/devices.py`
**Lines:** 380-383

---

## 4. Response Models — warnings Field

### DeviceStatsResponse (models/device.py L72-80)

```python
# BEFORE
class DeviceStatsResponse(BaseModel):
    device: DeviceSummary
    interface_count: int = Field(default=0)
    ip_count: int = Field(default=0)
    vlan_count: int = Field(default=0)
    enabled_count: int = Field(default=0)
    disabled_count: int = Field(default=0)

# AFTER: add warnings field, change vlan_count to Optional[int]
class DeviceStatsResponse(BaseModel):
    device: DeviceSummary
    interface_count: int = Field(default=0)
    ip_count: int = Field(default=0)
    vlan_count: Optional[int] = Field(default=None,
        description="Total VLAN count (null if unavailable due to server error)")
    enabled_count: int = Field(default=0)
    disabled_count: int = Field(default=0)
    warnings: Optional[list[dict[str, str]]] = Field(default=None,
        description="Recoverable error warnings from data fetch")
```

**File:** `nautobot_mcp/models/device.py`
**Lines:** 72-80 (add ~6 lines)

### DeviceInventoryResponse (models/device.py L83-121)

```python
# total_vlans already Optional[int] at L101 — just add warnings
# BEFORE: existing fields end at L120
    has_more: bool = Field(default=False)
# AFTER: add warnings after has_more
    has_more: bool = Field(default=False)
    warnings: Optional[list[dict[str, str]]] = Field(default=None)
```

**File:** `nautobot_mcp/models/device.py`
**Lines:** ~121 (append 3 lines)

### Warning Dict Structure

Consistent with Phase 31 D-05 and `WarningCollector` in `warnings.py` L29-46, but with different field names per the 32-CONTEXT D-05 design:

```python
{
    "section": "vlans",
    "message": "VLAN count unavailable: HTTP 500 — check Nautobot service health",
    "recoverable": True,
}
```

The `WarningCollector` in `workflows.py` uses `{"operation": ..., "error": ...}` which is for child-call-level granularity. The response-level `warnings` field uses `{"section": ..., "message": ..., "recoverable": ...}` for top-level section failures. The two are compatible because `WarningCollector` is used inside workflow functions, while the `warnings` field is at the response model level.

---

## 5. CLI Null/N/A Display

### devices_inventory (cli/devices.py L173-175) — Already Handles null

```python
# Current code already uses "?" for None:
iface_total = data['total_interfaces'] if data['total_interfaces'] is not None else "?"
ips_total   = data['total_ips']        if data['total_ips']        is not None else "?"
vlans_total = data['total_vlans']      if data['total_vlans']      is not None else "?"
```

**No change needed** — `vlans_total` will be `"?"` when `total_vlans=None`. Consistent with existing pattern.

### devices_summary (cli/devices.py L138-140) — Needs Fix

```python
# Current code — crashes if vlan_count is None:
typer.echo(f"  Interfaces: {data['interface_count']}")
typer.echo(f"  IP Addresses: {data['ip_count']}")
typer.echo(f"  VLANs: {data['vlan_count']}")  # ← crashes: "VLANs: None"
```

**Fix:** Apply the same null guard pattern:

```python
# AFTER
vlan_val = data['vlan_count'] if data['vlan_count'] is not None else "N/A"
typer.echo(f"  Interfaces: {data['interface_count']}")
typer.echo(f"  IP Addresses: {data['ip_count']}")
typer.echo(f"  VLANs: {vlan_val}")
```

**File:** `nautobot_mcp/cli/devices.py`
**Lines:** 138-140

### JSON Output

`json.dumps(data, indent=2)` naturally serializes `None` as `null` — no code change needed.

---

## 6. Test Patterns from Phase 31

### test_client.py — TestVLANCount500

Following the established pattern from `TestHandleApiError400` (test_client.py L121-214) and `TestParamGuard` (test_bridge.py L592-688):

```python
class TestVLANCount500:
    """Test count() behavior with UUID location filter and 500 error path."""

    def test_count_vlans_by_uuid_returns_int(self):
        """location=<uuid> produces a valid count integer."""
        # Mock http_session.get returning 200 with count=42
        ...

    def test_count_vlans_500_raises_nautobot_api_error(self):
        """500 from /count/ propagates as NautobotAPIError."""
        # Mock http_session.get returning 500
        # Mock pynautobot fallback also returning 500/RequestError
        # Assert NautobotAPIError raised
        ...

    def test_count_vlans_fallback_404_returns_pynautobot_count(self):
        """404 from /count/ falls back to pynautobot .count()."""
        ...
```

**File:** `tests/test_client.py`
**Location:** Append after existing `TestHandleApiErrorHintMap` (L222-294)

### test_devices.py — New File (following test_ipam.py as template)

```python
"""Tests for devices.py — VLAN count error handling and warnings."""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from nautobot_mcp.devices import get_device_summary, get_device_inventory
from nautobot_mcp.exceptions import NautobotAPIError
from nautobot_mcp.models.device import DeviceStatsResponse, DeviceInventoryResponse


class TestVLANCountErrorHandling:
    """Test that VLAN count failures are handled gracefully."""

    def test_get_device_summary_catches_vlan_count_500(self):
        """VLAN 500 → total_vlans=None, warning appended."""
        # Mock device with location.id
        # Mock count() raising NautobotAPIError for VLANs only
        # Assert vlan_count is None
        # Assert warnings is not None and contains vlans warning

    def test_get_device_inventory_catches_vlan_count_500(self):
        """VLAN 500 in sequential vlans branch → total_vlans=None."""
        ...

    def test_get_device_inventory_parallel_catches_vlan_count_500(self):
        """VLAN 500 in parallel block → total_vlans=None."""
        ...

    def test_get_device_inventory_fallback_catches_vlan_count_500(self):
        """VLAN 500 in sequential fallback → total_vlans=None."""
        ...

    def test_null_vlan_count_serializes_to_null_in_json(self):
        """vlan_count=None → 'null' in JSON, not crash."""
        ...

    def test_warning_dict_structure(self):
        """Warning dict has section, message, recoverable fields."""
        ...

    def test_vlan_count_by_uuid_not_500(self):
        """count() called with UUID (not name) — 200 response expected."""
        ...
```

**File:** `tests/test_devices.py` (new)
**Inherits fixtures from:** `tests/conftest.py` (`mock_device_record` has `location.id` and `location.name`)

### Test Fixtures Needed

The `mock_device_record` fixture in `conftest.py` L37-75 already provides:
- `device.location.id = "5555-6666-7777-8888"` — UUID for location
- `device.location.name = "SGN-DC1"` — name string

This is sufficient for all device-level tests. No new fixtures needed.

### Mocking Pattern for count() 500

```python
def test_get_device_summary_catches_vlan_count_500(self):
    from nautobot_mcp.exceptions import NautobotAPIError

    # Set up: count raises for VLANs only
    mock_client = MagicMock()
    mock_client.api.dcim.devices.get.return_value = mock_device_record  # has location.id
    mock_client.api.dcim.interfaces.count.return_value = 24
    mock_client.api.ipam.ip_addresses.count.return_value = 100
    mock_client.api.ipam.vlans.count.side_effect = NautobotAPIError(
        "API error during count on VLAN: HTTP 500",
        status_code=500,
    )

    # Act
    result = get_device_summary(mock_client, name="core-rtr-01")

    # Assert
    assert result.vlan_count is None
    assert result.warnings is not None
    assert any(w["section"] == "vlans" for w in result.warnings)
```

### Phase 31 Test Statistics (to replicate)

Phase 31 had:
- `TestParamGuard` — 9 tests (L595-688)
- `TestParamGuardIntegration` — 6 tests (L690-748)
- Total: **15 tests** covering guard logic + integration

Phase 32 test targets:
- `TestVLANCount500` — 3 tests in `test_client.py`
- `TestVLANCountErrorHandling` — 7 tests in `test_devices.py`
- Total: **~10 tests** covering count behavior + device-level handling

---

## 7. Specific File Locations and Line Numbers Summary

| File | Change | Lines |
|------|--------|-------|
| `nautobot_mcp/models/device.py` | Add `warnings` field to `DeviceStatsResponse` | L72-80 (extend) |
| `nautobot_mcp/models/device.py` | Add `warnings` field to `DeviceInventoryResponse` | L119-121 (append) |
| `nautobot_mcp/models/device.py` | Change `vlan_count: int` → `Optional[int]` in `DeviceStatsResponse` | L78 |
| `nautobot_mcp/devices.py` | `get_device_summary()`: use `device.location.id`, add try/except, add warnings | L254-263 |
| `nautobot_mcp/devices.py` | `get_device_inventory()` sequential "vlans" branch: UUID + try/except | L338-342 |
| `nautobot_mcp/devices.py` | `_count_vlans_by_loc` helper in parallel block: UUID + try/except | L346-349 |
| `nautobot_mcp/devices.py` | Sequential fallback: same pattern | L380-383 |
| `nautobot_mcp/devices.py` | Initialize `warnings: list[dict] = []` at top of `get_device_inventory` | L314-320 area |
| `nautobot_mcp/cli/devices.py` | `devices_summary`: null guard for `vlan_count` | L140 |
| `tests/test_client.py` | Add `TestVLANCount500` class | After L294 |
| `tests/test_devices.py` | New file: `TestVLANCountErrorHandling` + fixtures | New |

---

## 8. Change Footprint Analysis

### Risk Assessment

| Area | Risk | Mitigation |
|------|------|-----------|
| `client.count()` | No changes — already propagates correctly | None needed |
| `get_device_summary()` | Low — only adding try/except around existing call | `mock_device_record` fixture already has location.id |
| `get_device_inventory()` | Low — try/except added at 4 call sites in existing branches | Parallel block exception caught by outer try/except |
| `DeviceStatsResponse` | Low — `vlan_count` already Optional in `DeviceInventoryResponse` | Same pattern |
| `DeviceInventoryResponse` | Low — only adding `warnings` field, backward-compatible | New field with default=None |
| CLI `devices_summary` | Low — adding null guard, `N/A` for None | Consistent with `devices_inventory` pattern |
| Existing tests | Zero risk — no changes to working code | All existing tests pass unchanged |

### Backward Compatibility

- `warnings` field has `default=None` — existing JSON consumers ignore it
- `vlan_count=None` is the failure case only; normal path returns `int`
- `N/A` in table output is human-facing only; `--json` returns `null`
- No changes to `count()` signature, return type, or exception behavior

### Import Changes Required

In `devices.py`, add:
```python
from nautobot_mcp.exceptions import NautobotAPIError
```

In `cli/devices.py` (no new imports — uses existing pattern):
```python
# No new imports needed
```

---

## 9. Deferred Items Noted

1. **`list_vlans()` VLAN fetch** — `client.api.ipam.vlans.filter(id__in=chunk)` in `ipam.py` (same 414 pattern as Phase 30, deferred to future phase)
2. **`WarningCollector` vs response-level `warnings` naming** — different field names at different layers; acceptable since they serve different purposes (child-call-level vs response-level)
3. **TEST-02 / TEST-03 live verification** — requires `NAUTOBOT_URL` + `NAUTOBOT_TOKEN`; run as UAT with `pytest -m live`

---

*Research complete. Phase 32 is ready to plan.*
*Reference: 32-CONTEXT.md decisions D-01 through D-11, REQUIREMENTS.md VLAN-01..VLAN-04 and TEST-01..TEST-03, STATE.md v1.7 root causes.*
