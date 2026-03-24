# Architecture Research

**Domain:** MCP Server API Bridge for Nautobot
**Researched:** 2026-03-24
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│  MCP Server Layer (3 tools)                                  │
│                                                              │
│  ┌────────────────────┐ ┌───────────────┐ ┌──────────────┐  │
│  │ nautobot_api_catalog│ │ call_nautobot │ │ run_workflow  │  │
│  │ Discovery           │ │ Universal CRUD│ │ Composites   │  │
│  └────────┬───────────┘ └───────┬───────┘ └──────┬───────┘  │
│           │                     │                 │           │
├───────────┴─────────────────────┴─────────────────┴──────────┤
│  Bridge Layer (NEW)                                           │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Catalog      │  │ REST Bridge  │  │ Workflow Registry │   │
│  │ Engine       │  │ (bridge.py)  │  │ (workflows.py)   │   │
│  │              │  │              │  │                   │   │
│  │ Static JSON  │  │ Endpoint     │  │ bgp_summary      │   │
│  │ + Dynamic    │  │ routing +    │  │ routing_table     │   │
│  │ CMS discovery│  │ validation + │  │ firewall_summary  │   │
│  │              │  │ pagination   │  │ onboard_config    │   │
│  │              │  │              │  │ compare_device    │   │
│  │              │  │              │  │ ...               │   │
│  └──────┬───────┘  └──────┬───────┘  └────────┬──────────┘  │
│         │                 │                    │              │
├─────────┴─────────────────┴────────────────────┴─────────────┤
│  Domain Layer (UNCHANGED)                                     │
│                                                              │
│  devices │ interfaces │ ipam │ org │ circuits │ golden_config │
│  cms/routing │ cms/interfaces │ cms/firewalls │ cms/policies  │
│  cms/arp │ drift │ onboarding │ verification                 │
├──────────────────────────────────────────────────────────────┤
│  Client Layer (UNCHANGED)                                     │
│                                                              │
│  client.py (pynautobot) │ cms/client.py (CMS_ENDPOINTS)      │
└──────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `server.py` | Register 3 MCP tools, handle transport | FastMCP decorators, ~200 LOC |
| `catalog/` | Build and serve endpoint catalog | Static JSON (core) + dynamic (CMS_ENDPOINTS) |
| `bridge.py` | Route + validate + execute API calls | Endpoint routing: `/api/*` → pynautobot, `cms:*` → CMS helpers |
| `workflows.py` | Registry of composite workflow functions | Dict mapping name → function + params + description |
| Domain modules | Business logic (UNCHANGED) | Existing `devices.py`, `cms/routing.py`, etc. |
| `client.py` | Nautobot API client (UNCHANGED) | pynautobot singleton pattern |
| `cms/client.py` | CMS plugin client (UNCHANGED) | CMS_ENDPOINTS registry + generic CRUD |

## Recommended Project Structure

```
nautobot_mcp/
├── server.py              # 3 MCP tools (~200 LOC) [REWRITTEN]
├── catalog/               # API catalog engine [NEW]
│   ├── __init__.py
│   ├── engine.py          # build_catalog(), filter by domain
│   └── core_endpoints.json # Static core endpoint definitions
├── bridge.py              # REST execution bridge [NEW]
├── workflows.py           # Workflow registry + dispatch [NEW]
├── client.py              # pynautobot wrapper [UNCHANGED]
├── devices.py             # Device domain functions [UNCHANGED]
├── interfaces.py          # Interface domain functions [UNCHANGED]
├── ipam.py                # IPAM domain functions [UNCHANGED]
├── organizations.py       # Organization domain functions [UNCHANGED]
├── circuits.py            # Circuit domain functions [UNCHANGED]
├── golden_config.py       # Golden Config functions [UNCHANGED]
├── cms/                   # CMS domain [UNCHANGED]
│   ├── client.py          # CMS_ENDPOINTS + generic CRUD
│   ├── routing.py         # Routing composites (bgp_summary, etc.)
│   ├── interfaces.py      # Interface composites
│   ├── firewalls.py       # Firewall composites
│   ├── policies.py        # Policy functions
│   └── arp.py             # ARP functions
├── drift/                 # Drift comparison [UNCHANGED]
├── models/                # Pydantic models [UNCHANGED]
└── onboarding/            # Config onboarding [UNCHANGED]
```

### Structure Rationale

- **`catalog/`:** Isolated from runtime code; can be updated independently
- **`bridge.py`:** Single file for all endpoint routing logic; keeps dispatch centralized
- **`workflows.py`:** Flat registry — no class hierarchy, just a dict of name → function
- **Domain modules unchanged:** Zero-risk refactoring; all tests pass without modification

## Architectural Patterns

### Pattern 1: Catalog-Discovery Pattern

**What:** Agent calls discovery tool to learn available operations before executing them.
**When to use:** When the agent has no prior knowledge of available endpoints.
**Trade-offs:** Extra round-trip vs. agent confidence; catalog is cheap (~400 tokens).

