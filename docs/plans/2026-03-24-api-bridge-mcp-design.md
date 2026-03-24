# API Bridge MCP Architecture Design v2

**Date:** 2026-03-24
**Status:** Approved
**Goal:** Re-architect Nautobot MCP Server from 165+ tools to **3 tools + agent skills**.

## Problem Statement

The current MCP server exposes 165+ tools (116KB `server.py`). This causes:
- **~50K token overhead** — every tool description loaded into agent context
- **Agent confusion** — too many similar tools
- **High maintenance** — new Nautobot entity = 3-5 new MCP tools

**Target environment:** Claude Desktop (sandboxed, no CLI, no internet — MCP is the only path).
For Antigravity/Claude Code, the existing CLI + agent skills is preferred.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  MCP Server (3 tools)                                       │
│                                                             │
│  ┌───────────────────┐ ┌────────────────┐ ┌──────────────┐ │
│  │ nautobot_api_catalog│ │ call_nautobot  │ │ run_workflow │ │
│  │ Discovery          │ │ Universal CRUD │ │ Server-side  │ │
│  └───────────────────┘ └────────────────┘ └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Catalog Engine       │ REST Bridge       │ Workflow Reg.  │
│  ┌─────────────────┐  │ ┌──────────────┐ │ ┌────────────┐ │
│  │ Static Core     │  │ │ Endpoint     │ │ │ bgp_summary│ │
│  │ (dcim,ipam,..)  │  │ │ validation + │ │ │ fw_summary │ │
│  ├─────────────────┤  │ │ pagination + │ │ │ onboard    │ │
│  │ Dynamic Plugin  │  │ │ error hints  │ │ │ drift      │ │
│  │ (CMS discovery) │  │ └──────────────┘ │ │ compliance │ │
│  └─────────────────┘  │                  │ └────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Domain Modules (UNCHANGED)                                 │
│  devices │ interfaces │ ipam │ cms/ │ drift │ onboarding   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Agent Skills (distributed as files, NOT served via MCP)    │
│                                                             │
│  skills/device-audit/SKILL.md     ← cross-MCP (nautobot+jmcp)│
│  skills/onboard-config/SKILL.md   ← guides dry-run→commit  │
│  skills/verify-compliance/SKILL.md                          │
│                                                             │
│  Loaded natively by each agent platform:                    │
│  • Antigravity → .agent/skills/                             │
│  • Claude Desktop → native skill mechanism                  │
│  • OpenClaw → their skill format                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Tool 1: `nautobot_api_catalog`

**Purpose:** Agent calls this first to discover what Nautobot can do.

```python
@mcp.tool(name="nautobot_api_catalog")
def nautobot_api_catalog(domain: str | None = None) -> dict:
    """Discover available Nautobot API endpoints and workflows.

    Args:
        domain: Optional filter — "dcim", "ipam", "circuits", "cms", "workflows"
    """
```

**Returns:**
```json
{
  "dcim": {
    "devices": {
      "endpoint": "/api/dcim/devices/",
      "methods": ["GET", "POST", "PATCH", "DELETE"],
      "filters": ["name", "location", "role", "status", "tenant", "platform"],
      "description": "Network devices (routers, switches, firewalls)"
    }
  },
  "cms": {
    "static_routes": {
      "endpoint": "cms:juniper_static_routes",
      "methods": ["GET", "POST", "PATCH", "DELETE"],
      "filters": ["device", "prefix", "routing_instance"],
      "description": "Juniper static routes"
    }
  },
  "workflows": {
    "bgp_summary": {
      "params": {"device": "str (required)", "detail": "bool (optional)"},
      "description": "BGP groups, neighbors, address families for a device"
    },
    "onboard_config": {
      "params": {"config_json": "str (required)", "device_name": "str (required)", "dry_run": "bool"},
      "description": "Parse and onboard JunOS config into Nautobot"
    }
  }
}
```

**Catalog sources (hybrid):**
- **Static**: Core endpoints (dcim, ipam, circuits, tenancy) from embedded JSON
- **Dynamic**: CMS plugin endpoints from `CMS_ENDPOINTS` registry at runtime
- **Registry**: Workflows listed from `WORKFLOW_REGISTRY`

---

## Tool 2: `call_nautobot`

**Purpose:** Execute any Nautobot CRUD operation.

```python
@mcp.tool(name="call_nautobot")
def call_nautobot(
    endpoint: str,         # "/api/dcim/devices/" or "cms:juniper_static_routes"
    method: str = "GET",   # GET, POST, PATCH, DELETE
    params: dict | None = None,    # Query filters (GET)
    data: dict | None = None,      # Request body (POST/PATCH)
    id: str | None = None,         # Object UUID (single-object ops)
    limit: int = 50,       # Pagination limit
) -> dict:
    """Execute a Nautobot API call. Use nautobot_api_catalog first to discover endpoints."""
```

**Routing logic:**
```
"/api/*"     → pynautobot core accessor (dcim, ipam, circuits, tenancy)
"cms:*"      → CMS plugin via cms_list/get/create/update/delete
"plugins:*"  → Other plugins via pynautobot plugins accessor
```

**Key behaviors:**
- Validates endpoint exists (checked against catalog)
- Auto-pagination for GET (follows `next` links up to `limit`)
- Device name → UUID auto-resolution for CMS endpoints
- Error translation: HTTP 404/400/401 → structured hints

---

## Tool 3: `run_workflow`

**Purpose:** Execute server-side multi-step operations that would cost too many agent round trips.

