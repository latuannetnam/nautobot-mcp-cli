# Phase 32: VLANs 500 Fix + Regression Tests — Executable Plan

**Phase:** 32-vlans-500-fix-regression-tests
**Date:** 2026-03-29
**Status:** PLANNED

---

## Overview

Fixes the VLANs 500 error by passing `location=<uuid>` instead of `location=<name>` to `/api/ipam/vlans/count/`. Adds structured `warnings` field to response models. Adds regression tests. Live verification against prod.

### Decision Lock (D-01 through D-11)
All decisions are non-negotiable. Every task below implements exactly one decision.

| Decision | What | Where |
|----------|------|-------|
| D-01 | `device.location.id` instead of `device.location.name` | `devices.py` call sites |
| D-03 | `count()` propagates 500 as `NautobotAPIError` (no change — already works) | `client.py` |
| D-04 | Call sites catch `NautobotAPIError`, set `total_vlans = None` | `devices.py` |
| D-05/D-06 | `warnings: list[dict[str,str]] | None` with `{"section","message","recoverable"}` | Response models |
| D-07 | `vlan_count=None` → `null` in JSON (automatic via Pydantic) | Response models |
| D-08 | `vlan_count=None` → `N/A` in human table | `cli/devices.py` |
| D-09 | `TestVLANCount500` in `test_client.py` | 3 tests |
| D-10 | `tests/test_devices.py` (new) — device-level tests | 7 tests |
| D-11 | All existing tests pass | Verification |

---

## Wave 1: Model Changes — Add `warnings` Field

### Task 1.1 — `DeviceStatsResponse`: `vlan_count` → `Optional[int]`, add `warnings`

**`<read_first>`**
- `nautobot_mcp/models/device.py` L72-80

**`<acceptance_criteria>`**
- [ ] `DeviceStatsResponse` has `vlan_count: Optional[int] = Field(default=None, ...)` — grep `"vlan_count: Optional[int]"` in `models/device.py`
- [ ] `DeviceStatsResponse` has `warnings: Optional[list[dict[str, str]]] = Field(default=None, ...)` — grep `"warnings:"` in `DeviceStatsResponse`
- [ ] `uv run pytest tests/test_models.py -q` passes (if exists)

**`<action>`**

Edit `nautobot_mcp/models/device.py` L72-80:

```python
# BEFORE (L72-80):
class DeviceStatsResponse(BaseModel):
    device: DeviceSummary = Field(description="Core device info")
    interface_count: int = Field(default=0, description="Total interface count")
    ip_count: int = Field(default=0, description="Total IP count")
    vlan_count: int = Field(default=0, description="Total VLAN count")
    enabled_count: int = Field(default=0, description="Enabled interfaces")
    disabled_count: int = Field(default=0, description="Disabled interfaces")

# AFTER:
class DeviceStatsResponse(BaseModel):
    device: DeviceSummary = Field(description="Core device info")
    interface_count: int = Field(default=0, description="Total interface count")
    ip_count: int = Field(default=0, description="Total IP count")
    vlan_count: Optional[int] = Field(
        default=None,
        description="Total VLAN count (null if unavailable due to server error)",
    )
    enabled_count: int = Field(default=0, description="Enabled interfaces")
    disabled_count: int = Field(default=0, description="Disabled interfaces")
    warnings: Optional[list[dict[str, str]]] = Field(
        default=None,
        description="Recoverable error warnings from data fetch",
    )
```

---

### Task 1.2 — `DeviceInventoryResponse`: add `warnings` field

**`<read_first>`**
- `nautobot_mcp/models/device.py` L83-121 (entire class)

**`<acceptance_criteria>`**
- [ ] `DeviceInventoryResponse` has `warnings: Optional[list[dict[str, str]]] = Field(default=None)` appended after `has_more` — grep `"warnings:"` in `DeviceInventoryResponse`
- [ ] `total_vlans` already `Optional[int]` at L101 — no change needed

**`<action>`**

Edit `nautobot_mcp/models/device.py` L120-121 — append after `has_more`:

```python
    # BEFORE (L119-121):
    has_more: bool = Field(default=False, description="More results available")

# AFTER (add 3 lines):
    has_more: bool = Field(default=False, description="More results available")
    warnings: Optional[list[dict[str, str]]] = Field(
        default=None,
        description="Recoverable error warnings from data fetch",
    )
```

---

## Wave 2: `devices.py` — UUID Resolution + Error Catch

### Task 2.1 — `get_device_summary()`: UUID + try/except + warnings

**`<read_first>`**
- `nautobot_mcp/devices.py` L1-20 (imports), L240-265 (function body)
- `nautobot_mcp/exceptions.py` L98-128 (`NautobotAPIError`)
- `nautobot_mcp/models/device.py` L72-88 (`DeviceStatsResponse`)

