# Phase 30 Research: Direct HTTP Bulk Fetch for get_device_ips()

**Date:** 2026-03-29
**Status:** COMPLETE

---

## 1. How `client.api.http_session.get()` with Comma-Separated UUIDs Works

### URL Format

Django REST Framework (DRF) natively supports comma-separated values for `__in` lookups. When you pass a list or comma-joined string as a query parameter, DRF expands it into multiple WHERE clauses equivalent to SQL `WHERE id IN ('uuid1', 'uuid2', 'uuid3')`.

**Exact URL built by `requests` params dict:**
```
GET /api/ipam/ip_address_to_interface/?interface=uuid1,uuid2,uuid3
GET /api/ipam/ip_addresses/?id__in=uuid1,uuid2,uuid3
```

When `requests` receives `params={"interface": ["uuid1", "uuid2"]}` (a list), it serializes to `?interface=uuid1&interface=uuid2` — which DRF also accepts. Both formats work. The `?interface=uuid1,uuid2,uuid3` comma-separated form is shorter and equivalent.

**The `requests` library handles the encoding automatically:**
```python
# These are equivalent in the resulting URL:
session.get(url, params={"interface": "uuid1,uuid2,uuid3"})
session.get(url, params={"interface": ["uuid1", "uuid2", "uuid3"]})
session.get(url, params={"id__in": "uuid1,uuid2,uuid3"})
```

### Why This Fixes 414

The current code does O(n) `.filter(interface=chunk)` calls — one HTTP request per chunk. For a device with 700+ interfaces, that's 2+ round-trips minimum. Each call includes the full URL path and query string in the HTTP request line. Even with chunking, the cumulative URI length across many calls can exceed server limits.

Comma-separated bulk: **1 HTTP request** per pass (M2M + IP detail). URL stays well under 8K even with 500 UUIDs.

### Confirmed Working Pattern (from `list_ip_addresses()` lines 130-139)

```python
m2m_resp = client.api.http_session.get(
    f"{client._profile.url}/api/ipam/ip_address_to_interface/",
    params={"interface": str(iface.id)},  # single UUID — same pattern scales
)
```

### Confirmed Working Pattern (from `list_vlans()` lines 244-269)

For VLAN bulk fetch — already uses `client.api.ipam.vlans.filter(id__in=chunk)` in the current (slow) code. Direct HTTP will replace this with:

```python
resp = client.api.http_session.get(
    f"{client._profile.url}/api/ipam/vlans/",
    params={"id__in": ",".join(chunk)},
)
```

---

## 2. How `return_obj()` Works — Exact Parameters

### Source: `pynautobot/core/endpoint.py` lines 55-83

`Endpoint.__init__` sets:
```python
self.return_obj = self._lookup_ret_obj(name, model)
```

Where `return_obj` is a **class** (either a named `Record` subclass or the generic `Record` class).

### Signature

```python
Record.__init__(self, values: dict, api: pynautobot.api, endpoint: Endpoint)
```

`return_obj` is the `Record` class (or a subclass), so calling it:
```python
# return_obj IS the Record class — call it like a constructor:
record = endpoint.return_obj(raw_dict, api, endpoint)
```

### Usage in the Codebase

**Pattern from `list_ip_addresses()` lines 118-121:**
```python
iface_records = [
    client.api.dcim.interfaces.return_obj(r, client.api, client.api.dcim.interfaces)
    for r in iface_data.get("results", [])
]
```

**Pattern from `list_ip_addresses()` lines 136-140:**
```python
m2m_records = [
    client.api.ipam.ip_address_to_interface.return_obj(r, client.api, client.api.ipam.ip_address_to_interface)
    for r in m2m_data.get("results", [])
]
```

**Key invariant:** `endpoint.return_obj` is always available because `Endpoint` objects are set up at pynautobot initialization time — they exist for all three endpoints involved:
- `client.api.dcim.interfaces` → `Endpoint` with `return_obj = Record` (or custom)
- `client.api.ipam.ip_address_to_interface` → `Endpoint` with `return_obj = Record`
- `client.api.ipam.ip_addresses` → `Endpoint` with `return_obj = Record`

### What `return_obj` Does Internally

