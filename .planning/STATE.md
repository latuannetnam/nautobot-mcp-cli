# Project State: nautobot-mcp-cli

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-17)

**Core value:** AI agents can read and write Nautobot data through standardized MCP tools
**Current focus:** Phase 1 — Core Foundation & Nautobot Client

## Current Phase

**Phase 1: Core Foundation & Nautobot Client**
- Status: Not Started
- Requirements: CORE-01–04, DEV-01–05, INTF-01–05, IPAM-01–06, ORG-01–04, CIR-01–03
- Plans: None yet

## Progress

| Phase | Status | Plans | Progress |
|-------|--------|-------|----------|
| 1     | ○      | 0/0   | 0%       |
| 2     | ○      | 0/0   | 0%       |
| 3     | ○      | 0/0   | 0%       |
| 4     | ○      | 0/0   | 0%       |

## Key Decisions

| Decision | Phase | Rationale |
|----------|-------|-----------|
| FastMCP 3.0 for MCP server | 1 | De facto standard, type-hint driven, official SDK |
| pynautobot for API client | 1 | Official Nautobot SDK, handles pagination/auth |
| Typer for CLI | 2 | Consistent type-hint patterns with FastMCP |
| Juniper-first parser | 3 | jmcp already available, extensible architecture |

## Blockers

None.

---
*State initialized: 2026-03-17*
*Last updated: 2026-03-17*
