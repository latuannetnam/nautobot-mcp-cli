---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: — Juniper CMS Model MCP Tools
status: unknown
last_updated: "2026-03-20T15:03:27.000Z"
progress:
  total_phases: 7
  completed_phases: 1
  total_plans: 2
  completed_plans: 2
---

# Project State: nautobot-mcp-cli

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-20)

**Core value:** AI agents can read and write Nautobot data through standardized MCP tools
**Current focus:** Phase 09 — routing-models-static-routes-bgp

## Current Position

Phase: 09 (routing-models-static-routes-bgp) — PLANNED
Plan: 0 of 3 (ready for execution)

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

## Accumulated Context

- v1.0 shipped 2026-03-18 with 44+ MCP tools, CLI, agent skills
- v1.1 shipped 2026-03-20 with 46 MCP tools, 105 tests, ~11k LOC
- Architecture: shared core library + thin MCP/CLI layers
- jmcp `show configuration | display json` returns null for large configs
- pynautobot `ip_addresses.filter(interface_id=...)` not a valid filter
- Nautobot IPs often have `assigned_object_id=None` (unlinked)
- netnam-cms-core has 40+ Juniper models across routing, interfaces, firewalls, policies, ARP

## Blockers

None.

---
*State initialized: 2026-03-17*
*Last updated: 2026-03-20T16:43:00+07:00*