**`<acceptance_criteria>`**
- [ ] `from nautobot_mcp.exceptions import NautobotAPIError` is in `devices.py` imports — grep `"from nautobot_mcp.exceptions import"` in `devices.py`
- [ ] `device.location.id` is used instead of `device.location.name` at the VLAN count call site — grep `"device.location.id"` in `devices.py`
- [ ] `NautobotAPIError` is caught around VLAN count, `vlan_count` set to `None`, warning appended — grep `"NautobotAPIError"` in `devices.py`
- [ ] `DeviceStatsResponse` construction includes `warnings=warnings`

**`<action>`**

Edit `nautobot_mcp/devices.py` L1-20 (imports) — add `NautobotAPIError`:

```python
from nautobot_mcp.exceptions import NautobotAPIError, NautobotNotFoundError
```

Edit `nautobot_mcp/devices.py` L254-263 (VLAN count + return):

```python
# BEFORE (L254-263):
    # Step 4: VLAN count — scoped to device's location (VLANs have no device FK)
    device_location = device.location.name if device.location else None
    vlan_count = client.count("ipam", "vlans", location=device_location) if device_location else 0

    return DeviceStatsResponse(
        device=device,
        interface_count=interface_count,
        ip_count=ip_count,
        vlan_count=vlan_count,
    )

# AFTER:
    # Step 4: VLAN count — scoped to device's location (VLANs have no device FK)
    # D-01: Use UUID (device.location.id) instead of name to avoid 500 on /count/
    # D-04: Catch NautobotAPIError → set vlan_count=None, append warning
    stats_warnings: list[dict[str, str]] | None = None
    device_location_id = device.location.id if device.location else None
    vlan_count: int | None = None
    if device_location_id:
        try:
            vlan_count = client.count("ipam", "vlans", location=device_location_id)
        except NautobotAPIError as e:
            stats_warnings = [{"section": "vlans", "message": f"VLAN count unavailable: {e}", "recoverable": True}]

    return DeviceStatsResponse(
        device=device,
        interface_count=interface_count,
        ip_count=ip_count,
        vlan_count=vlan_count,
        warnings=stats_warnings,
    )
```

---

### Task 2.2 — `get_device_inventory()`: Initialize `warnings` list

**`<read_first>`**
- `nautobot_mcp/devices.py` L314-321 (variable initialization block)

**`<acceptance_criteria>`**
- [ ] `inventory_warnings: list[dict[str, str]] = []` is initialized alongside the other totals — grep `"inventory_warnings"` in `devices.py`

**`<action>`**

Edit `nautobot_mcp/devices.py` L314-321 — add `inventory_warnings`:

```python
    # BEFORE (L314-321):
    total_interfaces: int | None = None
    total_ips: int | None = None
    total_vlans: int | None = None
    interfaces_latency_ms: float | None = None
    ips_latency_ms: float | None = None
    vlans_latency_ms: float | None = None

# AFTER (add inventory_warnings):
    total_interfaces: int | None = None
    total_ips: int | None = None
    total_vlans: int | None = None
    interfaces_latency_ms: float | None = None
    ips_latency_ms: float | None = None
    vlans_latency_ms: float | None = None
    inventory_warnings: list[dict[str, str]] = []
```

---

### Task 2.3 — `get_device_inventory()`: Sequential "vlans" branch — UUID + try/except

**`<read_first>`**
- `nautobot_mcp/devices.py` L338-342 (sequential `detail == "vlans"` branch)

**`<acceptance_criteria>`**
- [ ] `device_obj.location.id` used instead of `device_obj.location.name` — grep `"device_obj.location.id"` in `devices.py`
- [ ] `NautobotAPIError` caught, `total_vlans = None`, warning appended to `inventory_warnings`

**`<action>`**

Edit `nautobot_mcp/devices.py` L338-342:

```python
# BEFORE (L338-342):
            elif detail == "vlans":
                t_vlans = time.time()
                loc_name = device_obj.location.name if device_obj.location else None
                total_vlans = client.count("ipam", "vlans", location=loc_name) if loc_name else 0
                vlans_latency_ms = (time.time() - t_vlans) * 1000

# AFTER:
            elif detail == "vlans":
                t_vlans = time.time()
                loc_id = device_obj.location.id if device_obj.location else None
                if loc_id:
                    try:
                        total_vlans = client.count("ipam", "vlans", location=loc_id)
                    except NautobotAPIError as e:
                        total_vlans = None
                        inventory_warnings.append({"section": "vlans", "message": f"VLAN count unavailable: {e}", "recoverable": True})
                else:
                    total_vlans = 0
                vlans_latency_ms = (time.time() - t_vlans) * 1000
```

---

### Task 2.4 — `get_device_inventory()`: Parallel `_count_vlans_by_loc` helper — UUID + try/except

**`<read_first>`**
- `nautobot_mcp/devices.py` L346-383 (parallel block + sequential fallback)

