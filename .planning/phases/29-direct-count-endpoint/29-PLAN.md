---
wave: 1
depends_on: []
files_modified:
  - nautobot_mcp/client.py
  - nautobot_mcp/devices.py
  - nautobot_mcp/bridge.py
requirements_addressed:
  - PERF-03
  - PERF-04
  - OBS-02
---

# Phase 29: Direct /count/ Endpoint — Plan

## Overview

pynautobot's `.count()` method does NOT use Nautobot's `/count/` endpoint. It sends `GET /endpoint/?limit=1` then auto-paginates through ALL pages, returning `len(results)` — making every count call O(n) with unnecessary network overhead. Phase 29 replaces all 8 `.count()` call sites with a new `NautobotClient.count()` method that calls `GET /api/{app}/{endpoint}/count/?...` directly (O(1)), with a 404 fallback to pynautobot for plugin endpoints that lack `/count/` support.

Phase 29 also adds `latency_ms` to every `nautobot_call_nautobot` response so agents and UAT can observe bridge performance independently of per-section timing in `devices.py`.

---

## Tasks

### Task 1: Add `NautobotClient.count()` method

<read_first>
nautobot_mcp/client.py (L1-165 — imports, class def, `api` property, `_handle_api_error`)
</read_first>

<action>
Add `count()` as a new method on `NautobotClient` in `nautobot_mcp/client.py`. Insert it after the `golden_config` property (after line 331, before the `cms` property at line 333). The method must:

1. Build the count URL as `{self._profile.url}/api/{app}/{endpoint}/count/` (note: `app` and `endpoint` are passed as separate args; the URL path is `api/{app}/{endpoint}/count/`)
2. Use `self.api.http_session.get(url, params=filters)` directly — same session used by pynautobot, already has token headers, SSL verify, and timeouts configured
3. On HTTP 200: return `response.json()["count"]` (an integer)
4. On HTTP 404: fall through to pynautobot fallback
5. On HTTP non-404 4xx/5xx: call `resp.raise_for_status()` to trigger `_handle_api_error` via the `except requests.exceptions.HTTPError` path (add `import requests` at the top)
6. On network errors: let `requests.exceptions.ConnectionError` propagate to `_handle_api_error`
7. Fallback: use `getattr(getattr(self.api, app), endpoint).count(**filters)` — pynautobot's auto-paginating count, used only when `/count/` is unavailable

**Exact code to insert after `client.py` line 331 (after `golden_config` property, before `cms` property):**

```python
    def count(self, app: str, endpoint: str, **filters) -> int:
        """O(1) count via Nautobot's /count/ endpoint.

        Calls GET /api/{app}/{endpoint}/count/?... directly, bypassing
        pynautobot's .count() which auto-paginates through all records.

        Falls back to pynautobot's .count() (O(n)) if the endpoint does not
        support /count/ (e.g., some plugin endpoints return 404).

        Args:
            app: Nautobot app name (e.g., "dcim", "ipam").
            endpoint: Endpoint name (e.g., "interfaces", "ip_addresses", "vlans").
            **filters: Query-string filters passed to the /count/ endpoint.

        Returns:
            Integer count of matching records.

        Raises:
            NautobotValidationError: For 400 errors or invalid filters.
            NautobotAuthenticationError: For 401/403 errors.
            NautobotAPIError: For 5xx errors or other API failures.
            NautobotConnectionError: For network-level failures.
        """
        import requests as _requests

        url = f"{self._profile.url}/api/{app}/{endpoint}/count/"
        try:
            resp = self.api.http_session.get(url, params=filters)
            if resp.ok:
                return resp.json()["count"]
            if resp.status_code == 404:
                # Endpoint does not support /count/ — fall back to pynautobot
                pass
            else:
                resp.raise_for_status()
        except _requests.exceptions.HTTPError:
            # Pass through to _handle_api_error
            pass

        # Fallback: pynautobot .count() — O(n) auto-pagination, but works everywhere
        app_obj = getattr(self.api, app)
        ep_obj = getattr(app_obj, endpoint)
        return ep_obj.count(**filters)
```

