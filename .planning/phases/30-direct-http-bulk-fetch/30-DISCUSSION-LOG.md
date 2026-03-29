# Phase 30: Direct HTTP Bulk Fetch - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 30-direct-http-bulk-fetch
**Areas discussed:** Comma-separated strategy, Code reuse, Error handling

---

## Gray Area 1: Comma-separated Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Comma-separated direct HTTP, no fallback | Replace both `.filter()` loops with direct HTTP + comma-separated UUIDs. No chunking fallback. | ✓ |
| Comma-separated + chunking fallback | Attempt comma-separated, fall back to chunked `.filter()` if M2M fails. More defensive. | |

**User's choice:** Comma-separated direct HTTP, no fallback
**Notes:** DRF comma-separated format works for `ip_address_to_interface` — `return_obj` is available on this endpoint. No fallback needed (URI-06's chunking strategy not required).

---

## Gray Area 2: Code Reuse

| Option | Description | Selected |
|--------|-------------|----------|
| Copy pattern inline | Implement direct HTTP + `return_obj()` logic directly in `get_device_ips()`, no new helper. Simpler to read. | |
| Extract `_bulk_get_by_ids()` helper | Reusable helper function that does direct HTTP + comma-separated IDs + `return_obj()` + pagination. Used by both `get_device_ips()` and `list_ip_addresses()`. | ✓ |

**User's choice:** Extract `_bulk_get_by_ids()` helper
**Notes:** Cleaner architecture; `list_ip_addresses()` L104-192 already shows the pattern. The helper should be placed in `ipam.py` before `get_device_ips()`.

---

## Gray Area 3: Error Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Top-level `_handle_api_error` only | Any errors surface via `_handle_api_error` at top level. M2M and IP passes are all-or-nothing. | |
| Partial failure tolerance for IPs | Individual IP lookup failures (deleted IPs) collected in `unlinked_ips` rather than crashing. M2M all-or-nothing, IP detail partially tolerant. | ✓ |

**User's choice:** Partial failure tolerance for individual IPs
**Notes:** `DeviceIPsResponse` already has `unlinked_ips` field (currently always `[]`). IP detail fetch failures (e.g., IP deleted between M2M scan and detail fetch) should be caught and added to `unlinked_ips` rather than crashing. Hard failures (500, auth) still propagate via `_handle_api_error`.

---

## Deferred Ideas

- `list_vlans()` device VLAN fetch using `client.api.ipam.vlans.filter(id__in=chunk)` — same pattern but different function. Out of Phase 30 scope (Phase 31 or 32 consideration).
- Using `_bulk_get_by_ids()` in `list_ip_addresses()` — Phase 30 defines the helper; applying it to `list_ip_addresses()` is a cleanup.

---

*Log created: 2026-03-29*