From `pynautobot/core/response.py` lines 148-158, `Record.__init__`:
```python
def __init__(self, values, api, endpoint):
    self.has_details = False
    self._full_cache = []
    self._init_cache = []
    self.api = api
    self.default_ret = Record
    self.endpoint = self._endpoint_from_url(values["url"]) if "url" in values else endpoint
    if values:
        self._parse_values(values)
```

`Record._parse_values` recursively wraps nested objects as `Record` instances and caches everything in `_init_cache`. The result is a full-featured pynautobot object supporting attribute access (`m2m.ip_address.id`, `ip.address`, etc.) — identical to what you'd get from a direct `.filter()` call.

### No Network Call in `return_obj`

`return_obj` is a **pure constructor** — it parses the dict and creates Python objects in memory. No HTTP request is made. This is critical: it means bulk-fetching via direct HTTP + wrapping with `return_obj` is safe and fast.

---

## 3. How Pagination `next` Link Works in DRF Responses

### DRF Pagination Format

Every paginated list response from Nautobot has this shape:
```json
{
  "count": 1523,
  "next": "https://nautobot.netnam.vn/api/ipam/ip_addresses/?offset=100&limit=100",
  "previous": null,
  "results": [ ... ]
}
```

When `next` is `null`, there are no more pages.

### pynautobot's Pagination Logic (from `query.py` lines 337-350)

```python
def req_all(add_params):
    req = self._make_call(add_params=add_params)
    if isinstance(req, dict) and req.get("results") is not None:
        ret = req["results"]
        first_run = True
        while req["next"] and self.offset is None:
            if not add_params and first_run:
                req = self._make_call(add_params={"limit": req["count"], "offset": len(req["results"])})
            else:
                req = self._make_call(url_override=req["next"])
            first_run = False
            ret.extend(req["results"])
        return ret
    return req
```

### Manual Pagination Loop (for direct HTTP)

The pattern we need to implement manually since we're bypassing pynautobot:

```python
def _fetch_all_pages(url: str, session, initial_params: dict) -> list[dict]:
    """Fetch all pages from a DRF paginated endpoint."""
    results: list[dict] = []
    current_url = url
    params = dict(initial_params)

    while True:
        if current_url:
            resp = session.get(current_url)
        else:
            resp = session.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get("results", []))

        next_url = data.get("next")
        if not next_url:
            break
        # Use next URL directly — don't re-encode params
        current_url = next_url
        params = {}  # params are already in next_url

    return results
```

### Key Insight: Use `next` URL Directly

The `next` URL from DRF already has all query params encoded. The cleanest approach is to use `session.get(next_url)` directly without reconstructing params — avoids double-encoding edge cases.

### Limit on First Request Only

If a limit is provided, DRF respects it and `next` will appear after the first page. For bulk fetches with comma-separated IDs, we intentionally want **no `limit`** on the HTTP request — get all matching records in one shot. But if Nautobot's default page size kicks in (usually 50 or 100), pagination will occur.

Strategy: omit `limit` param → DRF uses server default → follow `next` links until exhausted.

---

## 4. Partial Failure Tolerance for Individual IP Detail Fetches

### Why Individual 404s Can Happen

Between the M2M scan (Pass 2) and IP detail fetch (Pass 3), a brief window exists where:
- An IP is deleted from Nautobot
- An IP is reassigned to a different device
- Network hiccup causes a transient 404

### Behavior Decision (from 30-CONTEXT.md D-12)

> Individual IP lookup failures (deleted IPs, 404s) are collected in `unlinked_ips` rather than crashing. Only hard failures (e.g., whole-request 500) propagate.

### Implementation Strategy

When using comma-separated bulk fetch with `id__in=uuid1,uuid2,...`, a single HTTP request returns all IPs. If **some** UUIDs are stale, DRF returns **200 with partial results** — the 404s are silently dropped. This is actually fine: missing IPs simply won't appear in the results, and we treat them as `unlinked_ips`.

```python
# In Pass 3, when wrapping raw results with return_obj:
fetched_ids = {r["id"] for r in all_ip_pages}
requested_ids = set(ip_ids)
missing_ids = requested_ids - fetched_ids

# Log missing IDs (informational only, not an error)
if missing_ids:
    logger.debug("IPs no longer exist in Nautobot: %s", missing_ids)
```

