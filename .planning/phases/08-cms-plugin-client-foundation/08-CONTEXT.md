# Phase 8: CMS Plugin Client Foundation - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the core client layer for communicating with netnam-cms-core plugin API endpoints. This phase establishes the API access pattern, module structure, and Pydantic model conventions that all subsequent CMS phases (9-14) will use. No domain-specific CRUD tools in this phase — those are Phases 9-14.

</domain>

<decisions>
## Implementation Decisions

### API Access Approach
- Use pynautobot plugin accessor: `client.api.plugins.netnam_cms_core`
- Same pattern as `client.golden_config` — no custom HTTP/requests needed
- Verified against real dev server: `.all()`, `.filter()`, `.get()`, `.create()`, `.delete()` all work
- Endpoint names use underscores in pynautobot (e.g., `juniper_static_routes` → API URL `juniper-static-routes`)
- Add `cms` property to `NautobotClient` class (like `golden_config` property)

### Module Organization
- New `nautobot_mcp/cms/` subpackage for all CMS domain modules
- Submodules per domain: `routing.py`, `interfaces.py`, `firewalls.py`, `policies.py`, `arp.py`
- New `nautobot_mcp/models/cms/` subpackage for CMS Pydantic models
- Submodules per domain mirror the CRUD modules

### Pydantic Model Strategy
- 1:1 API mirror — one Pydantic model class per CMS API resource
- Individual CRUD functions per object type (not aggregated)
- Use `from_nautobot(record)` classmethod pattern (same as existing models)
- Composite/aggregated models deferred to Phase 12

### Claude's Discretion
- Exact field selection per Pydantic model (which fields to include vs omit)
- Helper utilities (e.g., device UUID resolution helper used across all CMS modules)
- Error messages and hints specific to CMS operations
- Whether to create a base CMS model class or reuse existing `BaseModel` patterns

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing patterns to follow
- `nautobot_mcp/client.py` — NautobotClient class, plugin access pattern (`golden_config` property)
- `nautobot_mcp/golden_config.py` — Plugin CRUD pattern (how existing plugin operations are structured)
- `nautobot_mcp/devices.py` — Standard CRUD function pattern (list/get/create/update/delete)
- `nautobot_mcp/models/base.py` — `ListResponse[T]` generic wrapper, base model patterns

### CMS API reference
- `D:\latuan\Programming\nautobot-project\netnam-cms-core\netnam_cms_core\api\urls.py` — All 49 DRF endpoint registrations
- `D:\latuan\Programming\nautobot-project\netnam-cms-core\netnam_cms_core\models\routing.py` — Routing model definitions (fields, relationships)
- `D:\latuan\Programming\nautobot-project\netnam-cms-core\netnam_cms_core\models\interfaces.py` — Interface model definitions
- `D:\latuan\Programming\nautobot-project\netnam-cms-core\netnam_cms_core\models\firewalls.py` — Firewall model definitions
- `D:\latuan\Programming\nautobot-project\netnam-cms-core\netnam_cms_core\models\policies.py` — Policy model definitions
- `D:\latuan\Programming\nautobot-project\netnam-cms-core\netnam_cms_core\models\arp.py` — ARP model definitions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `NautobotClient._handle_api_error()` — Structured error translation for all API operations
- `ListResponse[T]` — Generic list response wrapper with count + results
- `from_nautobot()` classmethod — Standard pattern for converting pynautobot records to Pydantic
- `NautobotClient.validate_connection()` — Connection validation pattern

### Established Patterns
- CRUD functions take `client: NautobotClient` as first arg + domain-specific filters
- All operations wrapped in try/except with `_handle_api_error()`
- `list_*` returns `ListResponse[ModelSummary]` with optional `limit` param
- `get_*` returns single model, raises `NautobotNotFoundError` if not found
- `create_*` takes required fields as args + `**kwargs` for extras
- `update_*` takes `id` + `**updates`, uses `setattr` + `record.save()`
- `delete_*` takes `id`, returns `bool` or `dict` with success status

### Integration Points
- `NautobotClient` class — add `cms` property accessor
- `nautobot_mcp/models/` — add `cms/` subpackage
- `nautobot_mcp/` — add `cms/` subpackage
- pynautobot endpoint naming: `juniper_static_routes` (underscores) → API URL `juniper-static-routes` (hyphens)

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches following established codebase patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 08-cms-plugin-client-foundation*
*Context gathered: 2026-03-20*