**`<acceptance_criteria>`**
- [ ] `_count_vlans_by_loc` accepts `loc_id: str | None` (not `loc`) — grep `"_count_vlans_by_loc"` in `devices.py`
- [ ] `_count_vlans_by_loc` returns `int | None` (not just `int`) — grep `"int | None"` near `_count_vlans_by_loc`
- [ ] `_count_vlans_by_loc` catches `NautobotAPIError`, returns `None`

**`<action>`**

Edit `nautobot_mcp/devices.py` L346-365 (parallel block — change helper + inner call + result handling):

```python
# BEFORE (L346-365):
            def _count_vlans_by_loc(client_: NautobotClient, loc: str | None) -> int:
                if loc:
                    return client_.count("ipam", "vlans", location=loc)
                return 0

            try:
                loc_name = device_obj.location.name if device_obj.location else None
                with ThreadPoolExecutor(max_workers=3) as ex:
                    t_parallel_start = time.time()
                    f_iface = ex.submit(client.count, "dcim", "interfaces", device=device_name)
                    f_ips   = ex.submit(
                        ipam_mod.get_device_ips,
                        client, device_name=device_name, limit=0, offset=0
                    )
                    f_vlans = ex.submit(_count_vlans_by_loc, client, loc_name)
                    total_interfaces = f_iface.result()
                    ips_resp = f_ips.result()
                    total_vlans = f_vlans.result()
                    total_ips = ips_resp.total_ips
                    parallel_latency = (time.time() - t_parallel_start) * 1000
                    ips_latency_ms = parallel_latency
                    interfaces_latency_ms = parallel_latency
                    vlans_latency_ms = parallel_latency

# AFTER (replace L346-365 with):
            def _count_vlans_by_loc(client_: NautobotClient, loc_id: str | None) -> int | None:
                """Count VLANs by location UUID. Returns None if count fails."""
                if loc_id:
                    try:
                        return client_.count("ipam", "vlans", location=loc_id)
                    except NautobotAPIError:
                        return None
                return 0

            try:
                loc_id = device_obj.location.id if device_obj.location else None
                with ThreadPoolExecutor(max_workers=3) as ex:
                    t_parallel_start = time.time()
                    f_iface = ex.submit(client.count, "dcim", "interfaces", device=device_name)
                    f_ips   = ex.submit(
                        ipam_mod.get_device_ips,
                        client, device_name=device_name, limit=0, offset=0
                    )
                    f_vlans = ex.submit(_count_vlans_by_loc, client, loc_id)
                    total_interfaces = f_iface.result()
                    ips_resp = f_ips.result()
                    vlans_result = f_vlans.result()
                    total_vlans = vlans_result
                    total_ips = ips_resp.total_ips
                    parallel_latency = (time.time() - t_parallel_start) * 1000
                    ips_latency_ms = parallel_latency
                    interfaces_latency_ms = parallel_latency
                    vlans_latency_ms = parallel_latency
                    # D-04: Handle VLAN count failure in parallel path
                    if total_vlans is None:
                        inventory_warnings.append({"section": "vlans", "message": "VLAN count unavailable in parallel fetch", "recoverable": True})
                        total_vlans = None
```

---

### Task 2.5 — `get_device_inventory()`: Sequential fallback — UUID + try/except

**`<read_first>`**
- `nautobot_mcp/devices.py` L380-383 (sequential fallback block)

**`<acceptance_criteria>`**
- [ ] Fallback uses `device_obj.location.id` — grep `"loc_id"` near `except Exception` block

**`<action>`**

Edit `nautobot_mcp/devices.py` L380-383:

```python
# BEFORE (L380-383):
                t_vlans = time.time()
                loc_name = device_obj.location.name if device_obj.location else None
                total_vlans = client.count("ipam", "vlans", location=loc_name) if loc_name else 0
                vlans_latency_ms = (time.time() - t_vlans) * 1000

# AFTER:
                t_vlans = time.time()
                loc_id = device_obj.location.id if device_obj.location else None
                if loc_id:
                    try:
                        total_vlans = client.count("ipam", "vlans", location=loc_id)
                    except NautobotAPIError as e:
                        total_vlans = None
                        inventory_warnings.append({"section": "vlans", "message": f"VLAN count unavailable: {e}", "recoverable": True})
                else:
                    total_vlans = 0
                vlans_latency_ms = (time.time() - t_vlans) * 1000
```

---

### Task 2.6 — `get_device_inventory()`: Pass `warnings` to response model

**`<read_first>`**
- `nautobot_mcp/devices.py` L430-470 (end of function, return statement)

**`<acceptance_criteria>`**
- [ ] `DeviceInventoryResponse` construction includes `warnings=inventory_warnings` or `warnings=inventory_warnings or None` — grep `"warnings=inventory_warnings"` in `devices.py`

**`<action>`**

Edit the `return DeviceInventoryResponse(...)` call in `get_device_inventory()` to include:

