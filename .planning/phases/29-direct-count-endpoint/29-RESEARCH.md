# RESEARCH COMPLETE

## Topic 1: /count/ Endpoint Behavior

### Nautobot's `/count/` Endpoint — Exact Mechanics

Nautobot exposes a dedicated `/count/` sub-endpoint for every REST list endpoint. The format is:

```
GET /api/dcim/devices/count/          → {"count": 87382}
GET /api/dcim/devices/count/?site=tst1  → {"count": 5827}
GET /api/ipam/vlans/count/?location=...  → {"count": N}
```

- **URL format**: `{base_list_endpoint}/count/` (append `/count/` to the list URL)
- **Response shape**: `{"count": <integer>}` — single key, no pagination, no `results`
- **Filters**: Supports identical query-string filters as the list endpoint (e.g., `?device=name`, `?location=...`)
- **Authentication**: Same `Authorization: Token <token>` header as list endpoints
- **Speed**: O(1) — Nautobot executes a `SELECT COUNT(*)` at the DB level; the response body is ~20 bytes

### CRITICAL BUG FOUND: pynautobot's `.count()` Does NOT Use `/count/`

This is the root cause Phase 29 solves. Verified by reading pynautobot 3.0.0 source (`pynautobot/core/endpoint.py` line 494 + `pynautobot/core/query.py` line 480):

```python
# pynautobot/core/endpoint.py — Endpoint.count()
def count(self, *args, api_version=None, **kwargs):
    req = Request(
        filters=kwargs,
        base=self.url,   # self.url = f"{base_url}/{app}/{endpoint}"  ← LIST endpoint
        token=self.token,
        http_session=self.api.http_session,
        api_version=api_version,
    )
    return ret.get_count()

# pynautobot/core/query.py — Request.get_count()
def get_count(self, *args, **kwargs) -> int:
    return self._make_call(add_params={"limit": 1})["count"]
```

