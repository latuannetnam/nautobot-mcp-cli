---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: — Generic Resource Engine
status: defining-requirements
last_updated: "2026-03-24T11:25:00.000Z"
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State: nautobot-mcp-cli

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-24)

**Core value:** AI agents can read and write Nautobot data through standardized MCP tools
**Current focus:** Defining requirements for v1.3 Generic Resource Engine

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-24 — Milestone v1.3 started

## Context

**Goal:** Re-architect MCP tool layer from 165 individual tools to ~18 using a Generic Resource Engine pattern. Eliminate context window bloat (33% → ~3.5%) and restore agent accuracy.

**Scope:**
- Resource Registry module (`registry.py`) with unified catalog
- 3 generic discovery/CRUD tools replacing ~150 individual wrappers
- ~15 preserved composite workflow tools
- Clean break migration (no backwards compatibility)
- UAT against Nautobot dev server (http://101.96.85.93)

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
| Generic Resource Engine | v1.3 | 165 tools → ~18 via unified dispatcher; 33% → 3.5% context |
| Clean break (no aliases) | v1.3 | Long-term clarity over short-term compatibility |
| CLI unchanged | v1.3 | CLI calls domain modules directly, not MCP tools |

## Accumulated Context

- v1.0 shipped 2026-03-18 with 44+ MCP tools, CLI, agent skills
- v1.1 shipped 2026-03-20 with 46 MCP tools, 105 tests, ~11k LOC
- v1.2 shipped 2026-03-21 with 164 MCP tools, 293 tests, ~13k LOC
- Architecture: shared core library + thin MCP/CLI layers
- jmcp `show configuration | display json` returns null for large configs
- pynautobot `ip_addresses.filter(interface_id=...)` not a valid filter
- Nautobot IPs often have `assigned_object_id=None` (unlinked)
- netnam-cms-core has 40+ Juniper models across routing, interfaces, firewalls, policies, ARP
- cms/client.py already has CMS_ENDPOINTS registry + generic CRUD helpers (cms_list/get/create/update/delete)
- Research: AI accuracy drops <2% at 7+ domains (LangChain 2025); 165 tools consume ~66K tokens/request

## Blockers

None.

---
*State initialized: 2026-03-17*
*Last updated: 2026-03-24 — v1.3 milestone started*