### Alternative: Per-UUID Request with Try/Except

This would be safer but defeats the purpose of bulk fetch. The DRF `id__in` approach silently drops missing IDs — which is acceptable behavior since `unlinked_ips` is already a catch-all.

### Hard Failures Still Propagate

Only **whole-request** failures (HTTP 500, 503, auth errors, network timeouts) propagate via `_handle_api_error`. These represent systemic issues, not individual missing records.

```python
try:
    resp = client.api.http_session.get(url, params=params)
    resp.raise_for_status()  # Only 200-299 — raises for 500/503/etc.
except requests.exceptions.HTTPError as e:
    # 500, 503, etc. — hard failure, propagate
    client._handle_api_error(e, "bulk_fetch", "IPAddress")
except requests.exceptions.RequestException as e:
    # Network-level failure — propagate
    raise NautobotConnectionError(...)
```

---

## 5. `_bulk_get_by_ids()` Helper — Signature and Design

### Placement

`ipam.py`, module-level, before `list_prefixes()`.

### Signature

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pynautobot.core.endpoint import Endpoint
    from nautobot_mcp.client import NautobotClient


def _bulk_get_by_ids(
    client: NautobotClient,
    endpoint_accessor: "Endpoint",
    ids: list[str],
    id_param: str = "id__in",
) -> list:
    """Bulk fetch records by IDs using direct HTTP + comma-separated format.

    Replaces O(n) .filter() loops with O(1) direct HTTP calls using DRF's
    comma-separated __in syntax. Handles pagination automatically.

    Args:
        client: NautobotClient instance — provides http_session and _profile.url.
        endpoint_accessor: pynautobot Endpoint object
            (e.g., client.api.ipam.ip_addresses, client.api.ipam.ip_address_to_interface).
        ids: List of UUID strings to fetch.
        id_param: Query parameter name — "id__in" for IP/vlan lookups,
            "interface" for M2M interface lookups.

    Returns:
        List of pynautobot Record objects.

    Raises:
        NautobotAPIError: On HTTP errors (400, 401, 403, 500, etc.).
        NautobotConnectionError: On network-level failures.
    """
```

### Internal Flow

```
1. If ids is empty → return [] (early return per URI-05)
2. Build URL: f"{client._profile.url}{endpoint_accessor.url}"  (endpoint_accessor.url = "/api/ipam/ip_addresses/")
3. Build params: {id_param: ",".join(ids)}  → "?id__in=uuid1,uuid2,uuid3"
4. Initial GET → resp.json() → collect results + follow next link
5. Wrap all raw dicts with endpoint_accessor.return_obj(...)
6. Return list of Record objects
```

### Handling "interface" as id_param (M2M Case)

For `ip_address_to_interface` with interface UUIDs, the param name is `interface` (not `interface__in`):
```python
params = {"interface": ",".join(iface_ids)}
# Results in: ?interface=uuid1,uuid2,uuid3
```

DRF accepts this for `interface` filter on the M2M junction table.

### No Return Type Annotation on Record List

`pynautobot.core.response.Record` is importable but it's a class, not a generic type. `list[Record]` would require `from pynautobot.core.response import Record` — this is fine to import for type checking but the return type annotation should use string form for forward reference:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pynautobot.core.response import Record

def _bulk_get_by_ids(...) -> list["Record"]:
```

Or simply use `list` without annotation and document the return type in the docstring (matches existing codebase style).

### Call Sites in `get_device_ips()`

```python
# Pass 2: M2M bulk fetch
m2m_records: list = _bulk_get_by_ids(
    client,
    client.api.ipam.ip_address_to_interface,
    iface_ids,
    id_param="interface",
)

# Pass 3: IP detail bulk fetch
ip_records: list = _bulk_get_by_ids(
    client,
    client.api.ipam.ip_addresses,
    ip_ids,
    id_param="id__in",
)
```

### Call Site in `list_ip_addresses()` (Deferred — Phase 30 defines the helper)

The M2M fetch in `list_ip_addresses()` lines 130-139 (single-interface case) could use the same helper:
```python
# Current (single interface):
m2m_resp = client.api.http_session.get(
    f"{client._profile.url}/api/ipam/ip_address_to_interface/",
    params={"interface": str(iface.id)},
)
```

