# Stack Research

**Domain:** Python concurrency / HTTP parallelization for pynautobot-based Nautobot API clients
**Researched:** 2026-03-31
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `concurrent.futures.ThreadPoolExecutor` | stdlib (Python 3.11+) | Parallel HTTP calls within a single workflow | Already in the stdlib; zero dependency; used successfully in `devices.py` for parallel counts |
| pynautobot `threading=True` API flag | pynautobot ≥ 2.3.0 | Per-page parallel pagination | Built-in ThreadPool inside pynautobot's `Request.concurrent_get()`; activates when `page_size > 1` |
| pynautobot `max_workers=N` | pynautobot ≥ 2.3.0 | Controls ThreadPool size for parallel pagination | Tunable concurrency level; defaults to 4 |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `concurrent.futures.ThreadPoolExecutor` | stdlib | Parallelize independent CMS endpoint calls within a composite workflow | When N CMS domain calls are known upfront (e.g., families + VRRP + ARP fetched in parallel for `get_interface_detail`) |
| `concurrent.futures.as_completed` | stdlib | Collect results as futures resolve | When you need partial results if one call fails but others succeed |
| `requests.Session` (via `api.http_session`) | requests (pynautobot dep) | Shared session for direct HTTP calls | When bypassing pynautobot for raw bulk fetch (`_bulk_get_by_ids`) |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `pytest` + `pytest-asyncio` | Test framework | Already in dev deps; asyncio not needed for the concurrency patterns described here |
| `respx` | Mock HTTP responses | Already in dev deps; use to test ThreadPoolExecutor paths without live server |
| `inspect.getsource` | Verify pynautobot internals | Use to confirm threading path is triggered; avoids assumptions |

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|------------------------|
| `ThreadPoolExecutor` (stdlib) | `asyncio` + `aiohttp` / `httpx.AsyncClient` | `asyncio` requires async/await rewrite of all CMS domain sync functions; asyncio event loop cannot directly call `pynautobot` (sync-only) without `run_in_executor` wrapping everywhere; adds `aiohttp` dep for marginal benefit given the codebase's current architecture |
| `ThreadPoolExecutor` (stdlib) | `multiprocessing` | Wrong tool — HTTP I/O is not CPU-bound; processes add IPC overhead with no benefit |
| pynautobot `threading=True` (bulk) | Raw `httpx` client | Would require full pynautobot replacement; loses all Nautobot model abstraction |
| pynautobot `threading=True` (bulk) | `urllib3.ThreadPool` | Deprecated in favor of `concurrent.futures`; pynautobot itself uses `concurrent.futures` |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `asyncio` / `aiohttp` / `httpx.AsyncClient` | Requires async/await rewrite of all CMS domain sync functions; asyncio event loop cannot directly call `pynautobot` (sync-only) without `run_in_executor` wrapping everywhere; adds `aiohttp` dep for marginal benefit given the codebase's current architecture | `ThreadPoolExecutor` — drop-in for independent I/O calls |
| `multiprocessing.Pool` | HTTP I/O is I/O-bound, not CPU-bound; process spawning adds ~100ms overhead per worker with zero throughput gain | `ThreadPoolExecutor` |
| `gevent` / `greenlet` | Patches stdlib at import time; conflicts with pynautobot's `requests` transport; breaks `concurrent.futures` in subtle ways | `ThreadPoolExecutor` |
| Raw `httpx` client | Would replace pynautobot entirely; loses Nautobot model abstraction, error translation, and all existing CMS domain logic | Stay on pynautobot, use `http_session` for direct bulk fetches |
| pynautobot `threading=True` **alone** when PAGE_SIZE=1 | Even with `threading=True`, pynautobot's `Request.concurrent_get()` fires workers for each page; if Nautobot CMS plugin caps at PAGE_SIZE=1, you still get N sequential HTTP calls — just in parallel threads that all wait on the same slow single-record endpoint | `_CMS_BULK_LIMIT = 200` first (fixes page size), THEN `threading=True` for pagination-level parallelism |
| `concurrent.futures.ProcessPoolExecutor` | Same as `multiprocessing.Pool` — wrong for I/O-bound work |

---

## Stack Patterns by Variant

**If CMS endpoint has PAGE_SIZE=1 (N+1 pattern, the current situation):**
- Fix page size via `_CMS_BULK_LIMIT = 200` kwarg in `cms_list()` — collapses N sequential HTTP calls into `ceil(N/200)` calls
- Use `ThreadPoolExecutor(max_workers=N)` for independent multi-endpoint fetches within a composite workflow
- Do NOT rely on pynautobot's `threading=True` alone — it parallelizes pages but pages are still 1 record each

**If CMS endpoint has PAGE_SIZE ≥ 10 (after fix applied):**
- Enable pynautobot `threading=True` on the `Api` instance for bulk pagination parallelism
- pynautobot's `Request.concurrent_get()` uses `ThreadPoolExecutor(max_workers=4)` to fetch pages in parallel
- Each page still fetches 10–200 records in one HTTP call

**If CMS workflow has K independent domain calls (e.g., fetch families AND VRRP AND ARP simultaneously):**
- Use `ThreadPoolExecutor(max_workers=K)` to fire all K calls at once
- Use `as_completed()` to collect results — if one fails, others still succeed
- This pattern is already used in `devices.py` for parallel counts

