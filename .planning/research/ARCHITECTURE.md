# Research: Architecture — v1.7 URI Limit Fix

**Domain:** Bug fix
**Researched:** 2026-03-29

## How the fix integrates

### Before vs After: ipam.py get_device_ips()

```
BEFORE (3 passes):
  Pass 1: list(client.api.dcim.interfaces.filter(device=name))
  Pass 2: for chunk in chunked(iface_ids, 500):
            list(client.api.ipam.ip_address_to_interface.filter(interface=chunk))
          → ?interface=uuid1&interface=uuid2&... (repeated, ~18 KB per chunk)
  Pass 3: for chunk in chunked(ip_ids, 500):
            list(client.api.ipam.ip_addresses.filter(id__in=chunk))
          → ?id__in=uuid1&id__in=uuid2&... (repeated, ~18 KB per chunk)

AFTER (3 passes, 1 HTTP call each):
  Pass 1: list(client.api.dcim.interfaces.filter(device=name))  ← single device, safe
  Pass 2: HTTP GET ?interface=uuid1,uuid2,uuid3,...             ← comma-separated
  Pass 3: HTTP GET ?id__in=uuid1,uuid2,uuid3,...               ← comma-separated
```

### Before vs After: bridge.py

```
BEFORE (unguarded):
  list(endpoint.filter(**params, **pagination_kwargs))
  → {"id__in": [uuid1..uuid10000]} → repeated params → 414

AFTER (guarded):
  _guard_params(params) → validate list sizes
  if list values in params:
      if len(list) > 500: raise NautobotValidationError("chunk your __in requests")
      else: serialize as comma-separated string
  → endpoint.filter(id__in="uuid1,uuid2,uuid3")  ← DRF comma-separated
```

## Component changes

### nautobot_mcp/ipam.py — get_device_ips()

Replace the two `.filter()` loop passes with direct HTTP calls:

```
Pass 2 (M2M): client.api.http_session.get(
    f"{url}/api/ipam/ip_address_to_interface/",
    params={"interface": ",".join(iface_ids)},
    timeout=120,
)

Pass 3 (IP detail): client.api.http_session.get(
    f"{url}/api/ipam/ip-addresses/",
    params={"id__in": ",".join(ip_ids)},
    timeout=120,
)
```

Handle pagination by checking `data.get("next")` and following if present.

Wrap raw dicts back into pynautobot Record objects using `return_obj()`.

### nautobot_mcp/bridge.py — _execute_core() + _execute_cms()

Add `_guard_filter_params()` function:

```python
def _guard_filter_params(params: dict | None) -> dict | None:
    """Convert list values in __in params to comma-separated strings.

    Raises NautobotValidationError if any list > 500 items.
    """
    if not params:
        return params
    safe = {}
    for k, v in params.items():
        if isinstance(v, (list, tuple)) and not isinstance(v, str):
            if len(v) > 500:
                raise NautobotValidationError(
                    message=f"Parameter '{k}' has {len(v)} items; "
                            "maximum is 500 to avoid Request-URI Too Large errors.",
                    errors=[],
                    hint="Split into multiple calls with fewer items per __in parameter.",
                )
            safe[k] = ",".join(str(x) for x in v)
        else:
            safe[k] = v
    return safe
```

Apply to both `_execute_core()` and `_execute_cms()` before the `.filter()` call.

### nautobot_mcp/client.py — optional helper

May add a `_bulk_filter()` helper that handles comma-separated DRF format + pagination-following for reuse, but only if it simplifies multiple call sites. Otherwise, keep fixes inline in ipam.py.

## Data flow changes

- No change to Pydantic response models
- No change to CLI output format
- No change to MCP tool signatures
- Only internal HTTP call patterns change
- VLANs count: return `None` on 500 instead of raising

## Build order

1. **Phase 1 — ipam.py direct HTTP fix** (standalone, easy to test)
2. **Phase 2 — bridge.py param guard** (affects all MCP callers)
3. **Phase 3 — VLANs 500 mitigation + tests** (isolated, small)
