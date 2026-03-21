---
plan: 09-03
phase: 9
title: CLI Commands & Unit Tests for Routing Models
status: complete
completed: 2026-03-20
---

# Summary: Plan 09-03

## What Was Built

Created CLI routing subcommands and comprehensive unit tests.

## Key Files Created

- `nautobot_mcp/cli/cms_routing.py` — routing Typer subcommands
- `tests/test_cms_routing.py` — 22 unit tests

## Key Files Modified

- `nautobot_mcp/cli/app.py` — registered cms + routing sub-groups

## Tasks Completed

1. ✅ Created `nautobot_mcp/cli/cms_routing.py` with 13 commands:
   - `list-static-routes` (with `--routing-instance`, `--detail` flags)
   - `get-static-route --detail` (shows inlined next-hops)
   - `create-static-route` (device, destination, routing-table, preference)
   - `delete-static-route` (with --yes confirmation bypass)
   - `list-bgp-groups` / `get-bgp-group` / `create-bgp-group` / `delete-bgp-group`
   - `list-bgp-neighbors` (--device OR --group-id)
   - `get-bgp-neighbor` / `create-bgp-neighbor` / `delete-bgp-neighbor`
   - `list-bgp-address-families` (read-only)
   - `list-bgp-policy-associations` (read-only)
   - `list-bgp-received-routes` (read-only, requires --neighbor-id)

2. ✅ Updated `nautobot_mcp/cli/app.py`:
   - Added `cms_app = typer.Typer(name="cms", ...)`
   - Added `cms_app.add_typer(routing_app, name="routing")`
   - Registered as `app.add_typer(cms_app, name="cms")`
   - Commands accessible at: `nautobot-mcp cms routing <cmd>`

3. ✅ Created `tests/test_cms_routing.py` with 22 tests covering:
   - Model tests: StaticRouteSummary (3), BGPGroupSummary (3), BGPNeighborSummary (3), BGPReceivedRouteSummary (1)
   - CRUD tests: list_static_routes with device scope, nexthop inlining, routing instance filter
   - CRUD tests: list_bgp_groups, list_bgp_neighbors (device-scoped, group_id direct, empty)
   - CRUD tests: create_static_route, delete_static_route
   - Read-only: list_bgp_address_families, list_bgp_received_routes, list_static_route_nexthops

## Verification

```
22 tests collected
22 tests PASSED
153 total tests PASSED (full suite)
CLI: nautobot-mcp cms routing --help works
```

## Self-Check: PASSED
