# Plan 12-02: Routing Composite Functions and MCP Tools — SUMMARY

## What Was Done

### BGP and Routing Table Composite Functions
Added 2 composite summary functions to `nautobot_mcp/cms/routing.py`:

1. **`get_device_bgp_summary(client, device, detail=False)`**
   - Fetches all BGP groups + neighbors for a device
   - Default: groups with `neighbor_count`
   - Detail: each group includes nested neighbors with address families and policy associations

2. **`get_device_routing_table(client, device, detail=False)`**
   - Fetches static routes for a device (via `list_static_routes`)
   - Default: routes with `nexthop_count` (lists stripped)
   - Detail: routes with full nexthop lists inlined

### MCP Tools Registered
Added 2 MCP tools to `nautobot_mcp/server.py` before the CMS INTERFACE TOOLS section:
- `nautobot_cms_get_device_bgp_summary`
- `nautobot_cms_get_device_routing_table`

## Acceptance Criteria Verified
- [x] `from nautobot_mcp.cms.routing import get_device_bgp_summary` — OK
- [x] `from nautobot_mcp.cms.routing import get_device_routing_table` — OK
- [x] `from nautobot_mcp.server import mcp` — Server loads OK

## Commit
`feat(phase-12): add BGP+routing composite functions and MCP tools (plan 12-02)`
