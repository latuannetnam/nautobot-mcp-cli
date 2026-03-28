# Phase 28: Adaptive Count & Fast Pagination - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix `devices inventory` slow performance for large devices by skipping `count()` calls when paginating, inferring `has_more` from result count, and adding `--no-count` CLI flag with timing instrumentation. Affects only the CLI path (`nautobot_mcp/cli/devices.py`) and the `get_device_inventory()` function (`nautobot_mcp/devices.py`).

Phase 29 handles: replacing ALL pynautobot `count()` calls with direct `/count/` endpoint usage, parallel counts in other modules, and MCP bridge timing.

</domain>

<decisions>
## Implementation Decisions

### has_more inference
- **D-01:** `has_more = len(results) == limit` when count is skipped. Exact `limit` results → `has_more = True`. Fewer than `limit` → `has_more = False`.

### null handling for total fields
- **D-02:** When count is skipped, `total_interfaces`/`total_ips`/`total_vlans` are set to `null` (JSON `null`, Python `None`). This is an honest signal — the count was not fetched. Agents should check for null.

### --no-count flag scope
- **D-03:** `--no-count` added to CLI (`nautobot_mcp/cli/devices.py`) AND `skip_count` parameter added to `get_device_inventory()` in `nautobot_mcp/devices.py`. Also added to MCP `call_nautobot` as a top-level parameter so agents can explicitly suppress count.

### Timing metadata granularity
- **D-04:** Per-section timing: `interfaces_latency_ms`, `ips_latency_ms`, `vlans_latency_ms`, `total_latency_ms`. Each section measured from API call start to result return. `total_latency_ms` is wall-clock from first call to final output.

### Parallel counts for detail=all
- **D-05:** When `--detail all` and count IS needed (not `--no-count`), fetch all 3 counts concurrently using `concurrent.futures.ThreadPoolExecutor`. Reuse the client API session. All 3 counted in parallel, wall-clock is max not sum.

### --limit 0 (unlimited) behavior
- **D-06:** `--limit 0` means unlimited. In this mode, skip all count operations (same as `--no-count`). Return all records with zero count overhead.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Key source files
- `nautobot_mcp/devices.py` — `get_device_inventory()` (L267-358), `get_device_summary()` (L228-264) — contains all count() calls and the has_more logic
- `nautobot_mcp/cli/devices.py` — `devices_inventory` CLI command (L146-194) — where --limit, --detail, --offset are parsed
- `nautobot_mcp/bridge.py` — `_execute_core()` (L149-191) — where `limit` and `offset` are passed to pynautobot

### Requirements
- `REQUIREMENTS.md` §"Count Optimization" — PERF-01, PERF-02
- `REQUIREMENTS.md` §"Observability" — OBS-01
- `REQUIREMENTS.md` §"CLI UX" — UX-01, UX-02

</canonical_refs>

<codebase_context>
## Existing Code Insights

### Reusable Assets
- `nautobot_mcp/client.py` — `NautobotClient` with `api` property returning pynautobot session. HTTP session is `client.api.http_session`. Timeout: (10, 60).
- `nautobot_mcp/models/device.py` — `DeviceInventoryResponse` Pydantic model with `total_interfaces`, `total_ips`, `total_vlans`, `has_more`, `limit`, `offset` fields. These are Optional to support null.

### Established Patterns
- `concurrent.futures.ThreadPoolExecutor` — used in `nautobot_mcp/cms/routing.py` for parallel BGP fetches. Pattern exists: `with ThreadPoolExecutor(max_workers=3) as ex:`.
- `time.time()` for latency — used in `nautobot_mcp/workflows.py` to track workflow latency.

### Integration Points
- `nautobot_mcp/workflows.py` — `get_device_inventory` is imported at L26. Workflow registry calls this function directly. Any signature changes must be backward compatible or registry must be updated.
- `nautobot_mcp/cli/devices.py` — `get_device_inventory()` called at L158. `detail` (string), `limit` (int), `offset` (int) passed. `--no-count` flag needs to be added here.
- `nautobot_mcp/bridge.py` — `call_nautobot` has `limit` and `offset` params (L330-331). `skip_count` should be added as a new top-level param here for MCP parity.

### Key Observations
- The misleading comment at `devices.py` L247 "`.count(device=name) hits /count/?device=... (OK)`" is WRONG. pynautobot `.count()` does NOT use the `/count/` endpoint — it uses auto-pagination. This is the root cause. Phase 29 fixes this at the source.
- For Phase 28, we work AROUND this by skipping the count() call entirely when limit > 0.
- `DeviceInventoryResponse` in `models/device.py` already has `Optional` fields for totals — no model change needed.
</codebase_context>

<specifics>
## Specific Ideas

- HQV-PE1-NEW has 700+ interfaces — test device for performance validation
- Performance target: `devices inventory HQV-PE1-NEW --limit 5` should return in <1 second after fix
- Timing metadata should be added only in `--json` output mode (not in text/table mode)

</specifics>

<deferred>
## Deferred Ideas

None — all decisions captured above.

</deferred>

---

*Phase: 28-adaptive-count-fast-pagination*
*Context gathered: 2026-03-28*
