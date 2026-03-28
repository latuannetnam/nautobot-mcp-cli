# Phase 29: Direct /count/ Endpoint & Consistency - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace all pynautobot `.count()` calls with O(1) direct `/count/` endpoint usage via a new `NautobotClient.count()` method; add `latency_ms` to the `nautobot_call_nautobot` response envelope. Affects `devices.py` (get_device_summary), `bridge.py` (_execute_core, call_nautobot), and wires skip_count through the bridge. Phase 28 already plumbed `skip_count` through CLI → `get_device_inventory()` → `call_nautobot` param.

</domain>

<decisions>
## Implementation Decisions

### Direct count method design
- **D-01:** Add `NautobotClient.count(app, endpoint, **filters)` method using the HTTP session directly against `GET /<app>/<endpoint>/count/` endpoint. Returns an integer count in O(1) time.
- **D-02:** `client.count()` bypasses pynautobot's `.count()` auto-pagination entirely. Uses `client.api.http_session` directly.
- **D-03:** `client.count()` raises on HTTP errors — delegates error handling to the existing `_handle_api_error` pattern.

### Replacement scope
- **D-04:** `get_device_summary()` in `devices.py` — replace `client.api.dcim.interfaces.count(device=name)`, `client.api.ipam.ip_addresses.count(device_id=uuid)`, and `client.api.ipam.vlans.count(location=...)` with `client.count("dcim", "interfaces", device=name)` etc.
- **D-05:** `get_device_inventory()` parallel block and sequential fallback in `devices.py` — replace the remaining `vlans.count(location=...)` call with `client.count("ipam", "vlans", location=...)`.
- **D-06:** All remaining `count()` calls in the codebase (if any exist after Phase 28) are replaced with `client.count()`.

### skip_count wiring in bridge
- **D-07:** `skip_count` param in `call_nautobot` is wired through `_execute_core` — when `skip_count=True`, `_execute_core` skips any count() operations in its execution path. (Phase 28 added the param but didn't wire it.)

### latency_ms in bridge response
- **D-08:** `_execute_core` and `_execute_cms` return `latency_ms` as a single float (wall-clock ms) in their result dicts.
- **D-09:** `call_nautobot` passes `latency_ms` through to the MCP tool response dict, always present on every call.

### Claude's Discretion
- Exact HTTP session usage (what timeout/headers to pass to the direct /count/ request)
- Error handling details for edge cases (e.g., endpoint doesn't support /count/)
- Test coverage approach

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 28 (prior context)
- `.planning/phases/28-adaptive-count-fast-pagination/28-CONTEXT.md` — prior decisions, skip_count plumbing, has_more inference

### Source files to modify
- `nautobot_mcp/client.py` — add `count()` method; read HTTP session access pattern (L159: `client.api.http_session.timeout`)
- `nautobot_mcp/devices.py` — `get_device_summary()` L228-264 and `get_device_inventory()` L267-463 count() calls
- `nautobot_mcp/bridge.py` — `_execute_core()` L149-191 (add latency_ms), `_execute_cms()` L236-319 (add latency_ms), `call_nautobot()` L322-399 (wire skip_count)
- `nautobot_mcp/server.py` — `nautobot_call_nautobot()` L104-151 tool definition (docstring update for latency_ms)

### Requirements
- `REQUIREMENTS.md` §"Count Optimization (PERF)" — PERF-03 (direct /count/ fallback), PERF-04 (replace all count() calls)
- `REQUIREMENTS.md` §"Observability (OBS)" — OBS-02 (latency_ms in call_nautobot)

### Architecture context
- `ROADMAP.md` §"Phase 29" — goal, success criteria, requirements mapping

</canonical_refs>

<codebase_context>
## Existing Code Insights

### Reusable Assets
- `nautobot_mcp/client.py` — HTTP session at `client.api.http_session` (L159: `timeout=(10, 60)`). Used for direct API calls bypassing pynautobot.
- `ThreadPoolExecutor` pattern — already used in `devices.py` L354 for parallel counts. Can be reused if needed.
- `time.time()` — used throughout Phase 28 for `*_latency_ms` fields.

### Established Patterns
- `client._handle_api_error()` — standard error translation pattern used across all modules. `count()` should use this for error handling.
- `skip_count` param — already accepted by `call_nautobot`, `get_device_inventory`, and CLI. Needs to be wired through `_execute_core`.
- Workflow registry — `devices_inventory` workflow already maps `skip_count` (workflows.py L174). No registry changes needed.

### Integration Points
- `nautobot_mcp/workflows.py` — `WORKFLOW_REGISTRY["devices_inventory"]` already passes `skip_count`. No changes needed there.
- MCP tool signature — `nautobot_call_nautobot` in `server.py` already accepts `skip_count`. Need to ensure docstring reflects `latency_ms` in response.
- Phase 28 timing: `get_device_inventory()` already returns `total_latency_ms`. `call_nautobot` latency_ms is independent (lower-level).

### Key Observations
- `get_device_summary()` is a separate fast path from `get_device_inventory()`. It always counts (no skip_count option) — so it should use `client.count()` for O(1) performance instead of pynautobot's O(n).
- CMS `cms/client.py` uses `cms_list()` and `cms_get()` which don't call `count()` — CMS paths don't need count optimization.
- The bridge's `_execute_core` currently returns `{"count": len(results), "results": results}`. Adding `latency_ms` here makes it available to all callers of `call_nautobot`.

</codebase_context>

<specifics>
## Specific Ideas

- HQV-PE1-NEW (700+ interfaces) — test device for performance validation
- Performance target: `get_device_summary()` with 700+ interfaces should return in <1 second
- `latency_ms` should be added as a top-level key in the `call_nautobot` response dict, not nested

</specifics>

<deferred>
## Deferred Ideas

None — all Phase 29 scope decisions captured.

</deferred>

---

*Phase: 29-direct-count-endpoint*
*Context gathered: 2026-03-28*