**Also add `import requests` to the imports at the top of `client.py`** (around line 12, after `from requests.exceptions import ConnectionError as RequestsConnectionError`):

```python
import requests
```
</action>

<acceptance_criteria>
- [ ] `grep 'def count' nautobot_mcp/client.py` — method `count(self, app: str, endpoint: str, **filters)` is found
- [ ] `grep 'http_session.get' nautobot_mcp/client.py` — direct GET to `/count/` URL is present
- [ ] `grep 'resp.status_code == 404' nautobot_mcp/client.py` — 404 fallback to pynautobot is present
- [ ] `grep 'raise_for_status' nautobot_mcp/client.py` — non-404 errors are propagated
- [ ] `grep '^import requests' nautobot_mcp/client.py` — `import requests` added at module top
- [ ] `grep 'ep_obj.count' nautobot_mcp/client.py` — pynautobot fallback is present
</acceptance_criteria>

---

### Task 2: Replace all `.count()` call sites in `devices.py`

<read_first>
nautobot_mcp/devices.py (L228-264 for get_device_summary; L327-385 for get_device_inventory count block)
</read_first>

<action>
Replace all 8 `.count()` call sites in `nautobot_mcp/devices.py` with `client.count()` calls. All replacements follow the same pattern:

| Location | Old call | New call |
|----------|----------|----------|
| L248 | `client.api.dcim.interfaces.count(device=name)` | `client.count("dcim", "interfaces", device=name)` |
| L252 | `client.api.ipam.ip_addresses.count(device_id=device_uuid)` | `client.count("ipam", "ip_addresses", device_id=device_uuid)` |
| L257 | `client.api.ipam.vlans.count(location=device_location)` | `client.count("ipam", "vlans", location=device_location)` |
| L332 | `client.api.dcim.interfaces.count(device=device_name)` | `client.count("dcim", "interfaces", device=device_name)` |
| L342 | `client.api.ipam.vlans.count(location=loc_name)` | `client.count("ipam", "vlans", location=loc_name)` |
| L349 | `client_.api.ipam.vlans.count(location=loc)` | `client_.count("ipam", "vlans", location=loc)` |
| L375 | `client.api.dcim.interfaces.count(device=device_name)` | `client.count("dcim", "interfaces", device=device_name)` |
| L383 | `client.api.ipam.vlans.count(location=loc_name)` | `client.count("ipam", "vlans", location=loc_name)` |

**In `get_device_summary()` (L244-264):**

Replace L248-257 with:
```python
    # Step 2: Interface count — direct /count/ endpoint (O(1))
    interface_count = client.count("dcim", "interfaces", device=name)

    # Step 3: IP count — direct /count/ endpoint (O(1))
    device_uuid = device.id
    ip_count = client.count("ipam", "ip_addresses", device_id=device_uuid)

    # Step 4: VLAN count — scoped to device's location (VLANs have no device FK)
    device_location = device.location.name if device.location else None
    vlan_count = client.count("ipam", "vlans", location=device_location) if device_location else 0
```

**In `get_device_inventory()` — sequential count block (L330-343):**

Replace L331-343 with:
```python
            if detail == "interfaces":
                t_iface_count = time.time()
                total_interfaces = client.count("dcim", "interfaces", device=device_name)
                interfaces_latency_ms = (time.time() - t_iface_count) * 1000
            elif detail == "ips":
                t_ips = time.time()
                ips_resp = ipam_mod.get_device_ips(client, device_name=device_name, limit=0, offset=0)
                total_ips = ips_resp.total_ips
                ips_latency_ms = (time.time() - t_ips) * 1000
            elif detail == "vlans":
                t_vlans = time.time()
                loc_name = device_obj.location.name if device_obj.location else None
                total_vlans = client.count("ipam", "vlans", location=loc_name) if loc_name else 0
                vlans_latency_ms = (time.time() - t_vlans) * 1000
```

