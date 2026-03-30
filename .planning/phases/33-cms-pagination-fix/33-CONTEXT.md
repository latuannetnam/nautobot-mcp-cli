# Phase 33: CMS Pagination Fix - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix N+1 pynautobot pagination in CMS composite functions. When `limit=0` (get all), pynautobot's `Endpoint.all()` / `.filter()` discovers the total count then follows pagination links. If the CMS plugin has `PAGE_SIZE=1`, 151 records = 151 sequential HTTP calls (~80s). Fix: set `endpoint.limit = 200` before calling `.all()` or `.filter()` so each page fetches 200 records instead of 1.

Scope: `cms_list()` in `nautobot_mcp/cms/client.py` only.
Out of scope: modifying `cms_get()`, bulk HTTP changes (already done in Phase 30), bridge param guard (already done in Phase 31).

</domain>

<decisions>
## Implementation Decisions

### Page Size Override Mechanism
- **D-01:** `endpoint.limit = 200` before `.all()` / `.filter()` when `limit=0`. pynautobot 3.0.0's concurrent fetch uses `Request.limit` as the page size parameter. Setting it on the endpoint object before calling `.all()` / `.filter()` overrides the default. This is the mechanism used to collapse N sequential single-record calls into ceil(N/200) larger-page calls.
- **D-02:** `_CMS_BULK_LIMIT = 200` defined as a module-level constant in `cms/client.py`. Named with `_CMS_BULK_LIMIT` prefix to indicate its CMS-specific purpose. Documented with rationale: Nautobot cap, CMS plugin PAGE_SIZE=1 compatibility, conservative safety margin.
- **D-03:** Override is unconditional — always applied when `limit=0`, regardless of endpoint. No endpoint-specific registry or conditional application needed. `juniper_bgp_address_families` is confirmed slow (151 records, PAGE_SIZE=1 on HQV-PE1-NEW); applying 200 broadly handles it and any similar endpoints.

### Discovery Strategy
- **D-04:** No endpoint-specific slow registry needed. Apply `_CMS_BULK_LIMIT = 200` universally when `limit=0` in `cms_list()`. Only `juniper_bgp_address_families` is empirically confirmed slow. If other endpoints are found slow during regression testing, they are handled by the same fix without code changes.
- **D-05:** Discovery artifacts: researcher should verify the fix works by running `uat_cms_smoke.py` before and after, and record HTTP call counts. Findings written to Phase 33 summary.

### Regression Prevention
- **D-06:** `uat_cms_smoke.py` uses per-workflow timing thresholds. Thresholds set at 2x the empirically observed time after the fix is applied. Researcher measures actual post-fix times for each workflow, then sets thresholds in the smoke script.
- **D-07:** `uat_cms_smoke.py` committed and pushed to repository. CI/CD integration is out of scope for Phase 33.

### Claude's Discretion
- Exact pynautobot version compatibility (tested against 3.0.0; any 3.x should work)
- Whether to set `endpoint.limit = None` after the call to avoid polluting shared state (researcher to verify no side effects)
- Specific threshold values for each workflow (deferred to empirical measurement)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 33 Requirements
- `.planning/ROADMAP.md` §v1.8 — Phase 33 goal: fix N+1 pynautobot pagination via `_CMS_BULK_LIMIT = 200` override in `cms_list()`
- `.planning/REQUIREMENTS.md` §PAG/DISC/REG — PAG-01..PAG-06 (pagination), DISC-01..DISC-02 (discovery), REG-01..REG-03 (regression)

### Prior Phase Decisions
- `.planning/phases/31-bridge-param-guard/31-CONTEXT.md` — Phase 31 decisions, `_guard_filter_params()` pattern, error handling conventions
- `.planning/phases/30-direct-http-bulk-fetch/30-CONTEXT.md` — Phase 30 decisions, direct HTTP patterns
- `.planning/phases/16-rest-bridge-universal-crud/16-CONTEXT.md` — Bridge architecture, pynautobot accessor pattern

### Root Cause Context
- `.planning/STATE.md` — Root cause: `list_bgp_address_families(limit=0)` → 151 sequential HTTP calls (PAGE_SIZE=1 on HQV-PE1-NEW)
- `scripts/uat_cms_smoke.py` — existing smoke test script, 5 workflows on HQV-PE1-NEW

### Codebase References
- `nautobot_mcp/cms/client.py` — `cms_list()` function (L128-159) — the primary fix target
- `nautobot_mcp/cms/client.py` — `get_cms_endpoint()` (L107-125) — returns pynautobot endpoint accessor
- `nautobot_mcp/cms/routing.py` — `list_bgp_address_families()` and other CMS list functions — call sites of `cms_list(limit=0)`
- `nautobot_mcp/workflows.py` — CMS workflow handlers that call CMS list functions

</canonical_refs>

 benef
## Existing Code Insights

### Reusable Assets
- `cms_list()` in `nautobot_mcp/cms/client.py` — single choke point for all CMS list operations; fix applied here covers all CMS composite functions
- `get_cms_endpoint()` — returns pynautobot endpoint accessor; the `endpoint.limit` attribute is set on this object
- `uat_cms_smoke.py` — existing smoke test infrastructure; threshold mechanism already exists, just needs per-workflow values

### Established Patterns
- Module-level constants defined in `client.py` (e.g., `_CMS_BULK_LIMIT` to be added) — follows existing pattern for numeric constants
- `WarningCollector` in `workflows.py` — used for accumulating per-workflow warnings; pattern for structured metadata
- Error handling via `client._handle_api_error()` in `cms_list()` — already handles exceptions, no change needed

### Integration Points
- All CMS domain modules call `cms_list()`: `routing.py`, `interfaces.py`, `firewalls.py`, `policies.py`, `arp.py`, `cms_drift.py`
- CLI commands in `nautobot_mcp/cli/` call these CMS functions with `limit=0`
- MCP workflows call these CMS functions via `nautobot_run_workflow`

### Creative Options
- Option to use `endpoint.return_obj` to wrap raw responses instead of model conversion (not applicable — existing `from_nautobot()` pattern is correct)
- Conditional application based on endpoint name (rejected — apply universally when `limit=0`)

</code_context>

<specifics>
## Specific Ideas

- "Juniper BGP address families is the confirmed slow endpoint — 151 records at PAGE_SIZE=1 on HQV-PE1-NEW caused ~80s latency. This is the primary regression target."
- "Do not bulk-fetch unbounded result sets — large fetches impact both Nautobot server and MCP client memory. 200 is conservative."
- "Smoke test threshold for bgp_summary: was 80s, should be < 5s after fix."

</specifics>

<deferred>
## Deferred Ideas

### Reviewed Todos (not matched)
None — no pending todos matched Phase 33 scope.

### Scope Deferred
- CI/CD integration for `uat_cms_smoke.py` — deferred to future phase (not in Phase 33 scope)
- Endpoint-specific slow registry (CMS_SLOW_ENDPOINTS) — rejected in favor of universal application

</deferred>

---

*Phase: 33-cms-pagination-fix*
*Context gathered: 2026-03-30*
