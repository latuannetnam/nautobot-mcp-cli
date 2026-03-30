# Research Summary — v1.8 CMS Pagination Fix

**Date:** 2026-03-30
**Milestone:** Fix N+1 pynautobot pagination in CMS composite functions

## Root cause confirmed

`list_bgp_address_families(limit=0)` → pynautobot sends **no `limit` param** (limit=0 is falsy) → Nautobot CMS plugin uses PAGE_SIZE=1 → pynautobot follows `next` links one record at a time → **151 sequential HTTP calls** (~80s).

## Key findings

1. **No `page_size` attribute on pynautobot `Endpoint`** — only `Request(limit=N)` controls pagination
2. **`limit=0` means "no limit sent"** — not "fetch all with default" — bug in pynautobot's interaction with small-page-size plugins
3. **Fix: pass `_CMS_BULK_LIMIT = 200`** when `limit == 0` in `cms_list()`
4. **Single fix point**: `nautobot_mcp/cms/client.py::cms_list()` — all 38+ CMS list operations benefit automatically
5. **No thread safety risk** — `limit` passed per-call, dies with the `Request`

## Stack additions

None. Fix is entirely within existing `cms_list()` in `nautobot_mcp/cms/client.py`.

## Watch out for

1. **Setting `endpoint.page_size`** — silently ignored, not the right approach
2. **Overriding `limit > 0`** — violates caller intent, only override `limit == 0`
3. **Setting `limit` too high (e.g., 1000)** — server may cap lower and return 400/422
4. **Bypassing pynautobot with direct HTTP** — loses retries and error translation
5. **New list functions bypassing `cms_list()`** — silent regression, prevent via code review
