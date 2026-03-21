---
plan: 09-01
phase: 9
title: Routing Pydantic Models & Core CRUD Functions
status: complete
completed: 2026-03-20
---

# Summary: Plan 09-01

## What Was Built

Created all Pydantic models and CRUD functions for Juniper routing models.

## Key Files Created

### key-files.created
- `nautobot_mcp/models/cms/routing.py` — 8 Pydantic model classes
- `nautobot_mcp/cms/routing.py` — 20+ domain CRUD functions

### key-files.modified
- `nautobot_mcp/models/cms/__init__.py` — added 8 routing model exports
- `nautobot_mcp/cms/__init__.py` — exposed routing module

## Tasks Completed

1. ✅ Created `nautobot_mcp/models/cms/routing.py` with all 8 model classes:
   - `StaticRouteSummary` — with `nexthops` and `qualified_nexthops` lists
   - `StaticRouteNexthopSummary` — with nested IP/interface extraction
   - `StaticRouteQualifiedNexthopSummary` — extends nexthop with interface_name
   - `BGPGroupSummary` — with routing_instance and local_address FK extraction
   - `BGPNeighborSummary` — with group, peer_ip, session statistics
   - `BGPAddressFamilySummary` — grouped by group or neighbor
   - `BGPPolicyAssociationSummary` — policy FK extraction
   - `BGPReceivedRouteSummary` — read-only with prefix/next-hop extraction

2. ✅ Updated `nautobot_mcp/models/cms/__init__.py` — all 8 models exported

3. ✅ Created `nautobot_mcp/cms/routing.py` with all CRUD functions:
   - Static routes: list (with inlined nexthops), get (with inlined nexthops), create, update, delete
   - Static route nexthops: list, get (list/get only)
   - Static route qualified nexthops: list, get (list/get only)
   - BGP groups: list (device-scoped), get, create, update, delete
   - BGP neighbors: list (device-scoped via groups OR group_id filter), get, create, update, delete
   - BGP address families: list, get (list/get only)
   - BGP policy associations: list, get (list/get only)
   - BGP received routes: list, get (list/get only)

4. ✅ Updated `nautobot_mcp/cms/__init__.py` — routing module exposed

## Verification

All acceptance criteria passed:
```
All models importable
Package exports ok
CRUD functions importable
cms.routing module ok
```

## Self-Check: PASSED