**If using direct HTTP (`http_session.get()`) for bulk by-ID fetch:**
- Use DRF comma-separated UUIDs: `?id=uuid1,uuid2,uuid3` (not `?id=uuid1&id=uuid2&id=uuid3`)
- This is what `_bulk_get_by_ids()` already does
- Do NOT add threading here — single bulk call is already optimal

---

## Version Compatibility

| Package | Version | Compatible With | Notes |
|---------|---------|-----------------|-------|
| pynautobot | ≥ 2.3.0 | Python ≥ 3.11 | `threading` and `max_workers` params on `Api` class confirmed in 3.0.0; earlier versions may not have these |
| pynautobot | 3.0.0 | Python ≥ 3.9 | Current version in `pyproject.toml` constraint `>= 2.3.0`; installed version is 3.0.0 |
| `concurrent.futures` | stdlib | All Python 3.11+ | No version constraint needed; no extra dep |
| requests | via pynautobot dep | Any | `http_session` is a `requests.Session`; thread-safe |
| `pytest-asyncio` | in dev deps | pytest ≥ 7.0 | Not needed for sync ThreadPoolExecutor patterns; only if async work added later |

---

## Key Findings from Codebase

### pynautobot threading architecture

pynautobot's `Api` class accepts `threading=True` and `max_workers=4` (default). When enabled:

1. `Endpoint.filter()` / `Endpoint.all()` create a `Request(threading=True, max_workers=N)` object
2. `Request.get()` checks `if self.threading:` and calls `req_all_threaded()`
3. `req_all_threaded()` uses `cf.ThreadPoolExecutor(max_workers=self.max_workers)` to fire `_make_call` for each page **simultaneously**
4. Results are assembled in order before being returned

**Critical constraint:** Threading works at the **page level**, not the record level. If each page returns 1 record (PAGE_SIZE=1), 4 workers still means 4 × 1-record HTTP calls fired in parallel — but the Nautobot CMS plugin caps PAGE_SIZE=1, so you get the same number of HTTP calls, just across 4 threads instead of 1. The `_CMS_BULK_LIMIT = 200` kwarg bypasses this by setting `limit=200` on the first call, fetching 200 records in 1 HTTP call.

### Existing patterns in the codebase

| File | Pattern | Status |
|------|---------|--------|
| `devices.py` `get_device_inventory()` | `ThreadPoolExecutor(max_workers=3)` for 3 parallel count operations | ✅ Validated (v1.6) |
| `cms/client.py` `_CMS_BULK_LIMIT = 200` | Bulk fetch workaround for PAGE_SIZE=1 | ✅ Validated (v1.8 Phase 33) |
| `cms/client.py` `_bulk_get_by_ids()` | Direct HTTP bulk fetch with DRF comma-separated UUIDs | ✅ Validated (v1.7 Phase 30) |
| `cms/routing.py` `get_device_bgp_summary()` | 3-phase: bulk map → keyed lookup → per-item fallback | ✅ Validated (v1.9 Phase 34) |

### N+1 patterns still present in CMS composites (v1.10 scope)

| Location | Pattern | Fix |
|----------|---------|-----|
| `interfaces.py` `get_interface_detail()` — `list_interface_families` per unit | Sequential loop over units → N HTTP calls to families endpoint | Pre-fetch all families in 1 bulk call, then build dict keyed by unit_id |
| `interfaces.py` `get_interface_detail()` — `_get_vrrp_for_family` cached but called per family | 1 HTTP call per family in detail mode | Pre-fetch all VRRP groups in 1 bulk call, then dict lookup |
| `interfaces.py` `get_interface_unit()` — all_filters / all_policers no device filter | Fetch all filters/policers globally (no device scope) | Scope by device_id if endpoint supports it; otherwise parallelize via ThreadPoolExecutor |
| `routing.py` `list_static_routes()` — per-route nexthop fallback | "Backward-compatible fallback" calls nexthop endpoint per route | This is a fallback path only (runs when bulk map misses); optimize the bulk path first |
| `routing.py` `list_bgp_neighbors()` — fallback loop over groups | Per-group neighbor fetch in fallback path only | Already has direct device-scoped fetch as primary path; optimize only if fallback is frequently hit |

---

## Sources

- pynautobot 3.0.0 `Api.__init__` docstring — `threading` and `max_workers` params confirmed
- pynautobot 3.0.0 `Request.concurrent_get()` — uses `concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)`
- pynautobot 3.0.0 `Endpoint.filter()` — passes `threading=self.api.threading` to `Request`
- `devices.py` lines 374–393 — existing `ThreadPoolExecutor(max_workers=3)` for parallel counts (v1.6)
- `cms/client.py` line 23 — `_CMS_BULK_LIMIT = 200` constant
- `cms/client.py` `cms_list()` — `limit=0 → limit=200` via kwarg
- PROJECT.md v1.8 Phase 33 — PAGE_SIZE=1 root cause identified
- PROJECT.md v1.9 Phase 34 — AF/policy 60s+ timeout fix, 5/5 UAT PASS

---
*Stack research for: CMS N+1 Query Elimination (v1.10)*
*Researched: 2026-03-31*
