---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: — Juniper CMS Model MCP Tools
status: executing
last_updated: "2026-03-20T17:00:00.000Z"
progress:
  total_phases: 7
  completed_phases: 2
  total_plans: 8
  completed_plans: 5
---

# Project State: nautobot-mcp-cli

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-20)

**Core value:** AI agents can read and write Nautobot data through standardized MCP tools
**Current focus:** Phase 09 — ✅ COMPLETE — next: Phase 10

## Current Position

Phase: 09 (routing-models-static-routes-bgp) — **COMPLETE** ✅
Plans completed: 3 of 3

Next: Phase 10 (to be planned)

## Phase 09 Summary

All 3 plans executed:
- **09-01**: 8 Pydantic routing models + 20+ CRUD functions
- **09-02**: 14 MCP tools in server.py (nautobot_cms_ prefix)
- **09-03**: 13 CLI commands + 22 unit tests (153 total passing)

Key files added:
- `nautobot_mcp/models/cms/routing.py` — StaticRoute, BGPGroup, BGPNeighbor, etc.
- `nautobot_mcp/cms/routing.py` — all CRUD + nexthop inlining
- `nautobot_mcp/cli/cms_routing.py` — routing subcommands
- `tests/test_cms_routing.py` — 22 unit tests
- server.py extended with 14 nautobot_cms_* tools

## Context

**Goal:** Add full CRUD MCP tools for all Juniper-specific models in the netnam-cms-core Nautobot plugin, plus composite summary tools and live drift verification against CMS model records.

**Scope:** All 5 Juniper model domains (Routing, Interfaces, Firewalls, Policies, ARP) with 40+ models and 49 REST API endpoints.

## Key Decisions

| Decision | Phase | Rationale |
|----------|-------|-----------|
| FastMCP 3.0 for MCP server | 1 | De facto standard, type-hint driven, official SDK |
| pynautobot for API client | 1 | Official Nautobot SDK, handles pagination/auth |
| Typer for CLI | 2 | Consistent type-hint patterns with FastMCP |
| Juniper-first parser | 3 | jmcp already available, extensible architecture |
| VendorParser ABC + registry | 3 | Extensible to other vendors via network_os identifier |
| JSON parser for JunOS | 3 | `show configuration | display json` provides structured data |
| DiffSync v2 for verification | 4 | Object-by-object diff with structured output |
| Factory-style adapter init | 4 | DiffSync v2 Adapter.__new__ only accepts kwargs |
| netnam-cms-core via plugin API | v1.2 | Plugin exposes 49 DRF endpoints, consume directly |
| CMS routing nexthop inlining | 9 | Static route nexthops inlined into parent for MCP efficiency |
| BGP neighbor device-scoping | 9 | Neighbors scoped via group → device chain for device queries |

## Accumulated Context

- v1.0 shipped 2026-03-18 with 44+ MCP tools, CLI, agent skills
- v1.1 shipped 2026-03-20 with 46 MCP tools, 105 tests, ~11k LOC
- v1.2 in progress: Phase 8 (CMS foundation) + Phase 9 (routing) done
- Architecture: shared core library + thin MCP/CLI layers
- jmcp `show configuration | display json` returns null for large configs
- pynautobot `ip_addresses.filter(interface_id=...)` not a valid filter
- Nautobot IPs often have `assigned_object_id=None` (unlinked)
- netnam-cms-core has 40+ Juniper models across routing, interfaces, firewalls, policies, ARP

## Blockers

None.

---
*State initialized: 2026-03-17*
*Last updated: 2026-03-20T17:00:00+07:00*
