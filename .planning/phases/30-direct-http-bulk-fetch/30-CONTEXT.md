# Phase 30: Direct HTTP Bulk Fetch for get_device_ips() - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace `.filter(interface=chunk)` and `.filter(id__in=chunk)` in `ipam.py get_device_ips()` with direct HTTP calls using DRF comma-separated UUID format. Handles empty ID sets with early return. Fixes 414 Request-URI Too Large at the source.

</domain>

<decisions>
## Implementation Decisions

### M2M Fetch Strategy (Pass 2)

- **D-01:** M2M bulk fetch uses direct HTTP against `/api/ipam/ip_address_to_interface/` with comma-separated interface UUIDs: `?interface=uuid1,uuid2,uuid3`.
- **D-02:** No chunking fallback — DRF comma-separated format works for `ip_address_to_interface` (pynautobot's `return_obj` method is available on this endpoint).
- **D-03:** Empty interface ID list: early return with empty `DeviceIPsResponse` before any HTTP call (existing behavior preserved).

### IP Detail Fetch Strategy (Pass 3)

- **D-04:** IP detail bulk fetch uses direct HTTP against `/api/ipam/ip_addresses/` with comma-separated IP UUIDs: `?id__in=uuid1,uuid2,uuid3`.
- **D-05:** No chunking fallback — same rationale as D-02.
- **D-06:** Empty IP ID list: skip Pass 3 entirely, return early with `interface_ips=[]` and `unlinked_ips=[]`.

### Pagination Following

- **D-07:** Both passes follow HTTP `next` links when present in the response body. Collect all pages before returning results.
- **D-08:** `return_obj()` wraps raw HTTP response dicts back into pynautobot `Record` objects so attribute access (`m2m.ip_address.id`, `ip.address`, etc.) continues to work.

### Code Structure

- **D-09:** Extract a `_bulk_get_by_ids(endpoint, id_list, id_name, client)` helper in `ipam.py` that:
  - Accepts a pynautobot endpoint, list of UUID strings, and ID field name
  - Does direct HTTP with comma-separated IDs + `return_obj()`
  - Follows pagination `next` links
  - Raises on HTTP errors (delegates to `_handle_api_error`)
  - Returns a list of pynautobot `Record` objects
- **D-10:** Both `get_device_ips()` and `list_ip_addresses()` can use `_bulk_get_by_ids()` once extracted.

### Error Handling

- **D-11:** Pass 2 (M2M) errors propagate to top-level `_handle_api_error` — M2M fetch is all-or-nothing.
- **D-12:** Pass 3 (IP detail) implements partial failure tolerance: individual IP lookup failures (deleted IPs, 404s) are collected in `unlinked_ips` rather than crashing the pass. Only hard failures (e.g., whole-request 500) propagate.

### Boundary Notes

- The initial interface fetch (`client.api.dcim.interfaces.filter(device=device_name)`) is OUT of scope — not a 414 source and not mentioned in ROADMAP success criteria.
- `list_vlans()` device VLAN fetch (`client.api.ipam.vlans.filter(id__in=chunk)`) is OUT of scope — Phase 30 targets `get_device_ips()` specifically.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — URI-01, URI-02, URI-03, URI-04, URI-05, URI-06

### Source files
- `nautobot_mcp/ipam.py` — `get_device_ips()` (L318-407), `list_ip_addresses()` (L87-192 — pattern source for direct HTTP + return_obj + pagination)
- `nautobot_mcp/client.py` — `NautobotClient` (HTTP session access at L161, `count()` method as precedent for direct HTTP L343-383)
- `nautobot_mcp/utils.py` — `chunked()` utility (pattern for chunking; new helper will follow similar style)

### Prior Phase Decisions
- `.planning/phases/29-direct-count-endpoint/29-CONTEXT.md` — `client.count()` pattern, HTTP session auth headers setup, `client._profile.url` usage
- `.planning/phases/28-adaptive-count-fast-pagination/28-CONTEXT.md` — HTTP session usage patterns, pynautobot `return_obj()` pattern
- `.planning/phases/21-workflow-contracts-error-diagnostics/21-CONTEXT.md` — `_handle_api_error` usage

### Models
- `nautobot_mcp/models/ipam.py` — `DeviceIPsResponse`, `DeviceIPEntry` Pydantic models

</canonical_refs>

<codebase_context>
## Existing Code Insights

### Reusable Assets
- `client.api.http_session` — authenticated HTTP session with `(10, 60)` timeout, `Authorization: Token` header already set
- `client._profile.url` — base URL for constructing full API paths
- `endpoint.return_obj(raw_dict, api, endpoint)` — wraps raw HTTP response dicts into pynautobot `Record` objects; available on `ip_address_to_interface`, `ip_addresses`, `interfaces`
- `client._handle_api_error()` — standard error translation; called at function level, not per-item

### Established Patterns
- Direct HTTP + `return_obj()` already exists in `list_ip_addresses()` L104-192 for interface list and non-device IP list paths
- `count()` in `client.py` L343-383 uses direct HTTP + `resp.json()` + 404 fallback — same pattern applies here
- Paginated HTTP responses: response dict has `{"results": [...], "next": "url|null"}` — loop while `next` is not None
- `chunked()` utility already exists in `utils.py` (used in `list_vlans()` for VLAN ID chunking)

### Integration Points
- `get_device_ips()` is called by `workflows.py` `get_device_ips` workflow stub and potentially by CLI
- No changes needed to `workflows.py` or `server.py` — function signature and return type remain the same
- `_bulk_get_by_ids()` helper should be placed in `ipam.py` before `get_device_ips()` (near the top of the module)

### Key Observations
- `list_ip_addresses()` L130-139 already does M2M fetch via direct HTTP for single-interface case — pattern is proven
- `return_obj` is available on all three endpoints involved: `interfaces`, `ip_address_to_interface`, `ip_addresses`
- Current Pass 1 (interface fetch) uses `client.api.dcim.interfaces.filter(device=device_name)` — not a 414 source, not in scope
- `unlinked_ips` field already exists in `DeviceIPsResponse` — currently always `[]`, will be populated by partial failure logic

</codebase_context>

<specifics>
## Specific Ideas

- `_bulk_get_by_ids()` helper should handle the `None`/`next` pagination loop cleanly
- `get_device_ips()` returns `DeviceIPsResponse(device_name, total_ips, interface_ips, unlinked_ips)` — keep the same Pydantic model
- Test device: HQV-PE1-NEW (700+ interfaces, likely 1000+ IPs) — used for v1.6/v1.7 performance validation

</specifics>

<deferred>
## Deferred Ideas

- `list_vlans()` device VLAN fetch using `client.api.ipam.vlans.filter(id__in=chunk)` — same pattern as Phase 30 but different function. Not in Phase 30 scope — note for Phase 31 or 32 consideration.
- Extracting `_bulk_get_by_ids()` and using it in `list_ip_addresses()` — Phase 30 implements the helper; using it in `list_ip_addresses()` is a cleanup that can be done separately.

</deferred>

---

*Phase: 30-direct-http-bulk-fetch*
*Context gathered: 2026-03-29*
