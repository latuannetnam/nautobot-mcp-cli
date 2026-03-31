# Pitfalls Research: CMS N+1 Query Elimination (v1.10)

**Domain:** MCP Server / Nautobot CMS Plugin / HTTP Concurrency
**Researched:** 2026-03-31
**Confidence:** HIGH

---

## Critical Pitfalls

### Pitfall 1: Sequential Per-Unit Family Loop — 700+ HTTP Calls per `get_interface_detail`

**What goes wrong:**
`get_interface_detail` (interfaces.py:690–692) calls `list_interface_families(client, unit_id=unit.id)` inside a sequential `for unit in units` loop. For a device like HQV-PE1-NEW with 709 interface units, this fires 709 sequential HTTP calls, each potentially triggering pynautobot's 1-record-per-page CMS pagination loop — turning a 2-second operation into 60+ seconds.

**Why it happens:**
`list_interface_units` already does the right thing — bulk-fetches all families for the device in one call (lines 69–83) and builds a `family_count_by_unit` dict. But `get_interface_detail` discards this and re-fetches per unit. The developer likely copied the pattern from `get_interface_unit` (which correctly does per-unit enrichment for a single unit) without realizing the composite already has the data.

**How to avoid:**
Restructure `get_interface_detail` to reuse `list_interface_units`'s bulk family data. The `list_interface_units` → `family_count_by_unit` lookup already covers the per-unit mapping. For `detail=True` mode, additionally bulk-fetch all VRRP groups for the device upfront (one call), then distribute in-memory. Never call a per-parent-ID function inside a loop over that parent's children.

**Warning signs:**
- `for <parent> in <parents>:` followed by `<child_endpoint>.filter(<parent>_id=<parent>.id)` — classic N+1 smell
- Any loop whose body contains `http` or network I/O (via pynautobot)
- A function named `list_X_for_Y` called inside a `for y in ys` loop

**Phase to address:** Phase 35 — `get_interface_detail` parallelization

---

### Pitfall 2: Per-Filter / Per-Policer Detail Loops in `get_device_firewall_summary`

**What goes wrong:**
`get_device_firewall_summary` (firewalls.py:707–733) runs two sequential loops in `detail=True` mode: `for fw_filter in filters_data:` → `list_firewall_terms(...)` and `for policer in policers_data:` → `list_firewall_policer_actions(...)`. For a device with 30 filters × 20 terms each, this is 30 + N sequential HTTP calls — one per filter/policer.

**Why it happens:**
Each filter's terms are a separate CMS endpoint with a FK relationship. The developer used the same pattern as the BGP composite (per-neighbor enrichment) without recognizing the filter/policer count as unbounded. Unlike BGP (which had a `detail=True` guard and `all_neighbors:` gate), the firewall detail path has no such throttle.

**How to avoid:**
Adopt the bulk-map-then-distribute pattern (already proven in `list_firewall_filters` for term_count):
1. Before the detail loop: bulk-fetch all `juniper_firewall_terms` for the device in one call → `terms_by_filter_id: dict[filter_id, list[FirewallTermSummary]]`
2. Before the detail loop: bulk-fetch all `juniper_firewall_policer_actions` for the device in one call → `actions_by_policer_id: dict[policer_id, list[FirewallPolicerActionSummary]]`
3. Inside the detail loop: lookup from the dict, not a new HTTP call