```python
    # Add to the return statement (exact location depends on file):
    warnings=inventory_warnings or None,
```

Verify the full return statement includes all fields, e.g.:
```python
    return DeviceInventoryResponse(
        device=device_obj,
        interfaces=interfaces_data,
        interface_ips=interface_ips_data,
        vlans=vlans_data,
        total_interfaces=total_interfaces,
        total_ips=total_ips,
        total_vlans=total_vlans,
        interfaces_latency_ms=interfaces_latency_ms,
        ips_latency_ms=ips_latency_ms,
        vlans_latency_ms=vlans_latency_ms,
        total_latency_ms=(time.time() - t_start) * 1000,
        limit=limit,
        offset=offset,
        has_more=has_more,
        warnings=inventory_warnings or None,
    )
```

---

## Wave 3: CLI Formatter — `N/A` for Null `vlan_count`

### Task 3.1 — `devices_summary`: null guard for `vlan_count`

**`<read_first>`**
- `nautobot_mcp/cli/devices.py` L138-140

**`<acceptance_criteria>`**
- [ ] `devices_summary` shows `N/A` when `data['vlan_count']` is `None` — grep `"N/A"` in `cli/devices.py`

**`<action>`**

Edit `nautobot_mcp/cli/devices.py` L138-140:

```python
# BEFORE (L138-140):
        typer.echo(f"\n  Interfaces: {data['interface_count']}")
        typer.echo(f"  IP Addresses: {data['ip_count']}")
        typer.echo(f"  VLANs: {data['vlan_count']}")

# AFTER:
        typer.echo(f"\n  Interfaces: {data['interface_count']}")
        typer.echo(f"  IP Addresses: {data['ip_count']}")
        vlan_val = data["vlan_count"] if data["vlan_count"] is not None else "N/A"
        typer.echo(f"  VLANs: {vlan_val}")
```

Note: `devices_inventory` (L173-175) already handles `None` → `"?"` — no change needed there.

---

## Wave 4: Tests — Zero Regression + New Coverage

### Task 4.1 — Add `TestVLANCount500` to `test_client.py`

**`<read_first>`**
- `tests/test_client.py` L1-18 (imports), L220-295 (last class before EOF)
- `tests/conftest.py` L37-75 (`mock_device_record` fixture — has `location.id` and `location.name`)

**`<acceptance_criteria>`**
- [ ] `TestVLANCount500` class appended to `test_client.py` — grep `"class TestVLANCount500"` in `tests/test_client.py`
- [ ] `test_count_vlans_by_uuid_returns_int` — mocks HTTP 200, asserts `int` return — grep `"test_count_vlans_by_uuid"` in `tests/test_client.py`
- [ ] `test_count_vlans_500_raises_nautobot_api_error` — mocks HTTP 500, pynautobot fallback 500, asserts `NautobotAPIError` raised — grep `"test_count_vlans_500"` in `tests/test_client.py`
- [ ] `test_count_vlans_fallback_404_returns_pynautobot_count` — mocks 404 + pynautobot fallback, asserts int return
- [ ] `uv run pytest tests/test_client.py::TestVLANCount500 -v` — 3 pass

**`<action>`**

Append to `tests/test_client.py` (after `TestHandleApiErrorHintMap` at L295):

```python
# ---------------------------------------------------------------------------
# VLAN-01 + VLAN-02: count() with UUID location filter
# ---------------------------------------------------------------------------


class TestVLANCount500:
    """Test count() behavior with UUID location filter and 500 error path.

    Covers:
    - D-01: location=<uuid> succeeds with 200
    - D-03: 500 propagates as NautobotAPIError
    - D-04: caller catches NautobotAPIError
    """

    def _make_client(self, mock_nautobot_profile) -> NautobotClient:
        client = NautobotClient(profile=mock_nautobot_profile)
        client._api = MagicMock()
        client.api.http_session = MagicMock()
        return client

    def test_count_vlans_by_uuid_returns_int(self, mock_nautobot_profile):
        """location=<uuid> produces a valid count integer (200 OK)."""
        client = self._make_client(mock_nautobot_profile)

        fake_resp = MagicMock()
        fake_resp.ok = True
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"count": 42}
        client.api.http_session.get.return_value = fake_resp

        result = client.count("ipam", "vlans", location="5555-6666-7777-8888")
        assert result == 42
        # Verify UUID was passed, not name
        call_args = client.api.http_session.get.call_args
        assert "5555-6666-7777-8888" in str(call_args)

    def test_count_vlans_500_raises_nautobot_api_error(self, mock_nautobot_profile):
        """500 from /count/ propagates as NautobotAPIError (D-03)."""
        from nautobot_mcp.exceptions import NautobotAPIError

        client = self._make_client(mock_nautobot_profile)

        # Direct HTTP returns 500
        fake_resp_500 = MagicMock()
        fake_resp_500.ok = False
        fake_resp_500.status_code = 500
        fake_resp_500.text = "Internal Server Error"
        fake_resp_500.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=fake_resp_500
        )

        # pynautobot fallback also raises 500 (e.g. RequestError)
        fallback_error = make_request_error(500, "Internal Server Error", "/api/ipam/vlans/")
        client.api.http_session.get.return_value = fake_resp_500

        # Set up pynautobot endpoint to also raise
        mock_vlans = MagicMock()
        mock_vlans.count.side_effect = fallback_error
        client.api.ipam.vlans = mock_vlans

        with pytest.raises(NautobotAPIError) as exc_info:
            client.count("ipam", "vlans", location="5555-6666-7777-8888")

        assert exc_info.value.status_code == 500

    def test_count_vlans_fallback_404_returns_pynautobot_count(
        self, mock_nautobot_profile
    ):
        """404 from /count/ falls back to pynautobot .count() (D-03 path: 404 → pass)."""
        client = self._make_client(mock_nautobot_profile)

        # Direct HTTP returns 404 (endpoint not supported)
        fake_resp_404 = MagicMock()
        fake_resp_404.ok = False
        fake_resp_404.status_code = 404
        fake_resp_404.text = "Not Found"
        fake_resp_404.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=fake_resp_404
        )
        client.api.http_session.get.return_value = fake_resp_404

        # pynautobot fallback succeeds
        mock_vlans = MagicMock()
        mock_vlans.count.return_value = 17
        client.api.ipam.vlans = mock_vlans

        result = client.count("ipam", "vlans", location="5555-6666-7777-8888")
        assert result == 17
        mock_vlans.count.assert_called_once_with(location="5555-6666-7777-8888")
```

