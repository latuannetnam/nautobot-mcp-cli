---
gsd_state_version: 1.0
milestone: v1.4
milestone_name: Operational Robustness
status: Phase 22 Complete
last_updated: "2026-03-26T10:30:00.000Z"
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 8
  completed_plans: 8
---

# Project State: nautobot-mcp-cli

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-25)

**Core value:** AI agents can read and write Nautobot data through standardized MCP tools
**Current focus:** Phase 22 — response-ergonomics-uat

## Current Position

Phase: 22 (response-ergonomics-uat) — COMPLETE
Plan: 1 of 1

Milestone v1.4 Operational Robustness: ALL 4 PHASES COMPLETE

## Context

**Goal:** Fix confirmed pain points in the MCP bridge: partial failure resilience, catalog accuracy, error diagnostics, response ergonomics, endpoint dereference, and workflow parameter contracts.

**Pain points from user reports (verified against v1.3 codebase):**

- P1: Composite workflow all-or-nothing failure (routing.py get_device_bgp_summary)
- P2: Catalog/runtime filter mismatch (cms_discovery.py CMS_DOMAIN_FILTERS)
- P3: Linked object dereference gap (bridge.py _validate_endpoint)
- P4: Workflow parameter contract ambiguity (workflows.py verify_data_model)
- P5: Generic error feedback (client.py _handle_api_error)
- P6: Large response payloads (composite workflows lack summary/limit)

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
| API Bridge MCP Server | v1.3 | 165 tools → 3 via catalog + REST bridge + workflows; 96% token reduction |
| Clean break (no aliases) | v1.3 | Long-term clarity over short-term compatibility |
| CLI unchanged | v1.3 | CLI calls domain modules directly, not MCP tools |
| Skills as files (not MCP) | v1.3 | Cross-MCP orchestration + user-interactive flows stay agent-side |
| Exception-as-warning envelope | 21 | ERR-03: exceptions in composite workflows captured as {operation, error} warning dicts; backward-compat preserved via error field |

## Accumulated Context

- v1.0 shipped 2026-03-18 with 44+ MCP tools, CLI, agent skills
- v1.1 shipped 2026-03-20 with 46 MCP tools, 105 tests, ~11k LOC
- v1.2 shipped 2026-03-21 with 164 MCP tools, 293 tests, ~13k LOC
- v1.3 shipped 2026-03-25 with 3 MCP tools, 397 tests, ~3.2k LOC
- Architecture: shared core library + thin MCP/CLI layers
- jmcp `show configuration | display json` returns null for large configs
- pynautobot `ip_addresses.filter(interface_id=...)` not a valid filter
- Nautobot IPs often have `assigned_object_id=None` (unlinked)
- netnam-cms-core has 40+ Juniper models across routing, interfaces, firewalls, policies, ARP
- cms/client.py already has CMS_ENDPOINTS registry + generic CRUD helpers
- User-reported pain points verified against codebase (6/6 confirmed or partially confirmed)
- ERR-03: composite workflow exceptions now include {operation, error} warning entries in error envelope
- RSP-01: `interface_detail(detail=False)` summary mode strips nested arrays, keeps counts
- RSP-02: `response_size_bytes` added to all workflow envelopes (measured as `len(json.dumps(data))`)
- RSP-03: `limit=N` added to all 4 composite functions with per-array independent caps

## Blockers

None.

---
*State initialized: 2026-03-17*
*Last updated: 2026-03-25 — Phase 19 (Partial Failure Resilience) completed: WarningCollector, envelope three-tier status, 4 composite function refactors, 415 tests pass*

```