```python
@mcp.tool(name="run_workflow")
def run_workflow(workflow: str, params: dict) -> dict:
    """Execute a multi-step Nautobot workflow server-side.
    Use nautobot_api_catalog to see available workflows."""
```

### Workflow Classification

Server-side workflows exist for two reasons:
1. **N+1 query patterns** — aggregating hierarchical data (Category 2)
2. **Complex business logic** — algorithms that can't be skill steps (Category 3)

| Workflow | Category | Internal API Calls | Why Server-Side |
|----------|----------|-------------------|-----------------|
| `bgp_summary` | 2 (N+1) | 5-20+ calls | Groups → neighbors → AFs → policies |
| `routing_table` | 2 (N+1) | 3N+1 calls | Routes → nexthops per route |
| `firewall_summary` | 2 (N+1) | 2+N×M calls | Filters → terms → actions |
| `interface_detail` | 2 (N+1) | N+1 calls | Units → families → VRRP |
| `onboard_config` | 3 (logic) | 499 LOC | Config parsing, type mapping, idempotent match |
| `compare_device` | 3 (logic) | 256 LOC | Input normalization, drift comparison |
| `verify_data_model` | 3 (logic) | ~150 LOC | Structured comparison + report |
| `verify_compliance` | 3 (logic) | ~80 LOC | Golden Config + compliance check |
| `compare_bgp` | 3 (logic) | CMS drift | Live vs CMS neighbor comparison |
| `compare_routes` | 3 (logic) | CMS drift | Live vs CMS route comparison |

### What Stays Agent-Side (Skills)

Simple aggregations that need only 2-3 calls → guided by agent skills, NOT server workflows:

| Operation | API Calls | Mechanism |
|-----------|-----------|-----------|
| `device_summary` | 3 (device + interfaces + IPs) | Skill step |
| `get_device_ips` | 2 (interfaces + IP M2M) | Skill step |
| Full device audit | 5+ (nautobot + jmcp) | Cross-MCP skill |

---

## Agent Skills (Distributed as Files)

Skills are NOT served through MCP. They ship alongside the package and are loaded by each agent's native skill mechanism.

```
nautobot-mcp-cli/
├── nautobot_mcp/          ← MCP server
│   ├── server.py          ← 3 tools (~200 LOC)
│   ├── catalog/           ← API catalog engine
│   ├── bridge.py          ← REST execution engine
│   └── workflows.py       ← Workflow registry + functions
├── skills/                ← Agent skills (distributed with package)
│   ├── device-audit/SKILL.md
│   ├── onboard-config/SKILL.md
│   ├── verify-compliance/SKILL.md
│   └── device-summary/SKILL.md
└── cli/                   ← CLI commands (unchanged)
```

Skills reference the new 3-tool API:
```markdown
# Before (old skill references old tool names)
Step 2: Use nautobot_cms_compare_bgp_neighbors(device_name="X", live_neighbors=[...])

# After (new skill references new tools)
Step 2: Use run_workflow(workflow="compare_bgp", params={"device": "X", "live_neighbors": [...]})
```

### Separation of Concerns

| Concern | Handled By | NOT Handled By |
|---------|------------|----------------|
| API execution (CRUD) | MCP `call_nautobot` | Skills |
| Data aggregation (N+1) | MCP `run_workflow` | Skills |
| Complex algorithms | MCP `run_workflow` | Skills |
| Cross-MCP orchestration | **Skills** (nautobot + jmcp) | MCP |
| User-interactive flows | **Skills** (dry-run → review → commit) | MCP |
| Discovery | MCP `nautobot_api_catalog` | — |

---

## Impact Analysis

### What Changes

| Component | Change |
|-----------|--------|
| `server.py` | **REWRITTEN** — 116KB/165 tools → ~200 lines/3 tools |
| `catalog/` | **NEW** — static JSON + dynamic CMS discovery |
| `bridge.py` | **NEW** — endpoint routing, validation, pagination |
| `workflows.py` | **NEW** — workflow registry wrapping existing domain functions |
| `skills/` | **UPDATED** — rewritten to reference new 3-tool API |

### What Stays the Same

| Component | Reason |
|-----------|--------|
| `client.py` | pynautobot wrapper unchanged |
| `devices.py`, `interfaces.py`, `ipam.py` | Domain logic untouched |
| `cms/client.py` + `CMS_ENDPOINTS` | CMS generic CRUD reused |
| `cms/routing.py`, `cms/firewalls.py`, etc. | Domain logic untouched |
| `models/` | Pydantic models stay (used by workflows) |
| `cli/` | CLI commands unchanged |
| All domain module tests | Functions unchanged |

### Token Impact

| Metric | Current (165 tools) | After (3 tools) | Reduction |
|--------|---------------------|------------------|-----------|
| Tool descriptions | ~50K tokens | ~1.8K tokens | **96%** |
| `server.py` size | 116KB | ~15KB | **87%** |
| Agent context consumed | High | Minimal | Dramatic |

---

## Migration Strategy

**Clean break** — no backwards compatibility aliases.

**Phases:**
1. Build catalog engine + `nautobot_api_catalog`
2. Build REST bridge + `call_nautobot`
3. Build workflow registry + `run_workflow` (wrapping existing domain functions)
4. Rewrite `server.py` to expose only 3 tools
5. Update agent skills to reference new tool API
6. Update tests
7. UAT against Nautobot dev server

---

*Design v2: API Bridge + Skills Architecture*
*Finalized: 2026-03-24 brainstorming session*
