# Phase 15: Catalog Engine & Core Endpoints - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the API catalog engine that lets agents discover available Nautobot endpoints and workflows via `nautobot_api_catalog()`. This includes:
- Static core endpoint definitions (dcim, ipam, circuits, tenancy)
- Dynamic CMS endpoint discovery from `CMS_ENDPOINTS` registry
- Workflow entry listing (stub registry until Phase 17 implements actual functions)
- Dev script for catalog maintenance
- Unit tests for catalog completeness and domain filtering

</domain>

<decisions>
## Implementation Decisions

### Static Catalog Structure
- **Curated subset** of Nautobot endpoints — only those useful for network automation agents (skip admin-only endpoints like `object_changes`, `custom_fields`)
- **Mirror Nautobot's app structure** for domain grouping: `dcim`, `ipam`, `circuits`, `tenancy` (matches API URL structure)
- **Dev script** (`scripts/generate_catalog.py`) to introspect Nautobot's API and generate/update the catalog data file. Not an MCP tool — a developer utility for catalog maintenance when Nautobot is upgraded.
- **Token budget: soft guideline** — aim for ~1500 tokens but up to ~2000 is acceptable, especially with CMS's 38+ entries

### CMS Discovery Mechanism
- **Friendly display name + raw key** — catalog shows human-readable names (e.g., `"Static Routes"`) while preserving the raw endpoint key (e.g., `cms:juniper_static_routes`) for `call_nautobot` dispatch
- Auto-discovered from `CMS_ENDPOINTS` registry at runtime — zero duplication with `cms/client.py`

### Workflow Entries in Catalog
- **Design doc format** for workflow params: `param_name: "type (required|optional)"` + one-line description
- **Include `aggregates` field** showing which endpoints a workflow uses under the hood — helps agents understand what a workflow does
- Example: `"bgp_summary": { "params": {...}, "description": "...", "aggregates": ["cms:juniper_bgp_groups", ...] }`

### Claude's Discretion
- Storage format for static catalog (embedded Python dict vs external JSON file)
- CMS metadata level (minimal vs enriched with filters/descriptions)
- CMS filter source (hardcoded per domain vs inferred vs none)
- CMS collapsing in unfiltered response (summarized domain counts vs full listing)
- Whether to include a `hint` field in catalog response guiding agent to next tool
- How to handle workflow registry before Phase 17 (static list vs placeholder import vs stub registry)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture
- `docs/plans/2026-03-24-api-bridge-mcp-design.md` — Full API Bridge architecture design v2 (approved). Defines 3-tool interface, catalog format, routing logic, workflow classification.

### Requirements
- `.planning/REQUIREMENTS.md` §Catalog Engine (CAT) — CAT-01 through CAT-06 + TST-02

### Existing Code
- `nautobot_mcp/cms/client.py` — `CMS_ENDPOINTS` registry (38+ entries), `resolve_device_id()`, generic CRUD helpers (`cms_list/get/create/update/delete`)
- `nautobot_mcp/server.py` — Current 165-tool server (to be replaced in Phase 17)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CMS_ENDPOINTS` dict in `cms/client.py` (lines 20-65) — maps 38+ endpoint names to model class names, grouped by domain (routing, interfaces, firewalls, policies, ARP). Catalog should read this directly.
- `resolve_device_id()` in `cms/client.py` — device name → UUID resolution, will be reused by the REST bridge (Phase 16)
- `cms_list/get/create/update/delete` helpers — generic CRUD functions that the bridge will dispatch to

### Established Patterns
- Domain modules (`devices.py`, `interfaces.py`, `ipam.py`, `cms/routing.py`, etc.) are standalone — no coupling to MCP layer
- `NautobotClient` singleton via `get_client()` in `server.py` — pattern stays unchanged
- pynautobot accessor pattern: `client.api.{app}.{endpoint}` for core, `client.cms.{endpoint}` for CMS

### Integration Points
- New `catalog/` module will be imported by the rewritten `server.py` (Phase 17)
- `nautobot_api_catalog` tool function will live in the catalog module and be registered in `server.py`
- CMS discovery reads `CMS_ENDPOINTS` from `cms/client.py` at import time

</code_context>

<specifics>
## Specific Ideas

- Dev script should hit Nautobot's API root or `/api/docs/` to discover endpoints, then generate a catalog data file for review
- Workflow `aggregates` field should list the CMS/core endpoints that a workflow touches internally — this helps agents understand scope without reading workflow source code

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 15-catalog-engine-core-endpoints*
*Context gathered: 2026-03-24*