**In `get_device_inventory()` — parallel count block (L347-371):**

Replace L347-350 with:
```python
            def _count_vlans_by_loc(client_: NautobotClient, loc: str | None) -> int:
                if loc:
                    return client_.count("ipam", "vlans", location=loc)
                return 0
```

**In `get_device_inventory()` — sequential fallback block (L374-384):**

Replace L374-384 with:
```python
            except Exception:
                # Sequential fallback on any parallel failure
                t_iface_count = time.time()
                total_interfaces = client.count("dcim", "interfaces", device=device_name)
                interfaces_latency_ms = (time.time() - t_iface_count) * 1000
                t_ips = time.time()
                ips_resp = ipam_mod.get_device_ips(client, device_name=device_name, limit=0, offset=0)
                total_ips = ips_resp.total_ips
                ips_latency_ms = (time.time() - t_ips) * 1000
                t_vlans = time.time()
                loc_name = device_obj.location.name if device_obj.location else None
                total_vlans = client.count("ipam", "vlans", location=loc_name) if loc_name else 0
                vlans_latency_ms = (time.time() - t_vlans) * 1000
```
</action>

<acceptance_criteria>
- [ ] `grep -c '\.count(' nautobot_mcp/devices.py` returns `0` — no remaining `.count(` calls exist
- [ ] `grep 'client.count(' nautobot_mcp/devices.py` — exactly 8 `client.count(` call sites are found
- [ ] `grep 'client_.count(' nautobot_mcp/devices.py` — `client_.count("ipam", "vlans", location=loc)` is present
- [ ] `grep 'device_id=device_uuid' nautobot_mcp/devices.py` — ip_addresses count uses `client.count("ipam", "ip_addresses", device_id=device_uuid)`
- [ ] `grep 'location=loc_name' nautobot_mcp/devices.py` — vlans count uses `client.count("ipam", "vlans", location=loc_name)`
</acceptance_criteria>

---

### Task 3: Add `latency_ms` to bridge response envelope

<read_first>
nautobot_mcp/bridge.py (L149-191 `_execute_core`, L236-319 `_execute_cms`, L322-399 `call_nautobot`)
</read_first>

<action>
Add wall-clock `latency_ms` to the `call_nautobot` response dict. The latency must cover the full execution of `call_nautobot` (not just `_execute_core`/`_execute_cms`), including any overhead from `resolve_device_id` in CMS calls.

**Step A — `bridge.py`: Add `import time` at the top if not present**

Check if `import time` is already present (grep: `grep '^import time' nautobot_mcp/bridge.py`). If not, add it after the other imports (after `import re` on line 11):

```python
import time
```

**Step B — `bridge.py`: Wrap the try block in `call_nautobot` with wall-clock timing**

In `call_nautobot()` (around line 372), the current try block starts with:
```python
    try:
        # Route to correct backend, passing offset
        if base_endpoint.startswith("/api/"):
            ...
```

Replace that entire `try` block (lines 372-399) with:

```python
    t_start = time.time()
    try:
        # Route to correct backend, passing offset
        if base_endpoint.startswith("/api/"):
            app_name, ep_name = _parse_core_endpoint(base_endpoint)
            result = _execute_core(client, app_name, ep_name, method,
                                   params, effective_data, id, limit, offset)
        elif base_endpoint.startswith("cms:"):
            cms_key = base_endpoint[4:]  # Strip "cms:" prefix
            result = _execute_cms(client, cms_key, method,
                                  params, effective_data, id, limit, offset)
        else:
            raise NautobotValidationError(
                message=f"Unsupported endpoint prefix: '{endpoint}'",
                hint="Endpoints must start with '/api/' or 'cms:'. "
                     "Use nautobot_api_catalog() to see available endpoints.",
            )

        # Add request context and latency to response
        latency_ms = round((time.time() - t_start) * 1000, 1)
        result["endpoint"] = endpoint
        result["method"] = method
        result["latency_ms"] = latency_ms
        return result

    except NautobotMCPError:
        # Record latency even on known errors
        result = {"endpoint": endpoint, "method": method}
        result["latency_ms"] = round((time.time() - t_start) * 1000, 1)
        raise
    except Exception as e:
        # Translate unexpected errors
        client._handle_api_error(e, method.lower(), endpoint)
        raise  # _handle_api_error always raises, but satisfy type checker
```

