---
plan: 09-02
phase: 9
title: MCP Server Tools for Routing Models
status: complete
completed: 2026-03-20
---

# Summary: Plan 09-02

## What Was Built

Added 14 MCP tool wrappers in `nautobot_mcp/server.py` for all routing CMS operations.

## Key Files Modified

### key-files.modified
- `nautobot_mcp/server.py` — added CMS routing import and 14 MCP tools

## Tasks Completed

1. ✅ Added `from nautobot_mcp.cms import routing as cms_routing` import
2. ✅ Added CMS ROUTING TOOLS section with 14 tool functions:
   - Static routes: list (with routing_instance filter), get, create, update, delete
   - BGP groups: list (device-scoped), get, create (with local_address/cluster_id), update, delete
   - BGP neighbors: list (device OR group_id filter), get, create, update, delete
   - BGP address families: list (read-only, group or neighbor filter)
   - BGP policy associations: list (read-only, group or neighbor filter)
   - BGP received routes: list (read-only, neighbor_id required)
   - Static route nexthops: list (read-only, route or device filter)

## Verification

```
Server module loads successfully
```

## Self-Check: PASSED