**Example:**
```python
# Agent workflow:
# 1. Discover: nautobot_api_catalog(domain="dcim")
# 2. Execute: call_nautobot(endpoint="/api/dcim/devices/", method="GET", params={"name": "router1"})
```

### Pattern 2: Endpoint Routing Bridge

**What:** Single dispatcher that routes to different backends based on endpoint prefix.
**When to use:** When multiple APIs (core, CMS, plugins) share one MCP interface.
**Trade-offs:** Slightly more complex routing logic vs. massive tool count reduction.

**Example:**
```python
def route_endpoint(endpoint: str):
    if endpoint.startswith("/api/"):
        return use_pynautobot(endpoint)
    elif endpoint.startswith("cms:"):
        return use_cms_client(endpoint)
    elif endpoint.startswith("plugins:"):
        return use_plugin_accessor(endpoint)
```

### Pattern 3: Workflow Registry Pattern

**What:** Named workflows registered in a dict, dispatched by string name.
**When to use:** For N+1 query patterns and complex business logic that shouldn't be agent-side.
**Trade-offs:** Fixed set of workflows vs. flexible agent; new workflow = one dict entry + one function.

**Example:**
```python
WORKFLOW_REGISTRY = {
    "bgp_summary": {
        "function": cms_routing.get_device_bgp_summary,
        "params": {"device": "str (required)", "detail": "bool"},
        "description": "BGP groups, neighbors, address families for a device"
    }
}
```

## Data Flow

### Request Flow

```
Agent Request (e.g. "list devices")
    ↓
nautobot_api_catalog(domain="dcim")  ← Agent discovers available endpoints
    ↓
call_nautobot(endpoint="/api/dcim/devices/", method="GET", params={...})
    ↓
bridge.py: validate endpoint + route
    ↓
pynautobot: nautobot.dcim.devices.filter(**params)  ← Existing client
    ↓
Nautobot REST API: /api/dcim/devices/?name=...
    ↓
Response → serialize → return to agent
```

### Workflow Flow

```
Agent Request (e.g. "show BGP summary for router1")
    ↓
run_workflow(workflow="bgp_summary", params={"device": "router1"})
    ↓
workflows.py: lookup "bgp_summary" in WORKFLOW_REGISTRY
    ↓
cms/routing.py: get_device_bgp_summary(device="router1")
    ↓
  ├── CMS API: get BGP groups for device
  ├── CMS API: get neighbors per group (N calls)
  └── CMS API: get address families per neighbor (M calls)
    ↓
Aggregated response → return to agent (1 tool call instead of N+1)
```

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-10 agents | Current 3-tool design handles this trivially |
| 10-50 agents | Add connection pooling to pynautobot if needed |
| 50+ agents | Consider Streamable HTTP transport (FastMCP 3.0 supports this) |

### Scaling Priorities

1. **First bottleneck:** Nautobot API rate limiting — solved by pagination limits and caching at agent level
2. **Second bottleneck:** MCP server throughput — solved by async FastMCP + Streamable HTTP

## Anti-Patterns

### Anti-Pattern 1: Recreating Tool Proliferation

**What people do:** Generate one MCP tool per endpoint from catalog
**Why it's wrong:** Recreates the 165-tool problem with extra steps
**Do this instead:** Single `call_nautobot` tool with endpoint as parameter

### Anti-Pattern 2: Fat Catalog

**What people do:** Include full schema (all fields, types, constraints) in catalog response
**Why it's wrong:** Bloats catalog response, agent doesn't need schema to make a request
**Do this instead:** Include only endpoint, methods, common filters, and description

### Anti-Pattern 3: Workflow Bypass

**What people do:** Let agents call N individual API calls instead of using `run_workflow`
**Why it's wrong:** N+1 round-trips are slow and error-prone
**Do this instead:** Skills guide agents to use `run_workflow` for composite operations

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Nautobot REST API | pynautobot (`client.py`) | Core, IPAM, circuits, tenancy, golden config |
| CMS Plugin API | `cms/client.py` | 49 DRF endpoints under `/api/plugins/netnam-cms-core/` |
| jmcp (Juniper MCP) | Agent-side skills only | NOT integrated server-side; skills orchestrate cross-MCP |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| server.py ↔ catalog/ | Function call | `build_catalog(domain)` returns dict |
| server.py ↔ bridge.py | Function call | `execute_api_call(endpoint, method, ...)` returns dict |
| server.py ↔ workflows.py | Function call | `execute_workflow(name, params)` returns dict |
| bridge.py ↔ domain modules | Function call via pynautobot | Existing patterns unchanged |

## Sources

- API Bridge Design v2 (internal) — architecture diagram, tool classification
- FastMCP 3.0 documentation — component versioning, Streamable HTTP
- pynautobot documentation — dynamic endpoint generation, App hierarchy
- MCP specification — tool primitives, JSON-RPC 2.0 protocol

---
*Architecture research for: MCP Server API Bridge for Nautobot*
*Researched: 2026-03-24*