This would become:
```python
m2m_records = _bulk_get_by_ids(
    client,
    client.api.ipam.ip_address_to_interface,
    [str(iface.id)],
    id_param="interface",
)
```

But this is out of scope for Phase 30 per deferred decisions in 30-CONTEXT.md.

---

## Summary: All 5 Key Questions Answered

| # | Question | Answer |
|---|----------|--------|
| 1 | How does `http_session.get()` with comma-separated UUIDs work? | `requests` serializes `{"id__in": "uuid1,uuid2"}` to `?id__in=uuid1,uuid2`; DRF expands to SQL `IN` clause. URL stays well under 8K. Pattern proven in `list_ip_addresses()` lines 130-139. |
| 2 | How does `return_obj()` work — exact parameters? | `Endpoint.return_obj` is the `Record` class. Call: `endpoint.return_obj(raw_dict, api, endpoint)` — pure constructor, no HTTP call. Available on all three endpoints (`interfaces`, `ip_address_to_interface`, `ip_addresses`). |
| 3 | How does pagination `next` link work? | DRF response: `{"results": [...], "next": "url|null"}`. Loop: `while next_url: resp = session.get(next_url); results += resp.json()["results"]; next_url = resp.json()["next"]`. Use `next_url` directly (already fully-encoded). |
| 4 | Partial failure tolerance for IP detail fetches? | DRF `id__in` with stale UUIDs returns 200 with partial results (missing IPs silently dropped). Track `requested - fetched` IDs → add to `unlinked_ips`. Only whole-request failures (500/503/auth) propagate via `_handle_api_error`. |
| 5 | What does `_bulk_get_by_ids()` helper signature look like? | `_bulk_get_by_ids(client, endpoint_accessor, ids, id_param="id__in")` — direct HTTP, comma-joined params, follows `next` links, wraps with `return_obj()`, returns `list[Record]`. Empty `ids` → early `[]` return. |

---

## Don't Hand-Roll

- **Pagination logic from scratch** — use the `while next_url` loop already analyzed; don't invent new pagination schemes.
- **Type stubs for pynautobot Record** — just import `Record` from `pynautobot.core.response` for type annotations. It's a concrete class, not a Protocol.
- **Chunking fallback** — Phase 30 user decision: no chunking fallback. If DRF comma-separated fails (server misconfiguration), the error propagates normally.
- **Duplicate detection in `_bulk_get_by_ids()`** — caller (`get_device_ips()`) deduplicates by ID via `set()` before calling. Don't add deduplication inside the helper — keeps it composable.
- **Per-UUID try/except in Pass 3** — DRF `id__in` already handles missing IDs gracefully. Don't do N individual requests to "handle" 404s — that defeats the bulk fetch purpose.

---

## Useful Code Snippets

### Wrapping raw HTTP response results into Records

```python
records = [
    endpoint.return_obj(r, client.api, endpoint)
    for r in all_pages_results
]
```

### Following all `next` links in a DRF paginated response

```python
results: list[dict] = []
next_url: str | None = None

while True:
    if next_url:
        resp = client.api.http_session.get(next_url)
    else:
        resp = client.api.http_session.get(base_url, params=params)
    resp.raise_for_status()
    data = resp.json()
    results.extend(data.get("results", []))
    next_url = data.get("next")
    if not next_url:
        break
```

### `_bulk_get_by_ids` skeleton

```python
def _bulk_get_by_ids(
    client: NautobotClient,
    endpoint,
    ids: list[str],
    id_param: str = "id__in",
) -> list:
    """Bulk fetch by IDs via direct HTTP. See 30-RESEARCH.md §5."""
    if not ids:
        return []

    url = f"{client._profile.url}{endpoint.url}"
    params = {id_param: ",".join(ids)}
    results: list[dict] = []

    while True:
        resp = client.api.http_session.get(url if not results else next_url, params=params if not results else None)
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get("results", []))
        next_url = data.get("next")
        if not next_url:
            break
        params = None  # next_url already includes all params

    return [endpoint.return_obj(r, client.api, endpoint) for r in results]
```

---

*Research completed: 2026-03-29*
*All 5 key questions answered. Ready to plan.*