What happens:
1. `Endpoint.count(device="HQV-PE1-NEW")` builds a Request with `base = /api/dcim/interfaces/`
2. `get_count()` sends: `GET /api/dcim/interfaces/?device=HQV-PE1-NEW&limit=1`
3. Nautobot returns `{"count": 747, "results": [...], "next": "..."}`
4. pynautobot sees `next` is non-null → enters auto-pagination loop
5. Fetches ALL 747 pages (or up to pynautobot's max page limit)
6. Returns `len(all_results)` = 747

**The `/count/` endpoint is never called.** Every `.count()` in the codebase is O(n) page fetches, not O(1).

### pynautobot's `http_session`

- `api.http_session` is a `requests.Session` instance (line 72 of `pynautobot/core/api.py`)
- It's already configured with: token headers, SSL verify, retry adapter, timeouts `(10, 60)`
- It can be used directly for raw GET requests: `client.api.http_session.get(url, params={...})`
- Returns a `requests.Response` object with `.json()`, `.status_code`, `.ok`, etc.

### CMS Plugin Endpoints — `/count/` Support

CMS plugin endpoints (e.g., `client.api.plugins.netnam_cms_core`) may or may not have `/count/` sub-endpoints. This is plugin-dependent. The Phase 29 implementation must:
1. Try the direct `/count/` URL first
2. Gracefully fall back to `.count()` (O(n)) if the endpoint returns 404

## Topic 2: Implementation Approach

### Step A: Add `NautobotClient.count(endpoint, **filters) -> int`

Location: `nautobot_mcp/client.py`

```python
def count(self, app: str, endpoint: str, **filters) -> int:
    """O(1) count via Nautobot's /count/ endpoint.

    Falls back to pynautobot's .count() (O(n) auto-pagination) if
    /count/ is not available on the endpoint.
    """
```

URL construction:
- Base: `self._profile.url` (e.g., `https://nautobot.netnam.vn`)
- Count URL: `{base}/api/{app}/{endpoint}/count/`
- Example: `https://nautobot.netnam.vn/api/dcim/interfaces/count/?device=HQV-PE1-NEW`

Implementation pattern:
1. Build count URL from app + endpoint + filters
2. Make direct GET via `self.api.http_session.get(url, params=filters)`
3. On 200: return `response.json()["count"]`
4. On 404: fall back to `getattr(self.api, app).__getattr__(endpoint).count(**filters)`
5. On other errors: pass through `_handle_api_error`

Note: `self.api` (the `pynautobot.api` instance) is accessible via `NautobotClient.api` property.

### Step B: Replace All `.count()` Calls

#### devices.py — 6 occurrences

| Line | Current | Replacement |
|------|---------|-------------|
| 248 | `client.api.dcim.interfaces.count(device=name)` | `client.count("dcim", "interfaces", device=name)` |
| 252 | `client.api.ipam.ip_addresses.count(device_id=device_uuid)` | `client.count("ipam", "ip_addresses", device_id=device_uuid)` |
| 257 | `client.api.ipam.vlans.count(location=device_location)` | `client.count("ipam", "vlans", location=device_location)` |
| 332 | `client.api.dcim.interfaces.count(device=device_name)` | `client.count("dcim", "interfaces", device=device_name)` |
| 342 | `client.api.ipam.vlans.count(location=loc_name)` | `client.count("ipam", "vlans", location=loc_name)` |
| 349 | `client_.api.ipam.vlans.count(location=loc)` | `client_.count("ipam", "vlans", location=loc)` |
| 375 | `client.api.dcim.interfaces.count(device=device_name)` | `client.count("dcim", "interfaces", device=device_name)` |
| 383 | `client.api.ipam.vlans.count(location=loc_name)` | `client.count("ipam", "vlans", location=loc_name)` |

#### cms/client.py — `.count()` on CMS endpoints

CMS endpoints accessed via `client.api.plugins.netnam_cms_core.<endpoint>.count(...)` — check if these have `/count/` support. The `count()` method should be usable with the same pattern.

#### ipam.py — No `.count()` calls found

`ipam.py` uses `ListResponse(count=len(results), results=results)` — no direct `.count()` calls. `get_device_ips` computes `total_ips = len(all_entries)` from in-memory results (not a network call), so no change needed there.

### Step C: Add `latency_ms` to `call_nautobot` Response

Location: `nautobot_mcp/bridge.py` — `call_nautobot()` function

Pattern (already established in `devices.py`):
```python
import time
t_start = time.time()
# ... API call ...
result = ...
result["latency_ms"] = round((time.time() - t_start) * 1000, 1)
result["endpoint"] = endpoint
result["method"] = method
return result
```

Note: This only adds `latency_ms` to the `call_nautobot` response, NOT to the CLI output (CLI has its own formatting layer). The MCP tool response (via `server.py`) will automatically include it since `call_nautobot` is the bridge.

### Step D: `skip_count` Already Wired

Phase 28 already plumbed `skip_count` through `_execute_core`. Phase 29 does NOT need to add more `skip_count` logic — the flag is already respected by the calling code. The improvement is: when count IS needed, it will now be O(1) instead of O(n).

## Topic 3: Error Handling

### HTTP Error Responses from `/count/`

The `/count/` endpoint follows standard Nautobot REST error semantics:

| Status | Meaning | Handling |
|--------|---------|----------|
| 200 | Success | `return response.json()["count"]` |
| 400 | Invalid filter | Let `_handle_api_error` translate → `NautobotValidationError` |
| 401/403 | Auth failure | Let `_handle_api_error` translate → `NautobotAuthenticationError` |
| 404 | Endpoint has no `/count/` | **FALL BACK to pynautobot `.count()`** |
| 429 | Rate limited | Let `_handle_api_error` translate → `NautobotAPIError` with retry hint |
| 500/502/503/504 | Server error | Let `_handle_api_error` translate → `NautobotAPIError` |

### Critical: 404 Fallback Strategy

The 404 case is the most important edge case. Implementation:
```python
def count(self, app: str, endpoint: str, **filters) -> int:
    url = f"{self._profile.url}/api/{app}/{endpoint}/count/"
    try:
        resp = self.api.http_session.get(url, params=filters)
        if resp.ok:
            return resp.json()["count"]
        if resp.status_code == 404:
            # Endpoint doesn't support /count/ — fall back to pynautobot
            pass  # fall through to fallback
        resp.raise_for_status()
    except requests.exceptions.HTTPError:
        # Fall back to pynautobot
        pass

    # Fallback: pynautobot .count() — O(n) but works for all endpoints
    app_obj = getattr(self.api, app)
    ep_obj = getattr(app_obj, endpoint)
    return ep_obj.count(**filters)
```

Note: Use `resp.ok` (status < 400) to catch 2xx, then `resp.raise_for_status()` for 4xx/5xx that aren't 404.

### Error Propagation from `http_session`

`http_session.get()` raises `requests.exceptions.ConnectionError` on network failure, which `_handle_api_error` already catches and translates to `NautobotConnectionError`. The pynautobot `count()` fallback also goes through the same error handler.

## Topic 4: Testing Strategy

### Unit Tests (no credentials needed)

1. **`test_count_o1_fallback`** — Mock `http_session.get` to return `{"count": 42}`; verify `client.count("dcim", "interfaces", device="foo")` returns 42 without calling pynautobot
2. **`test_count_404_fallback`** — Mock 404 on direct URL, then mock pynautobot `.count()` to return 7; verify fallback is called
3. **`test_count_filter_passthrough`** — Verify filters are passed as query params to the `/count/` URL
4. **`test_bridge_latency_ms`** — Call `call_nautobot`, verify `latency_ms` key is in response and value is a float >= 0

### Live UAT (requires `NAUTOBOT_URL` + `NAUTOBOT_TOKEN`)

1. **Timing comparison**: Call `client.count("dcim", "interfaces", device="HQV-PE1-NEW")` and time it — should return in <100ms regardless of interface count
2. **Consistency check**: Compare `client.count("dcim", "interfaces", device=X)` vs `len(list(client.api.dcim.interfaces.filter(device=X)))` — must be identical
3. **Bridge latency**: Call `nautobot_call_nautobot` with a count endpoint and verify `latency_ms` in response

## Key Findings for Planning

- **CRITICAL BUG**: pynautobot 3.0.0 `.count()` uses `GET /endpoint/?limit=1` + auto-pagination — never calls `/count/`. Every `.count()` call in `devices.py` is O(n), not O(1). This is the root cause Phase 29 fixes.
- **The `/count/` URL format** is `{base_url}/api/{app}/{endpoint}/count/?{filters}` — append `/count/` to the list URL and pass filters as query params. Response is `{"count": N}`.
- **`http_session` is ready to use**: `client.api.http_session` is a configured `requests.Session` already used by pynautobot — it handles token headers, SSL, retries, and timeouts automatically.
- **404 fallback is essential**: Not all Nautobot plugins/endpoints expose `/count/`. The implementation must catch 404 and fall back to pynautobot's `.count()` to maintain correctness.
- **Only `devices.py` needs `.count()` replacements** — 6 call sites in `devices.py`, none in `ipam.py`. CMS endpoints should also use the new method but need runtime verification.
- **`latency_ms` addition to `call_nautobot`** is a one-timer: wrap the execution block with `time.time()` before/after, add `result["latency_ms"] = round(...)`, return. The `endpoint` and `method` are already added at the end of `call_nautobot`.