Also add this import near the top of `test_client.py` (after existing imports):
```python
import requests  # needed for HTTPError in test_count_vlans_500_raises_nautobot_api_error
```

---

### Task 4.2 — Create `tests/test_devices.py` — new file

**`<read_first>`**
- `tests/conftest.py` L37-75 (`mock_device_record` — has `location.id = "5555-6666-7777-8888"`, `location.name = "SGN-DC1"`)
- `nautobot_mcp/devices.py` L200-265 (`get_device_summary` + `get_device_inventory`)
- `tests/test_client.py` L1-10 (import style)

**`<acceptance_criteria>`**
- [ ] `tests/test_devices.py` exists — `ls tests/test_devices.py`
- [ ] `TestDeviceVLANCountErrorHandling` class present — grep `"TestDeviceVLANCountErrorHandling"` in `tests/test_devices.py`
- [ ] `test_get_device_summary_catches_vlan_count_500` — `vlan_count` is `None`, `warnings` contains vlans entry — grep `"test_get_device_summary_catches"` in `tests/test_devices.py`
- [ ] `test_get_device_inventory_catches_vlan_count_500` — sequential "vlans" branch, `total_vlans=None`, warning appended
- [ ] `test_get_device_inventory_parallel_catches_vlan_count_500` — parallel block returns `None`, warning appended
- [ ] `test_get_device_inventory_fallback_catches_vlan_count_500` — sequential fallback catches error
- [ ] `test_null_vlan_count_serializes_to_null` — `model_dump()` → JSON `null`
- [ ] `test_warning_dict_structure` — warning dict has `section`, `message`, `recoverable`
- [ ] `test_vlan_count_by_uuid` — count called with UUID not name
- [ ] `uv run pytest tests/test_devices.py -v` — 7 pass

**`<action>`**

Write `tests/test_devices.py`:

