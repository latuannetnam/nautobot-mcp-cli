# Architecture Research

**Domain:** MCP Tool Consolidation / Generic Resource Engine
**Researched:** 2026-03-24
**Confidence:** HIGH

## Standard Architecture: Toolhost Pattern

The "Toolhost Pattern" (documented in MCP best practices 2025-2026) is the industry-recognized approach for consolidating many closely related MCP tools into a single dispatcher. Our implementation follows this pattern precisely.

### System Overview

```
┌─────────────────────────────────────────────────────────┐
│              MCP Tool Layer (~18 tools)                   │
│  ┌──────────────────┐ ┌──────────────────┐              │
│  │  Discovery (2)    │ │  Composites (~15) │              │
│  │  list_resources   │ │  device_summary   │              │
│  │  resource_schema  │ │  bgp_summary      │              │
│  └────────┬─────────┘ │  firewall_summary │              │
│           │            │  compare_device   │              │
│  ┌────────┴─────────┐ │  ...              │              │
│  │  Generic CRUD (1) │ └────────┬─────────┘              │
│  │  resource()       │          │                        │
│  └────────┬─────────┘          │                        │
├───────────┴────────────────────┴────────────────────────┤
│              Resource Registry (registry.py)              │
│  RESOURCE_REGISTRY: Dict[str, ResourceDef]               │
│  ~50 entries mapping resource_type → handler config       │
├─────────────────────────────────────────────────────────┤
│              Domain Modules (UNCHANGED)                   │
│  devices.py │ interfaces.py │ ipam.py │ organization.py  │
│  cms/routing.py │ cms/interfaces.py │ cms/firewalls.py   │
│  cms/policies.py │ cms/arp.py │ golden_config.py         │
└─────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `nautobot_list_resources` | Catalog discovery | Iterate `RESOURCE_REGISTRY`, return types + actions |
| `nautobot_resource_schema` | Field schema for a resource | Introspect Pydantic model fields |
| `nautobot_resource` | Universal CRUD dispatcher | Route to domain functions via registry |
| `RESOURCE_REGISTRY` | Resource → handler mapping | Python dict with `ResourceDef` entries |
| Domain modules | Actual business logic | **Unchanged** — existing functions |
| Composite tools | Multi-entity joins | **Unchanged** — existing functions |

## Recommended Project Structure

```
nautobot_mcp/
├── registry.py           # [NEW] Resource registry + ResourceDef
├── server.py             # [MODIFIED] ~300 lines: 3 generic + ~15 composite tools
├── client.py             # [UNCHANGED]
├── config.py             # [UNCHANGED]
├── devices.py            # [UNCHANGED]
├── interfaces.py         # [UNCHANGED]
├── ipam.py               # [UNCHANGED]
├── organization.py       # [UNCHANGED]
├── circuits.py           # [UNCHANGED]
├── golden_config.py      # [UNCHANGED]
├── onboarding.py         # [UNCHANGED]
├── verification.py       # [UNCHANGED]
├── drift.py              # [UNCHANGED]
├── cms/
│   ├── client.py         # [UNCHANGED] — CMS_ENDPOINTS stays here
│   ├── routing.py        # [UNCHANGED]
│   ├── interfaces.py     # [UNCHANGED]
│   ├── firewalls.py      # [UNCHANGED]
│   ├── policies.py       # [UNCHANGED]
│   └── arp.py            # [UNCHANGED]
├── models/               # [UNCHANGED]
└── cli/                  # [UNCHANGED]
```

### Structure Rationale

- **`registry.py` is the only new file** — contains `ResourceDef` dataclass + `RESOURCE_REGISTRY` dict
- **`server.py` is the only modified file** — reduced from 3,883 to ~300 lines
- **All domain modules unchanged** — the dispatcher calls them, they don't know about it

## Architectural Patterns

### Pattern 1: Toolhost Dispatcher

**What:** Single MCP tool that routes to different handlers based on `resource_type` + `action` parameters
**When to use:** >20 closely related CRUD tools in an MCP server
**Trade-offs:** Slightly less transparent to the agent (needs discovery step), but dramatically reduces context consumption

```python
@mcp.tool(name="nautobot_resource")
def nautobot_resource(resource_type: str, action: str, ...) -> dict:
    resource_def = RESOURCE_REGISTRY.get(resource_type)
    handler = resource_def.handlers[action]
    return handler(client, **params)
```

### Pattern 2: Two-Phase Discovery

**What:** Agent first discovers available resources, then queries schema for a specific resource type before performing operations
**When to use:** When the generic tool has many possible parameter combinations
**Trade-offs:** Adds 1-2 tool calls before first CRUD operation, but eliminates hallucinated parameters

### Pattern 3: Dual-Registry (Core + CMS)

**What:** Core Nautobot resources mapped manually (devices, interfaces, IPs); CMS resources auto-mapped from `CMS_ENDPOINTS`
**When to use:** When one domain has an existing programmatic registry
**Trade-offs:** Slightly different handling paths, but maximizes code reuse

## Data Flow

### Generic CRUD Request Flow

```
Agent: nautobot_resource(resource_type="cms.static_route", action="list", filters={"device": "core-rtr-01"})
    ↓
server.py → RESOURCE_REGISTRY["cms.static_route"]
    ↓
ResourceDef(domain="cms", handler=cms_routing.list_static_routes, model=StaticRouteSummary)
    ↓
cms_routing.list_static_routes(client, device_name="core-rtr-01")
    ↓
cms_client.cms_list("juniper_static_routes", client, StaticRouteSummary, filters)
    ↓
Nautobot REST API → pynautobot → Pydantic model → dict response
```

## Anti-Patterns

### Anti-Pattern 1: Dynamic Tool Generation

**What people do:** Generate `@mcp.tool` decorators dynamically from registry at import time
**Why it's wrong:** IDE can't inspect, harder to debug, test coverage unclear, FastMCP may not handle dynamic names well
**Do this instead:** Static 3 tool definitions with internal dispatch

### Anti-Pattern 2: Over-Parameterized Generic Tool

**What people do:** Put ALL possible fields as optional parameters on the generic tool
**Why it's wrong:** Tool description becomes enormous, defeating the purpose
**Do this instead:** Accept `filters: dict` and `data: dict` — let `nautobot_resource_schema` guide the agent

### Anti-Pattern 3: Round-Trip for Every Child Entity

**What people do:** Require separate `nautobot_resource` calls for children (nexthops, address families)
**Why it's wrong:** Multiplies agent round-trips
**Do this instead:** Keep composite tools for multi-entity operations

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Nautobot REST API | pynautobot client (unchanged) | All CRUD via existing domain functions |
| Nautobot CMS Plugin | CMS client via CMS_ENDPOINTS (unchanged) | Auto-mapped to registry |
| jmcp (Juniper MCP) | Via agent workflow only | Not affected by this refactor |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Registry → Domain modules | Direct Python function calls | No new interfaces needed |
| Registry → CMS client | Via `cms_list/get/create/update/delete` | Already generic |
| Server → Registry | Import + dict lookup | O(1) lookup performance |

---
*Architecture research for: MCP Tool Consolidation*
*Researched: 2026-03-24*
