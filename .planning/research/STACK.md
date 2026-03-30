# Stack Research: CMS Pagination Fix (v1.8)

**Pynautobot version:** 3.0.0

## Key Finding: No `page_size` Attribute on `Endpoint`

pynautobot's `Endpoint` class holds **zero pagination state**. Only `Request.limit` matters. `limit=0` is falsy → not sent in HTTP request → server uses PAGE_SIZE=1 → 151 sequential calls.

## Fix: Override `limit=0` with `_CMS_BULK_LIMIT = 200` in `cms_list()`

Single choke point in `nautobot_mcp/cms/client.py`. All 38+ CMS list operations benefit automatically.

## Slow Endpoints (confirmed)

| Function | Endpoint | Records | Calls (before) | Calls (after) |
|---|---|---|---|---|
| `list_bgp_address_families()` | `juniper_bgp_address_families` | 151 | 151 | 1 |
| `list_bgp_policy_associations()` | `juniper_bgp_policy_associations` | — | 1+ (plugin bug) | 1 |
| `list_interface_families()` | `juniper_interface_families` | varies | N | ceil(N/200) |

All other `cms_list()` callers also benefit: `list_static_routes`, `list_firewall_filters`, `list_interface_units`, etc.
**Researched:** 2026-03-29

## No new libraries needed

All fix patterns already exist in the codebase.

## Existing patterns to replicate

### Direct HTTP via http_session.get()

Already used in `list_interfaces()`, `list_ip_addresses()`, `list_vlans()`, `NautobotClient.count()`:

```python
resp = client.api.http_session.get(
    f"{client._profile.url}/api/<app>/<endpoint>/",
    params={"id__in": ",".join(ids)},   # comma-separated, not repeated params
)
resp.raise_for_status()
data = resp.json()
records = data.get("results", [])
```

### DRF comma-separated format

Django REST Framework supports both:
- Repeated params: `?id__in=uuid1&id__in=uuid2` — pynautobot default, hits 414 at ~500 UUIDs
- Comma-separated: `?id__in=uuid1,uuid2,uuid3` — DRF-native, ~3x shorter URI

The codebase already uses comma-separated in the direct HTTP pattern above.

### pynautobot Record wrapping

Direct HTTP returns raw dicts. Existing code uses `return_obj()` to wrap them:

```python
from pynautobot.core.response import Record
record = endpoint.return_obj(raw_dict, api, endpoint)
```

## Fix locations

| Component | File | Function | Pattern to fix |
|-----------|------|----------|----------------|
| CLI/MCP IP fetch | `ipam.py` | `get_device_ips()` | `.filter(id__in=chunk)` → direct HTTP |
| CLI/MCP M2M fetch | `ipam.py` | `get_device_ips()` | `.filter(interface=chunk)` → direct HTTP |
| REST bridge | `bridge.py` | `_execute_core()` | `.filter(**params)` → guard `__in` lists |
| REST bridge CMS | `bridge.py` | `_execute_cms()` | `.filter(**effective_params)` → guard `__in` lists |
| VLAN list | `ipam.py` | `list_vlans()` | Already uses direct HTTP, safe |
| Interface list | `interfaces.py` | `list_interfaces()` | Already uses direct HTTP, safe |

## Chunking utility

Already exists in `utils.py:12`:
```python
def chunked(iterable: Iterable[T], size: int) -> Iterator[list[T]]:
    it = iter(iterable)
    while chunk := list(itertools.islice(it, size)):
        yield chunk
```

Chunk size of 500 is used for existing patterns. Comma-separated DRF format is shorter than repeated params, so 500 comma-separated UUIDs should stay well under 8 KB.

## No new dependencies

- `pynautobot` (existing — provides `http_session` and `return_obj`)
- `more_itertools.chunked` (already used)
- Python ≥ 3.11 (existing)