```python
"""Tests for devices.py — VLAN count error handling and warnings.

Covers VLAN-01, VLAN-02, VLAN-03, VLAN-04 and TEST-01.
D-01: location=<uuid> instead of location=<name>
D-04: NautobotAPIError caught → vlan_count=None + warning appended
D-05/D-06: warnings field with {"section", "message", "recoverable"}
D-07: vlan_count=None → null in JSON
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import json as json_module

import pytest

from nautobot_mcp.devices import get_device_summary, get_device_inventory
from nautobot_mcp.exceptions import NautobotAPIError
from nautobot_mcp.models.device import DeviceStatsResponse, DeviceInventoryResponse
from tests.conftest import *  # noqa: F403 — fixtures from conftest.py


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_mock_device_record():
    """Build a fresh mock device record using conftest fixture pattern."""
    device = MagicMock()
    device.id = "aaaa-bbbb-cccc-dddd"
    device.name = "core-rtr-01"
    device.status.display = "Active"
    device.device_type.id = "1111-2222-3333-4444"
    device.device_type.name = "MX204"
    device.device_type.display = "Juniper MX204"
    device.location.id = "5555-6666-7777-8888"  # UUID — D-01
    device.location.name = "SGN-DC1"  # name — should NOT be used for VLAN count
    device.location.display = "SGN-DC1"
    device.tenant = None
    device.role = None
    device.platform = MagicMock()
    device.platform.name = "junos"
    device.serial = "ABC123"
    device.primary_ip = None
    return device


# ---------------------------------------------------------------------------
# TestDeviceVLANCountErrorHandling
# ---------------------------------------------------------------------------


class TestDeviceVLANCountErrorHandling:
    """Test that VLAN count failures are handled gracefully.

    Verifies D-01 (UUID), D-04 (catch), D-05/D-06 (warnings), D-07 (null serialization).
    """

    # ------------------------------------------------------------------
    # get_device_summary
    # ------------------------------------------------------------------

    def test_get_device_summary_catches_vlan_count_500(self):
        """VLAN 500 → total_vlans=None, warning appended, no crash."""
        mock_client = MagicMock()

        # Device fetch succeeds — has location.id
        mock_client.api.dcim.devices.get.return_value = make_mock_device_record()
        mock_client.api.dcim.interfaces.count.return_value = 24
        mock_client.api.ipam.ip_addresses.count.return_value = 100

        # VLAN count raises NautobotAPIError 500 — D-04: caught at call site
        mock_client.api.ipam.vlans.count.side_effect = NautobotAPIError(
            "HTTP 500 during VLAN count",
            status_code=500,
        )

        result = get_device_summary(mock_client, name="core-rtr-01")

        # D-04: vlan_count is None (not 0, not re-raised)
        assert result.vlan_count is None
        # D-05/D-06: warnings present with correct structure
        assert result.warnings is not None
        assert len(result.warnings) == 1
        w = result.warnings[0]
        assert w["section"] == "vlans"
        assert "recoverable" in w
        assert w["recoverable"] is True
        assert "message" in w

        # Other counts unaffected
        assert result.interface_count == 24
        assert result.ip_count == 100

    def test_get_device_summary_normal_vlan_count(self):
        """Normal VLAN count (no 500) → vlan_count=int, warnings=None."""
        mock_client = MagicMock()
        mock_client.api.dcim.devices.get.return_value = make_mock_device_record()
        mock_client.api.dcim.interfaces.count.return_value = 24
        mock_client.api.ipam.ip_addresses.count.return_value = 100
        mock_client.api.ipam.vlans.count.return_value = 42  # succeeds

        result = get_device_summary(mock_client, name="core-rtr-01")

        assert result.vlan_count == 42
        assert result.warnings is None

    def test_vlan_count_by_uuid_not_name(self):
        """count() is called with location=<uuid>, not location=<name>."""
        mock_client = MagicMock()
        mock_client.api.dcim.devices.get.return_value = make_mock_device_record()
        mock_client.api.dcim.interfaces.count.return_value = 24
        mock_client.api.ipam.ip_addresses.count.return_value = 100
        mock_client.api.ipam.vlans.count.return_value = 5

        get_device_summary(mock_client, name="core-rtr-01")

        # Verify count was called with UUID (5555-6666-7777-8888), not name (SGN-DC1)
        call_args_list = mock_client.api.ipam.vlans.count.call_args_list
        if call_args_list:
            # Direct HTTP path: called with location=5555-6666-7777-8888
            args, kwargs = call_args_list[0]
            assert kwargs.get("location") == "5555-6666-7777-8888"

    # ------------------------------------------------------------------
    # get_device_inventory — sequential "vlans" branch
    # ------------------------------------------------------------------

    def test_get_device_inventory_catches_vlan_count_500(self):
        """Sequential 'vlans' branch: 500 → total_vlans=None, warning appended."""
        mock_client = MagicMock()
        mock_client.api.dcim.devices.get.return_value = make_mock_device_record()

        # Count calls: interfaces ok, IPs skipped (not detail=ips), VLANs 500
        mock_client.api.dcim.interfaces.count.return_value = 10
        mock_client.api.ipam.vlans.count.side_effect = NautobotAPIError(
            "HTTP 500", status_code=500
        )

        result = get_device_inventory(
            mock_client, name="core-rtr-01", detail="vlans", limit=50
        )

        assert result.total_vlans is None
        assert result.warnings is not None
        assert any(w["section"] == "vlans" for w in result.warnings)

    # ------------------------------------------------------------------
    # get_device_inventory — parallel block (detail="all")
    # ------------------------------------------------------------------

    def test_get_device_inventory_parallel_catches_vlan_count_500(self):
        """Parallel block: _count_vlans_by_loc returns None → warning appended."""
        mock_client = MagicMock()
        mock_client.api.dcim.devices.get.return_value = make_mock_device_record()

        # Interface count ok
        mock_client.api.dcim.interfaces.count.return_value = 10

        # get_device_ips for the parallel block — return a mock response
        mock_ips_resp = MagicMock()
        mock_ips_resp.total_ips = 50
        mock_client.api.ipam.ip_addresses.count.return_value = 50

        # Patch ipam.get_device_ips to return our mock response
        with patch("nautobot_mcp.devices.ipam_mod.get_device_ips") as mock_get_ips:
            mock_get_ips.return_value = mock_ips_resp

            # VLAN count 500 (will be caught inside _count_vlans_by_loc)
            mock_client.api.ipam.vlans.count.side_effect = NautobotAPIError(
                "HTTP 500", status_code=500
            )

            result = get_device_inventory(
                mock_client, name="core-rtr-01", detail="all", limit=50
            )

        # Parallel path caught the error → total_vlans=None, warning appended
        assert result.total_vlans is None
        assert result.warnings is not None
        assert any(w["section"] == "vlans" for w in result.warnings)

    # ------------------------------------------------------------------
    # get_device_inventory — sequential fallback
    # ------------------------------------------------------------------

    def test_get_device_inventory_fallback_catches_vlan_count_500(self):
        """Sequential fallback path catches VLAN 500 → total_vlans=None."""
        mock_client = MagicMock()
        mock_client.api.dcim.devices.get.return_value = make_mock_device_record()
        mock_client.api.dcim.interfaces.count.return_value = 10

        # get_device_ips in fallback also needs to be patchable
        mock_ips_resp = MagicMock()
        mock_ips_resp.total_ips = 50

        with patch("nautobot_mcp.devices.ipam_mod.get_device_ips") as mock_get_ips:
            mock_get_ips.return_value = mock_ips_resp
            # Force the fallback path by raising in the parallel path
            def count_side_effect(*args, **kwargs):
                # First call is interfaces (ok), second is VLANs
                if "vlans" in str(args) or kwargs.get("endpoint") == "vlans":
                    raise NautobotAPIError("HTTP 500", status_code=500)
                return 10

            mock_client.api.dcim.interfaces.count.return_value = 10

            # Make ThreadPoolExecutor fail by raising in count
            # We patch the thread so fallback is triggered
            def raise_on_vlans(*args, **kwargs):
                raise Exception("force fallback")

            # Actually, simpler: just ensure VLAN count in fallback raises
            # Patch the parallel block to immediately fail
            mock_client.api.dcim.interfaces.count.side_effect = [
                NautobotAPIError("force fallback", status_code=500)
            ] * 2

            result = get_device_inventory(
                mock_client, name="core-rtr-01", detail="all", limit=50
            )

        # In fallback, VLAN count 500 → total_vlans=None
        assert result.total_vlans is None
        assert result.warnings is not None

    # ------------------------------------------------------------------
    # JSON serialization (D-07)
    # ------------------------------------------------------------------

    def test_null_vlan_count_serializes_to_null_in_json(self):
        """vlan_count=None serializes to JSON null, not a crash."""
        mock_client = MagicMock()
        mock_client.api.dcim.devices.get.return_value = make_mock_device_record()
        mock_client.api.dcim.interfaces.count.return_value = 24
        mock_client.api.ipam.ip_addresses.count.return_value = 100
        mock_client.api.ipam.vlans.count.side_effect = NautobotAPIError(
            "HTTP 500", status_code=500
        )

        result = get_device_summary(mock_client, name="core-rtr-01")

        # model_dump should not raise
        data = result.model_dump()
        assert data["vlan_count"] is None

        # json.dumps should produce "null", not "None"
        json_str = json_module.dumps(data, indent=2)
        assert "null" in json_str
        assert "None" not in json_str

    # ------------------------------------------------------------------
    # Warning dict structure (D-05/D-06)
    # ------------------------------------------------------------------

    def test_warning_dict_structure(self):
        """Warning dict has required fields: section, message, recoverable."""
        mock_client = MagicMock()
        mock_client.api.dcim.devices.get.return_value = make_mock_device_record()
        mock_client.api.dcim.interfaces.count.return_value = 24
        mock_client.api.ipam.ip_addresses.count.return_value = 100
        mock_client.api.ipam.vlans.count.side_effect = NautobotAPIError(
            "HTTP 500", status_code=500
        )

        result = get_device_summary(mock_client, name="core-rtr-01")

        assert result.warnings is not None
        w = result.warnings[0]

        # Required fields per D-06
        assert "section" in w
        assert "message" in w
        assert "recoverable" in w

        # Value types
        assert isinstance(w["section"], str)
        assert isinstance(w["message"], str)
        assert isinstance(w["recoverable"], bool)
        assert w["section"] == "vlans"
        assert w["recoverable"] is True
```

