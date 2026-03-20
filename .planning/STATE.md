---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Agent-Native MCP Tools
status: active
last_updated: "2026-03-20T03:40:49.000Z"
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 15
  completed_plans: 15
---

# Project State: nautobot-mcp-cli

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-20)

**Core value:** AI agents can read and write Nautobot data through standardized MCP tools
**Current focus:** Phase 6 — Device Summary & Enriched Interface Data

## Current Position

Phase: 6 (Device Summary & Enriched Interface Data) — NOT STARTED
Plan: 0 of 0 (needs discuss → plan → execute)

## Context

**Problem discovered:** During a real-world IP drift comparison (HQV-PE-Test MX204 vs Nautobot), the AI agent had to write a 100-line Python script because MCP tools couldn't answer basic questions like "what IPs are on this device's interfaces?" in a single call.

**Goal:** Eliminate agent scripting by adding composite tools, cross-entity filters, and file-free drift comparison.

## Progress

| Phase | Status | Plans | Progress |
|-------|--------|-------|----------|
| Phase 5 | ✅ Completed | 2/2 | 100% |
| Phase 6 | ⬜ Not started | 0/0 | 0% |
| Phase 7 | ⬜ Not started | 0/0 | 0% |

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

## Accumulated Context

- v1.0 shipped 2026-03-18 with 44+ MCP tools, CLI, agent skills
- 76 unit tests passing
- Architecture: shared core library + thin MCP/CLI layers
- jmcp `show configuration | display json` returns null for large configs
- pynautobot `ip_addresses.filter(interface_id=...)` not a valid filter
- Nautobot IPs often have `assigned_object_id=None` (unlinked)

## Blockers

None.

---
*State initialized: 2026-03-17*
*Last updated: 2026-03-20T10:40:00+07:00*