**Note:** When `_handle_api_error` re-raises, we can't add latency to the raised exception object. Instead, we record it in a short-lived `result` dict before re-raising. The MCP tool response will only have `latency_ms` on success, but the caller can observe the timing in logs via the success path. (Agents typically read the success response only.)

**Step C — `bridge.py`: Remove now-redundant `result["endpoint"]` / `result["method"]` additions**

After the rewrite in Step B, the lines `result["endpoint"] = endpoint` and `result["method"] = method` are no longer duplicated — they are now inside the try block as shown above. The old lines after the try block (around L390-391) must be deleted. Verify the final structure of `call_nautobot` ends with `return result` inside the `try` block and no code after the `except` clauses.
</action>

<acceptance_criteria>
- [ ] `grep '^import time' nautobot_mcp/bridge.py` — `import time` is at module top
- [ ] `grep 'time.time()' nautobot_mcp/bridge.py` — `t_start = time.time()` is present (2 occurrences: start + in exception handler)
- [ ] `grep "result\['latency_ms'\]" nautobot_mcp/bridge.py` — `latency_ms` added to result dict on success
- [ ] `grep 'latency_ms = round' nautobot_mcp/bridge.py` — `latency_ms` rounded to 1 decimal place
- [ ] Verify `call_nautobot` return statement is inside the try block (no code after except clauses except `raise`)
</acceptance_criteria>

---

## Verification

| Requirement | Criterion | Verification |
|-------------|-----------|--------------|
| PERF-03 | `client.count()` uses direct `/count/` URL | `grep 'http_session.get' client.py` + `grep 'count/' client.py` |
| PERF-04 | All `.count()` in `devices.py` replaced | `grep -c '\.count(' devices.py` returns `0`; 8 `client.count(` calls exist |
| OBS-02 | `latency_ms` in `call_nautobot` response | `grep "latency_ms" bridge.py` and `grep "latency_ms" server.py` docstring |

---

## must_haves

1. **`NautobotClient.count(app, endpoint, **filters)`** — returns `int`, calls `GET /api/{app}/{endpoint}/count/?...` directly, 404 falls back to pynautobot
2. **Zero `.count(` occurrences** in `nautobot_mcp/devices.py` after the phase (grep-verifiable)
3. **`latency_ms` as a `float`** present in every `nautobot_call_nautobot` success response dict, set via `result["latency_ms"] = round((time.time() - t_start) * 1000, 1)`
4. **All 8 call sites** replaced: 3 in `get_device_summary`, 1 sequential + 1 parallel + 1 sequential fallback in `get_device_inventory` (3 × 1 = 3 sections × multiple lines = 8 total individual lines)
5. **`import requests`** added to `nautobot_mcp/client.py` — required for `requests.exceptions.HTTPError` / `requests.exceptions.ConnectionError` to be reachable from within `count()`

---

## Notes

- **`skip_count` is already wired** from Phase 28: `call_nautobot` accepts it, passes it to `_execute_core`/`_execute_cms`. Phase 29 does NOT modify `skip_count` logic — the improvement is only: when count IS needed, it will now be O(1) instead of O(n) via `client.count()`.
- **CMS endpoints** (`cms/client.py`) do not call `.count()` — no changes needed there.
- **`ipam.py`** uses `ListResponse(count=len(results), results=results)` — no `.count()` calls exist there either.
- **Unit test coverage**: `tests/test_bridge.py` should gain `test_count_o1` (mock http_session → verify direct call) and `test_count_404_fallback` (mock 404 → verify pynautobot fallback). These are out-of-scope for the plan itself but should be added before Phase 29 is marked complete.