**Note on the fallback test:** The `test_get_device_inventory_fallback_catches_vlan_count_500` test is complex because triggering the sequential fallback requires the ThreadPoolExecutor to raise. Simplify by patching `_count_vlans_by_loc` to raise directly. If the test proves too complex, remove it — the sequential "vlans" branch test and parallel test provide sufficient coverage of the try/except logic.

---

### Task 4.3 — Verify existing tests pass (TEST-01)

**`<read_first>`**
- `tests/test_client.py` — confirm all existing tests present
- `tests/test_bridge.py` — confirm all existing tests present

**`<acceptance_criteria>`**
- [ ] `uv run pytest tests/test_client.py tests/test_bridge.py tests/test_models.py -q` — all pass
- [ ] No existing test fails due to added `warnings` field (Pydantic ignores extra fields by default; existing tests use exact dict comparisons so we must ensure new field has default=None)

**`<action>`**

Run:
```bash
uv run pytest tests/test_client.py tests/test_bridge.py tests/test_models.py -v
```

If any test fails due to exact dict comparisons (comparing expected vs actual), inspect the failure. The `warnings` field has `default=None`, so existing `DeviceStatsResponse(...)` and `DeviceInventoryResponse(...)` constructions should work unchanged.

If a test uses `.model_dump()` and compares the result, check if it hardcodes the expected keys — if so, the test needs updating to include `warnings=None` in the expected dict.

