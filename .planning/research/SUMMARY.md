# Research Summary — v1.7 URI Limit Fix

**Date:** 2026-03-29
**Milestone:** Eliminate all 414 Request-URI Too Large errors and address VLANs 500 errors

## Root cause confirmed

**ipam.py — `get_device_ips()`:** Already chunked at 500 with `chunked()`, but pynautobot's `.filter(id__in=chunk)` and `.filter(interface=chunk)` expand lists into **repeated query params**:
```
?id__in=uuid1&id__in=uuid2&...  (~18 KB per chunk for 500 UUIDs)
```
With ~700 IPs on HQV-PE1-NEW → 2 chunks × ~18 KB → 414.

**bridge.py — `_execute_core()` + `_execute_cms()`:** Accept arbitrary `params` dict. Any caller (agent or external) can inject `id__in=[uuid1, ..., uuid10000]` → 414 on any endpoint. **HIGHEST severity finding.**

**All other `.filter()` call sites:** Pass scalar values (single device name, single interface ID) — safe.

## Fix strategy

**ipam.py:** Replace `.filter()` loops with direct `http_session.get()` using DRF comma-separated format:
```
?id__in=uuid1,uuid2,uuid3   (~3x shorter than repeated params)
```
Handle pagination by following `next` links.

**bridge.py:** Add `_guard_filter_params()` that converts list values in `__in` params to comma-separated strings and raises `NautobotValidationError` for lists > 500 items.

**VLANs 500:** Catch 500 errors in `count()` method, return `None` instead of raising.

## Stack

No new libraries. All patterns already exist in codebase:
- `client.api.http_session.get()` — direct HTTP (used in `list_interfaces()`)
- `endpoint.return_obj()` — pynautobot Record wrapping (used elsewhere)
- `chunked()` utility — already in `utils.py`

## Key decisions needed (during planning)

1. **Chunk size for direct HTTP path:** 500 (current) or 200 (safer)? Comma-separated at 500 ≈ 18 KB. 200 ≈ 7 KB. Safer route: 200.
2. **M2M endpoint comma-separated:** Must verify against real Nautobot. Fallback: smaller chunk size (100) with repeated params.
3. **Bridge guard behavior:** Raise error vs auto-chunk? Recommendation: raise error (auto-chunking would change semantics and hide bad caller patterns).

## Watch out for

1. Direct HTTP pagination — follow `next` links if present
2. M2M endpoint comma-separated format — test or fallback
3. Bridge guard breaking small-list callers — only reject > 500
4. VLANs 500 — catch and return `None`, don't raise
5. Unit testing direct HTTP paths — mock `http_session.get()`, not pynautobot

## Phases recommended

1. **Phase 30:** Fix `ipam.py get_device_ips()` — direct HTTP for M2M + IP bulk fetch
2. **Phase 31:** Fix `bridge.py` — `_guard_filter_params()` for both core and CMS paths
3. **Phase 32:** VLANs 500 mitigation + regression tests
