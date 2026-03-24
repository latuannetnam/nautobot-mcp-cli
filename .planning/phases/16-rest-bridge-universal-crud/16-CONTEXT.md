# Phase 16: REST Bridge & Universal CRUD - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the universal `call_nautobot` tool that dispatches CRUD operations to the correct backend based on endpoint prefix. This includes:
- Endpoint validation against catalog before dispatch
- Routing: `/api/*` → pynautobot core, `cms:*` → CMS plugin helpers
- Auto-pagination for GET operations with hard cap
- Device name → UUID auto-resolution for CMS endpoints
- HTTP error translation with structured hints and "did you mean?" suggestions
- Unit tests for routing, validation, error hints, and existing test suite passing

</domain>

<decisions>
## Implementation Decisions

### Endpoint Routing & Dispatch
- **Direct pynautobot accessor** for core endpoints — parse `/api/dcim/devices/` → `client.api.dcim.devices`, call `.all()`, `.get()`, `.create()` directly. No domain module indirection.
- **Claude's discretion** for CMS dispatch approach — may use existing `cms_list/get/create/update/delete` helpers or raw pynautobot CMS accessor, whichever produces the cleanest implementation.
- **`plugins:*` routing deferred** — Phase 16 covers only `/api/*` and `cms:*` prefixes. Generic plugin routing (`plugins:*`) deferred to a future phase when there's concrete need beyond golden_config (which is only used by workflows in Phase 17).

### Response Format & Serialization
- **Raw pynautobot dicts** — bridge is a thin passthrough, no Pydantic transformation or field flattening. Agent sees the real Nautobot API shape.
- **Wrapped response** — all responses wrapped in `{"count": N, "results": [...], "endpoint": "...", "method": "..."}` plus truncation indicators (`"truncated": true, "total_available": N`) when applicable. Matches the `ListResponse` pattern established in CMS domain modules.

### Error Hints & "Did You Mean?"
- **`difflib.get_close_matches()`** for fuzzy endpoint suggestions — stdlib, zero external dependencies. Used when agent passes an invalid endpoint to suggest closest valid matches.
- **Structured errors with endpoint context** — error responses include the endpoint called, method used, and an actionable hint. Reuses existing `NautobotMCPError.to_dict()` pattern from `exceptions.py`.

### Auto-Pagination
- **Auto-paginate up to `limit`** — follow Nautobot's `next` links, collecting results until `limit` is reached. If more results exist beyond `limit`, include `"truncated": true, "total_available": N` in the response.
- **Hard cap at 200** — if agent passes `limit` > 200, silently cap at 200 and note in response. Prevents agents from flooding their own context window.

### Claude's Discretion
- CMS dispatch approach (existing helpers vs raw accessor)
- Internal code organization within `bridge.py`
- Endpoint parsing implementation details (regex vs split)
- Validation caching strategy (catalog lookup frequency)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture
- `docs/plans/2026-03-24-api-bridge-mcp-design.md` — Full API Bridge architecture design v2 (approved). Defines 3-tool interface, catalog format, routing logic, workflow classification. §Tool 2 (`call_nautobot`) is the primary reference for this phase.

### Requirements
- `.planning/REQUIREMENTS.md` §REST Bridge (BRG) — BRG-01 through BRG-07
- `.planning/REQUIREMENTS.md` §Testing (TST) — TST-01 (existing tests pass), TST-03 (new `test_bridge.py`)

### Existing Code
- `nautobot_mcp/catalog/engine.py` — `get_catalog()` function for endpoint validation
- `nautobot_mcp/catalog/core_endpoints.py` — Static core endpoint definitions (dcim, ipam, circuits, tenancy)
- `nautobot_mcp/cms/client.py` — `CMS_ENDPOINTS` registry (38+ entries), `resolve_device_id()`, generic CRUD helpers (`cms_list/get/create/update/delete`), `get_cms_endpoint()`
- `nautobot_mcp/client.py` — `NautobotClient` with `_handle_api_error()`, property accessors (`dcim`, `ipam`, `tenancy`, `circuits`, `cms`)
- `nautobot_mcp/exceptions.py` — Exception hierarchy (`NautobotMCPError`, `NautobotNotFoundError`, `NautobotValidationError`, `NautobotAPIError`) with `.to_dict()` for structured responses

### Prior Phase Context
- `.planning/phases/15-catalog-engine-core-endpoints/15-CONTEXT.md` — Phase 15 decisions on catalog structure, CMS discovery, workflow stubs

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `get_catalog()` in `catalog/engine.py` — returns full endpoint catalog for validation; bridge validates endpoint against this before dispatch
- `CMS_ENDPOINTS` dict in `cms/client.py` (lines 20-65) — maps 38+ endpoint names to model class names; bridge uses this for CMS endpoint validation
- `resolve_device_id()` in `cms/client.py` — device name → UUID resolution; reused directly for BRG-05
- `cms_list/get/create/update/delete` in `cms/client.py` — generic CRUD functions; candidate for CMS dispatch
- `get_cms_endpoint()` in `cms/client.py` — returns pynautobot endpoint accessor by name; alternative CMS dispatch path
- `NautobotClient._handle_api_error()` in `client.py` — existing error translation from pynautobot → structured exceptions
- `NautobotMCPError.to_dict()` in `exceptions.py` — structured error serialization pattern

### Established Patterns
- `NautobotClient` singleton via `get_client()` in `server.py` — pattern stays unchanged (SVR-04)
- pynautobot accessor pattern: `client.api.{app}.{endpoint}` for core, `client.cms.{endpoint}` for CMS
- All domain modules are standalone — no coupling to MCP layer
- Error handling via `handle_error()` function in `server.py` catches `NautobotMCPError` subclasses

### Integration Points
- New `bridge.py` module will be imported by the rewritten `server.py` (Phase 17)
- `call_nautobot` tool function will live in `bridge.py` and be registered in `server.py`
- Bridge imports `get_catalog()` for endpoint validation and `resolve_device_id()` for CMS device resolution

</code_context>

<specifics>
## Specific Ideas

- Wrapped response should consistently include `endpoint` and `method` fields so agents can correlate responses with requests
- Truncation metadata (`truncated`, `total_available`) only appears when results were actually capped — not on every response
- "Did you mean?" suggestions should search across both core endpoint paths and CMS endpoint keys for maximum coverage

</specifics>

<deferred>
## Deferred Ideas

- **`plugins:*` generic routing** — deferred until concrete need beyond golden_config arises (golden_config only used by workflows in Phase 17)

</deferred>

---

*Phase: 16-rest-bridge-universal-crud*
*Context gathered: 2026-03-24*