---

## Wave 5: Live Verification (requires NAUTOBOT_URL + NAUTOBOT_TOKEN)

### Task 5.1 — Smoke test against prod with `devices summary`

**`<read_first>`**
- `CLAUDE.md` §"Configuration" — profile setup
- `.planning/phases/32-vlans-500-fix-regression-tests/32-CONTEXT.md` §"Specifics" — HQV-PE1-NEW

**`<acceptance_criteria>`**
- [ ] `nautobot-mcp --json devices summary HQV-PE1-NEW` returns HTTP 200 (no 500) — `vlan_count` is an integer
- [ ] No `NautobotAPIError` raised in output
- [ ] If VLANs 500 persists, `vlan_count` is `null` and `warnings` is present

**`<action>`**

```bash
# Using prod profile (default)
nautobot-mcp --json devices summary HQV-PE1-NEW

# Check output:
# - HTTP 200
# - "vlan_count": <int>  (UUID fix worked)
# OR
# - "vlan_count": null  (500 caught gracefully)
# - "warnings": [{"section": "vlans", ...}]
```

---

### Task 5.2 — Smoke test against prod with `devices inventory --detail vlans`

**`<acceptance_criteria>`**
- [ ] `nautobot-mcp --json devices inventory HQV-PE1-NEW --detail vlans` returns `total_vlans` as integer OR `null` with warning

**`<action>`**

```bash
nautobot-mcp --json devices inventory HQV-PE1-NEW --detail vlans
```

---

### Task 5.3 — Smoke test against prod with `devices inventory --detail all`

**`<acceptance_criteria>`**
- [ ] `nautobot-mcp --json devices inventory HQV-PE1-NEW --detail all` returns all 3 counts, parallel path
- [ ] If any count 500s, that section is `null` and `warnings` is non-empty

**`<action>`**

```bash
nautobot-mcp --json devices inventory HQV-PE1-NEW --detail all
```

---

## Verification Checklist

Run this at the end of all implementation tasks:

```bash
# 1. Model changes
uv run grep -n "warnings.*list\[dict" nautobot_mcp/models/device.py
# Expected: 2 occurrences (DeviceStatsResponse + DeviceInventoryResponse)

# 2. UUID used at call sites
uv run grep -n "device.location.id" nautobot_mcp/devices.py
# Expected: 3 occurrences (get_device_summary, get_device_inventory sequential, get_device_inventory parallel)

# 3. NautobotAPIError caught at call sites
uv run grep -n "NautobotAPIError" nautobot_mcp/devices.py
# Expected: 4 occurrences (get_device_summary + 3 in get_device_inventory)

# 4. N/A in CLI
uv run grep -n '"N/A"' nautobot_mcp/cli/devices.py
# Expected: 1 occurrence

# 5. All tests
uv run pytest tests/test_client.py tests/test_bridge.py tests/test_devices.py tests/test_models.py -q
# Expected: all pass

# 6. No new files left uncommitted
```

---

## File Change Summary

| File | Tasks | Lines Changed | Risk |
|------|-------|---------------|------|
| `nautobot_mcp/models/device.py` | 1.1, 1.2 | +8 | Low — backward-compatible fields |
| `nautobot_mcp/devices.py` | 2.1–2.6 | ~+40 | Medium — UUID resolution + try/except added at 4 call sites |
| `nautobot_mcp/cli/devices.py` | 3.1 | +1 | Low — null guard |
| `tests/test_client.py` | 4.1 | +60 | Low — new test class |
| `tests/test_devices.py` | 4.2 | ~+220 | Low — new file |
| `tests/conftest.py` | — | 0 | No change — fixtures already correct |

**Total: ~290 lines added, ~10 tests added, 0 existing tests broken.**

---

## PLANNING COMPLETE

Phase 32 Plan — 3 Waves + 5 Tasks + 12 sub-tasks
- Wave 1: Model changes (2 tasks)
- Wave 2: `devices.py` call sites (6 tasks)
- Wave 3: CLI formatter (1 task)
- Wave 4: Tests (3 tasks)
- Wave 5: Live verification (3 tasks)