**Warning signs:**
- `detail=True` path contains a second `for <entity> in <entities>:` loop with a CMS endpoint call inside
- No bulk-fetch of child entities before the enrichment loop
- `detail=True` path has no independent size guard (unlike BGP's `all_neighbors:` gate)

**Phase to address:** Phase 36 — `get_device_firewall_summary` detail parallelization

---

### Pitfall 3: ThreadPoolExecutor Shares pynautobot's `http_session` — Mutable Session State

**What goes wrong:**
All threads in a `ThreadPoolExecutor` share the same `client.api.http_session` (a `requests.Session`). pynautobot's `Request` builds a fresh `PreparedRequest` per call, so the HTTP layer is safe. BUT: the session object itself carries mutable state — connection pools (`HTTPAdapter`), cookies, and any monkey-patches applied to it. If a future change adds cookie handling or session-level auth state, it becomes a race condition.

**Why it happens:**
Developers assume `requests.Session` is inherently thread-safe because each request is independent. It mostly is for read operations, but the session's `mounts`, `cert`, `trust_env`, and adapter state are shared. The existing code in `devices.py:374` uses `ThreadPoolExecutor(max_workers=3)` without acknowledging this shared state risk.

**How to avoid:**
1. Never add session-level mutations inside worker threads (e.g., `session.headers.update(...)`, `session.cookies.set(...)`)
2. Add a comment in the ThreadPoolExecutor block: `# Note: http_session is shared across threads. pynautobot Request objects are stateless; session-level mutations in workers are unsafe.`
3. Consider making `http_session` a module-level or explicit thread-local if future complexity warrants it
4. Keep `max_workers` conservative (≤5 for pynautobot; avoid >10 which can exhaust the server's connection limits)

**Warning signs:**
- Code inside a thread pool callback that reads `client.api.xxx` (read is fine) but especially writes to it
- `client.api` attributes being set inside worker threads
- `max_workers > 10` — risks server-side rate limiting and client connection pool exhaustion

**Phase to address:** Phase 35 — thread safety review alongside parallelization

---

### Pitfall 4: Dual-Retry Collision — pynautobot Manually Retries ON TOP of HTTPAdapter Defaults

**What goes wrong:**
pynautobot wraps every call in a manual retry loop: `for attempt in range(3): response = session.send(prepared_request)` (pynautobot/core.py). Simultaneously, `requests.Session`'s `HTTPAdapter` has `max_retries=0` by default — no retry. But if someone changes `adapter.max_retries = 3` (a common "fix" for flaky servers), pynautobot's 3 manual retries × HTTPAdapter's 3 retries = **9 total attempts per call**. At scale (700+ parallel calls), this balloons to thousands of server requests.

**Why it happens:**
The HTTPAdapter retry config is global and persistent. A developer who sets `adapter.max_retries = 3` to handle transient Nautobot errors in one place (e.g., the count endpoint) unknowingly applies it everywhere — including within a `ThreadPoolExecutor` running 500 parallel CMS calls. This interaction is silent because pynautobot's retries are internal and invisible.

**How to avoid:**
1. Never set `adapter.max_retries` globally on `http_session`. If retry behavior is needed, do it at the call site using a custom session or a retry wrapper.
2. Document: "pynautobot already implements 3 retries internally. Do not configure HTTPAdapter retries globally."
3. Add a unit test that asserts `http_session.adapters["https://"].max_retries == 0` to catch accidental changes.

**Warning signs:**
- Any code that touches `session.mount()` or `adapter.max_retries`
- HTTP logs showing 9 attempts per call (exponential backoff noise in server logs)
- Server-side 500s spiking coincident with CMS workflow runs

**Phase to address:** Phase 35 — global HTTP config audit before parallelization

---

### Pitfall 5: Adding ThreadPoolExecutor Without Error Partitioning — One Failure Wipes All

**What goes wrong:**
If 8 parallel threads are each fetching a batch of families and one thread raises a `NautobotAPIError`, the `as_completed()` loop may miss collecting results from other threads that already finished. In the worst case, the caller receives a partial result dict with some keys missing, and no error signal — the workflow returns "success" with incomplete data.

**Why it happens:**
The `concurrent.futures` pattern used in `devices.py` uses `ex.submit(fn, *args)` for each task and `future.result()` to retrieve results. If an exception is raised inside the thread, `future.result()` re-raises it. BUT: the order of `as_completed()` means if thread 1 fails before thread 2–8 complete, the code raises immediately without checking whether threads 2–8 have collected any results. Their data is discarded.

**How to avoid:**
1. Wrap each `future.result()` in a try/except that stores partial results in a dict keyed by the task identifier
2. After all futures complete (or a timeout), check the dict for completeness — if any key is missing, add a warning rather than raising immediately
3. Use a sentinel `None` or a `WarningCollector`-compatible entry for failed partitions so the response can still be built with a warning
4. Never use `future.result()` without a timeout in a workflow (add `.result(timeout=30)` to prevent indefinite hang on a stuck call)

**Warning signs:**
- `future.result()` called without a `try/except` around it
- No timeout on `.result()` — a slow/hung HTTP call hangs the entire workflow
- Missing completeness check after `as_completed()` loop

**Phase to address:** Phase 35 — error partition design before thread pool implementation

---

### Pitfall 6: Over-Parallelizing Unbounded CMS Collections — Server and Memory Pressure

**What goes wrong:**
Adding `max_workers=20` to parallelize 700 interface unit family fetches creates 20 concurrent HTTP requests to the CMS plugin. If the plugin's Postgres queries are unindexed (as evidenced by the 60s+ timeouts in v1.9 Phase 34), 20 simultaneous slow queries can destabilize the Nautobot server, cause OOM on the MCP client (holding 700 family objects in memory simultaneously), or trigger server-side connection pool exhaustion.

**Why it happens:**
The developer sees 700 sequential 100ms calls → 70s total, and reasons "20 parallel → 3.5s — huge win!" This math is correct only if the server can sustain 20 concurrent queries. The CMS plugin has already shown it cannot — the AF/policy endpoints time out at 60s even at limit=1 (v1.9 Phase 34).

**How to avoid:**
1. Keep `max_workers` at 3–5 for CMS composite operations — consistent with the existing `devices.py` pattern
2. Add a comment explaining: "max_workers=3 is conservative. The CMS plugin has shown slow query behavior at scale. Increasing this without load testing the target server is unsafe."
3. Instrument the parallel fetch with per-call timing; if any single call exceeds 5s, fall back to sequential (the current `_CMS_BULK_LIMIT = 200` pattern already provides the right fallback behavior)
4. Enforce a maximum partition size (e.g., max 200 items per thread batch) so memory usage is bounded

**Warning signs:**
- `max_workers` set to a value derived from a "speedup calculation" rather than empirical server load testing
- No timeout on individual thread futures
- Entire family/term/policer lists held in memory at once with no streaming or pagination

**Phase to address:** Phase 35 — worker count selection and load test before merging

---

### Pitfall 7: Per-Route Nexthop Fallback Still Triggers N+1 When Bulk Map Is Empty

**What goes wrong:**
`list_static_routes` (routing.py:96–120) bulk-fetches nexthops for all routes upfront, but has a backward-compatible fallback: if the bulk map has no entry for a route, it calls `cms_list(route=route.id)` per-route. This fallback is triggered when the bulk fetch returns no data (e.g., `nh_by_route` is empty because the query returned no nexthops). In that case, the code loops over every route and makes an individual HTTP call — even though the bulk fetch confirmed those individual calls will also return empty lists.

**Why it happens:**
The fallback exists to preserve old test mocks that expect per-route calls. But it runs unconditionally — it doesn't check whether the bulk map is actually populated or whether the per-route calls are likely to succeed. When `nh_by_route` is empty, the fallback fires for every route simultaneously.

**How to avoid:**
Replace the fallback with an explicit "empty" sentinel. After the bulk fetch:
```python
if not nh_by_route and not qnh_by_route:
    # Bulk fetch returned no nexthops for any route — populate empty lists
    # without making per-route calls (they will also be empty)
    for route in routes.results:
        route.nexthops = []
        route.qualified_nexthops = []
else:
    # Populate from bulk map; per-route fallback only for specific routes
    # that are genuinely missing (not globally absent)
    ...
```
Only call per-route `cms_list` for specific routes that are absent from the bulk map, and only when the bulk map is not globally empty.

**Warning signs:**
- Empty `nh_by_route` dict after bulk fetch — triggers fallback for all routes
- Test mocks that assert per-route calls happen even when bulk returns data
- `try/except pass` swallowing all errors without differentiating "no data" from "fetch error"

**Phase to address:** Phase 37 — `list_static_routes` fallback cleanup

---

### Pitfall 8: Per-Neighbor AF/Policy Loop in `get_device_bgp_summary` — False Guard

**What goes wrong:**
`get_device_bgp_summary` (routing.py:734–746) has a per-neighbor fallback: after bulk-fetching all AFs/policies, if `af_by_nbr` lookup returns empty and `af_keyed_usable` is True, it calls `list_bgp_address_families(client, neighbor_id=nbr.id)` per neighbor. This fires one HTTP call per neighbor when the bulk map's `neighbor_id` FK field is present but the lookup key doesn't match. At 50+ neighbors, this is a secondary N+1 inside the already-improved BGP composite.

**Why it happens:**
The guard `af_keyed_usable` is set by checking if any AF record's `neighbor_id` matches any neighbor's ID — but this is a global existence check, not a per-neighbor check. If some AFs exist globally but for a different set of neighbors than the current device, the guard passes but every per-device neighbor lookup still misses.

**How to avoid:**
Change the guard logic: `af_keyed_usable = len(af_by_nbr) > 0` — if the bulk map has any entries keyed by neighbor_id, use it. If it's completely empty, skip the per-neighbor loop entirely. Never loop per neighbor when the bulk result set is confirmed empty for all neighbors.

**Warning signs:**
- `af_keyed_usable` computed via `any()` over a comprehension — a set-membership check masquerading as a per-record check
- Per-entity lookup inside a `for entity in entities:` loop — N+1 even after bulk optimization
- Guard variable that can pass even when the bulk result is useless for the specific entity list

**Phase to address:** Phase 37 — BGP AF/policy guard fix

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| `try/except: pass` swallowing all errors in enrichment | Enrichment never blocks the main result | Silent data loss — caller doesn't know fields are missing | Never — use `WarningCollector` and a sentinel value |
| Per-parent-ID loop for enrichment (N+1 accepted as "correct") | Simpler code — each enrichment is isolated | 700 HTTP calls for a single workflow | Never for composite workflows |
| Global `_CMS_BULK_LIMIT = 200` for all CMS endpoints | Single constant, simple to manage | Some endpoints may handle 500 fine; others may fail at 200 | Only until per-endpoint tuning is validated |
| `object.__setattr__(obj, "terms", ...)` for extra Pydantic attributes | Avoids schema changes for enriched objects | Type checkers and IDE autocomplete miss these fields | Temporarily acceptable; long-term: dedicated enriched models |
| Sequential fallback when bulk returns empty | Preserves test compatibility | Still N+1 when bulk is empty | Only if per-route calls genuinely add data; never when bulk is globally empty |
| `model_dump()` only at composite response boundary | Deferred serialization decisions | pynantic Record objects may leak into intermediate dicts | Only acceptable if every intermediate step is also Pydantic model → dict |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| pynautobot + ThreadPoolExecutor | Assuming each `Endpoint` is independent — they share `api.http_session` | Treat the session as shared mutable state; no session-level mutations in workers |
| pynautobot + HTTPAdapter retries | Setting `adapter.max_retries` globally — collides with pynautobot's manual 3-retry loop → 9 attempts/call | Never set adapter retries globally; pynautobot handles retries internally |
| CMS plugin + ThreadPoolExecutor | Too many concurrent slow queries destabilizing the Nautobot server (CMS plugin has unindexed queries) | Keep `max_workers ≤ 5`; instrument with per-call timeouts; fall back to sequential on any 5s+ timeout |
| `cms_list` + ThreadPoolExecutor | Passing `NautobotClient` instance to workers — `client.api` is shared | Safe for reads; document that session-level writes in workers are prohibited |
| Bulk map + per-entity fallback | Per-entity fallback fires even when bulk is globally empty — wasted N calls that return nothing | Guard per-entity fallback with `if bulk_map:` check; never loop when bulk confirmed empty |
| VRRP enrichment in `get_interface_detail` | Fetching VRRP groups per-family inside the family loop — compounding N+1 | Fetch all VRRP groups for the device once before the unit loop; distribute via dict lookup |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Per-unit family fetch loop in `get_interface_detail` | 700+ sequential HTTP calls; CMS plugin PAGE_SIZE=1 causes 700+ page walks per family type | Bulk-fetch all families for device in one call; distribute via dict keyed by unit_id | At 100+ interface units |
| Per-filter term fetch loop in firewall detail mode | 30+ sequential calls when `detail=True`; each term lookup hits unindexed CMS query | Bulk-fetch all terms for device; distribute via dict keyed by filter_id | At 10+ firewall filters |
| Per-neighbor AF/policy fallback with weak guard | Bulk AF/policy fetch runs but returns no keyed results; fallback loops per neighbor anyway | `af_keyed_usable = len(af_by_nbr) > 0` — strict emptiness check | At 50+ BGP neighbors |
| Over-enthusiastic thread pool (`max_workers=20`) | Server-side OOM or connection exhaustion; 20 simultaneous unindexed CMS queries | Cap at 3–5 workers; add per-call 5s timeout; sequential fallback on timeout | At 100+ entity count |
| Unbounded in-memory collection of bulk results | MCP client OOM for large devices (700 units × families × VRRP) held simultaneously | Process and yield results incrementally; cap per-batch at 200 records | At 500+ interface units |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Thread pool making authenticated requests with a shared token | If session state is ever made mutable (cookies, token refresh), one thread's auth state could interfere with another's | Keep `NAUTOBOT_TOKEN` immutable; document that session mutation in workers is prohibited |
| pynautobot's `api.token` being re-read on every request | If token is ever refreshed or rotated during MCP server lifetime, worker threads with stale token references fail silently | Token is set once at init; pynautobot reads it per-request — this is safe as long as token rotation is not implemented |
| Sharing `client.api.http_session` across threads | Connection pool state is shared; one thread's failed request could affect another's in-flight requests | HTTPAdapter is thread-safe for the connection pool itself; risk is in any future session-level state (cookies, certs) |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Slow `get_interface_detail` on large devices (>100 units) silently returns partial data if one thread fails | User sees incomplete interface list with no error signal; thinks the device has no VRRP groups | Always use `WarningCollector` pattern; surface partial results with warnings in the response envelope |
| `get_device_firewall_summary --detail` takes 30s+ on devices with many filters; no progress indicator | User thinks the command is hung; cancels and retries — making server load worse | Log per-phase timing (coarse: "Fetching filters...", "Fetching terms...", "Fetching policers...") |
| Sequential N+1 patterns silently added in new enrichment features | Future developer adds per-entity enrichment inside a loop; CI passes because no performance test exists | Add `uat_cms_smoke.py` HTTP call count assertion per workflow; block PR if call count increases by >10% |
| Thread pool exceptions propagate as tracebacks with no context | User sees `Exception in thread worker-2: NautobotAPIError` with no indication which entity caused it | Catch exceptions per-future and attach entity identifier to warning message |

---

## "Looks Done But Isn't" Checklist

- [ ] **`get_interface_detail`:** Parallelization added — but verify it reuses `list_interface_units`'s bulk family map, not re-fetching per unit
- [ ] **`get_device_firewall_summary` detail path:** Bulk term/policer fetch added — but verify the detail loop does dict lookup, not per-entity HTTP calls
- [ ] **ThreadPoolExecutor added:** Workers are bounded (max_workers ≤ 5), per-call timeouts set, partial result dict checked for completeness
- [ ] **HTTPAdapter retries:** Confirmed `adapter.max_retries == 0`; pynautobot's 3-retry loop is the only retry mechanism
- [ ] **Per-route nexthop fallback:** Guarded with `if not nh_by_route` check; per-route calls only fire when bulk is populated but specific route is absent
- [ ] **BGP AF/policy per-neighbor fallback:** Guard uses `len(af_by_nbr) > 0` not `any()` comprehension — strict emptiness check
- [ ] **`uat_cms_smoke.py` call count assertions:** Updated with new expected HTTP call counts per workflow; blocked at <10% increase threshold
- [ ] **Error handling:** Every `future.result()` has try/except and contributes to warning dict; no bare `future.result()` without timeout

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Per-unit family loop causes 60s+ timeout | LOW — revert to sequential, accept slower performance | Set `max_workers=1` to force sequential; file bug for parallelization in next milestone |
| ThreadPoolExecutor causes session-level race condition | MEDIUM — server returns 500 for some concurrent calls | Set `max_workers=3` and add per-call 5s timeout; check server logs for connection pool exhaustion |
| Over-parallelization crashes Nautobot CMS plugin | HIGH — requires server restart | Immediately reduce `max_workers`; add server-side connection limit; notify server team |
| Per-route nexthop fallback fires for all routes | MEDIUM — adds N wasted HTTP calls per workflow | Add `if nh_by_route` guard before fallback; re-run smoke test to confirm |
| HTTPAdapter retry collision causes 9× request volume | MEDIUM — server load spikes; workflow is 9× slower | Remove global `adapter.max_retries` setting; verify `uat_cms_smoke.py` passes |
| Partial results returned without warning | LOW — user gets incomplete data but no error | Wrap all enrichment in `WarningCollector`; verify response envelope always includes `warnings` field |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Sequential per-unit family loop | Phase 35: `get_interface_detail` parallelization | `uat_cms_smoke.py` call count for `interface_detail` drops from 712 → <10 |
| Per-filter/policer detail loops | Phase 36: `get_device_firewall_summary` detail optimization | `uat_cms_smoke.py` call count for `firewall_summary --detail` drops 50%+ |
| Shared http_session thread safety | Phase 35: thread safety review | Unit test asserts `adapter.max_retries == 0`; code review sign-off on session sharing |
| Dual-retry collision | Phase 35: HTTP config audit | Unit test fails if `adapter.max_retries != 0`; integration test asserts 3 attempts max |
| ThreadPoolExecutor error partitioning | Phase 35: error partition design | Unit test: one worker raises; verify response has partial data + warning |
| Over-parallelization server pressure | Phase 35: worker count + load test | Smoke test on HQV-PE1-NEW (709 units); no 5xx; latency <5s |
| Per-route nexthop false fallback | Phase 37: routing fallback guard fix | Mock bulk returns empty; verify 0 per-route calls made |
| BGP AF/policy weak guard | Phase 37: BGP guard strictness fix | Mock AF bulk returns unkeyed; verify 0 per-neighbor calls made |

---

## Sources

- `nautobot_mcp/cms/interfaces.py` — `get_interface_detail` N+1 analysis (lines 658–761)
- `nautobot_mcp/cms/firewalls.py` — `get_device_firewall_summary` N+1 analysis (lines 654–750)
- `nautobot_mcp/cms/routing.py` — `get_device_bgp_summary` guard analysis (lines 639–779), `list_static_routes` fallback analysis (lines 46–128)
- `nautobot_mcp/cms/client.py` — `_CMS_BULK_LIMIT = 200` pattern; `cms_list` implementation
- `nautobot_mcp/devices.py` — ThreadPoolExecutor pattern (lines 374–384); `max_workers=3` precedent
- v1.9 Phase 34 validated decisions: AF/policy gated behind `detail=True AND all_neighbors:`; CLI limit 50→10
- v1.8 Phase 33 validated decisions: `_CMS_BULK_LIMIT = 200`; CMS plugin PAGE_SIZE=1 workaround

---
*Pitfalls research for: CMS N+1 Query Elimination (v1.10)*
*Researched: 2026-03-31*
