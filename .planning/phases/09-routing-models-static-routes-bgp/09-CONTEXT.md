# Phase 9: Routing Models — Static Routes & BGP - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Add full CRUD MCP tools, Pydantic models, and CLI commands for Juniper routing models in netnam-cms-core: static routes (with next-hops), BGP (groups, neighbors, address families, policy associations, received routes), and routing instances as display/filter fields. Requirements RTG-01 through RTG-10.

</domain>

<decisions>
## Implementation Decisions

### MCP Tool Granularity — Inline & Device-Scoped

- **Static routes inline next-hops** — `list_static_routes` returns each route with its simple + qualified next-hops embedded. One call gives the full picture.
- **BGP tools are device-scoped** — `list_bgp_groups(device=X)` returns all groups for a device; `list_bgp_neighbors(device=X)` returns all neighbors across all groups for that device. Agent pattern: "show me all BGP config for device X."
- **Child models are list/get only** — Nexthops, address families, policy associations do NOT get create/update/delete tools. They're read through their parents or via standalone list/get.
- **Received routes are read-only** — `JuniperBGPReceivedRoute` is operational data (Adj-RIB-In). Only list/get tools, no mutation.

### CLI Command Structure

- **Nested domain namespace** — `nautobot-mcp cms routing <command>` (e.g., `nautobot-mcp cms routing list-static-routes --device R1`)
- **Tabular output + `--detail` flag** — Default shows concise table with most important columns. `--detail` flag shows inlined child data (next-hops, address families).
- **CLI ships with this phase** — Not deferred to Phase 14. Each domain phase (9, 10, 11, 12, 13) includes its own CLI commands. Phase 14 focuses on the agent skill guide.

### Routing Instance Handling

- **No dedicated routing instance tools** — `JuniperRoutingInstance` has NO DRF API endpoint registered in `urls.py`. Cannot be queried directly via the CMS plugin API.
- **Display field + optional filter** — Routing instance name appears as a column in static route and BGP group output. It's also an optional filter parameter: `list_static_routes(device="R1", routing_instance="VRF-CUST-A")`.
- **Extract from nested FK** — When querying static routes/BGP groups, extract `routing_instance.display` from the nested FK reference for the Pydantic model.

### CRUD Scope per Model

| Model | List | Get | Create | Update | Delete |
|-------|------|-----|--------|--------|--------|
| JuniperStaticRoute | ✅ | ✅ | ✅ | ✅ | ✅ |
| JuniperStaticRouteNexthop | ✅ (inline) | ✅ | ❌ | ❌ | ❌ |
| JuniperStaticRouteQualifiedNexthop | ✅ (inline) | ✅ | ❌ | ❌ | ❌ |
| JuniperBGPGroup | ✅ | ✅ | ✅ | ✅ | ✅ |
| JuniperBGPNeighbor | ✅ | ✅ | ✅ | ✅ | ✅ |
| JuniperBGPAddressFamily | ✅ | ✅ | ❌ | ❌ | ❌ |
| JuniperBGPPolicyAssociation | ✅ | ✅ | ❌ | ❌ | ❌ |
| JuniperBGPReceivedRoute | ✅ | ✅ | ❌ | ❌ | ❌ |
| JuniperRoutingInstance | ❌ (no API) | ❌ | ❌ | ❌ | ❌ |

### Claude's Discretion
- Exact Pydantic field selection per model (which fields to include vs omit)
- Table column selection for CLI output per model
- Internal helper functions for inlining next-hops into static route responses
- Error messages and hints for routing-specific operations

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Established patterns (from Phase 8)
- `nautobot_mcp/cms/client.py` — Generic CRUD helpers (`cms_list`, `cms_get`, `cms_create`, `cms_update`, `cms_delete`), device UUID resolution, endpoint registry
- `nautobot_mcp/models/cms/base.py` — `CMSBaseSummary` base model with `from_nautobot()`, `_extract_device()`, `_get_field()`
- `nautobot_mcp/client.py` — `NautobotClient.cms` property for plugin access

### CMS API model definitions
- `D:\latuan\Programming\nautobot-project\netnam-cms-core\netnam_cms_core\models\routing.py` — All routing models (StaticRoute, Nexthops, BGPGroup, BGPNeighbor, AddressFamily, PolicyAssociation, ReceivedRoute)
- `D:\latuan\Programming\nautobot-project\netnam-cms-core\netnam_cms_core\models\routing_instance.py` — RoutingInstance model (no API endpoint)
- `D:\latuan\Programming\nautobot-project\netnam-cms-core\netnam_cms_core\api\urls.py` — DRF endpoint registrations (confirms no routing instance endpoint)

### Existing CLI patterns
- `nautobot_mcp/cli/` — Existing CLI commands using Typer + rich tables

</canonical_refs>

<code_context>
## Existing Code Insights

### CMS Endpoint Names (pynautobot underscore format)
- `juniper_static_routes` → Static routes
- `juniper_static_route_nexthops` → Simple next-hops
- `juniper_static_route_qualified_nexthops` → Qualified next-hops
- `juniper_bgp_groups` → BGP groups
- `juniper_bgp_neighbors` → BGP neighbors
- `juniper_bgp_address_families` → Address families
- `juniper_bgp_policy_associations` → Policy associations
- `juniper_bgp_received_routes` → Received routes

### Key Model Relationships
- StaticRoute.routing_instance → FK to RoutingInstance (nullable, null = global)
- StaticRoute.destination → FK to Prefix
- StaticRouteNexthop.route → FK to StaticRoute (related_name: `simple_next_hops`)
- StaticRouteQualifiedNexthop.route → FK to StaticRoute (related_name: `qualified_next_hops`)
- BGPGroup.routing_instance → FK to RoutingInstance (nullable)
- BGPNeighbor.group → FK to BGPGroup
- BGPNeighbor.peer_ip → FK to IPAddress
- BGPAddressFamily has XOR parent: group OR neighbor (not both)
- BGPPolicyAssociation has XOR parent: bgp_group OR bgp_neighbor
- BGPReceivedRoute.neighbor → FK to BGPNeighbor

### Inlining Strategy
For static routes, after fetching routes via `cms_list`, need to fetch nexthops separately and merge. Two approaches:
1. N+1: For each route, query its nexthops (slow for many routes)
2. Batch: Fetch all nexthops for the device, group by `route` FK, attach to route objects
Recommend batch approach for list operations.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches following established Phase 8 patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 09-routing-models-static-routes-bgp*
*Context gathered: 2026-03-20*
