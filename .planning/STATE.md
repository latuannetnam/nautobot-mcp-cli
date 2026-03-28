---
gsd_state_version: 1.0
milestone: v1.6
milestone_name: Query Performance Optimization
status: Requirements defined
last_updated: "2026-03-28T00:00:00.000Z"
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State: nautobot-mcp-cli

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-28)

**Core value:** AI agents can discover, read, write, and orchestrate Nautobot data through 3 tools instead of 165
**Current focus:** v1.6 — Query Performance Optimization

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Requirements defined
Last activity: 2026-03-28 — v1.6 milestone defined

## Context

**Goal:** Fix slow CLI and MCP queries for devices with large interface/IP counts.

**Root cause identified:**
- `pynautobot.count(device=name)` does NOT use `/count/` endpoint
- Instead calls `.filter()` → auto-paginates through ALL pages → returns `len(results)`
- For HQV-PE1-NEW (700+ interfaces): wastes ~700+ record fetches + Record→dict conversions
- The count is only needed for the "total: N" header and `has_more` flag
- When user requests `--limit 5`, they don't need the total count upfront

**Impact:** `devices inventory HQV-PE1-NEW --limit 5` is slow because of count fetch, not data fetch

**Fix strategy:** Skip count when `limit > 0` and `detail != "all"`; infer `has_more` from `returned_count == limit`

## Key Decisions

| Decision | Phase | Rationale |
|----------|-------|-----------|
| Skip count for paginated requests | v1.6 | O(1) vs O(n) — eliminates all wasteful fetches |
| Infer has_more from result count | v1.6 | When limit is respected, `len == limit` means more exist |
| Direct `/count/` endpoint fallback | v1.6 | When count IS needed, bypass pynautobot for true O(1) |
| Adaptive count strategy | v1.6 | Only count when `detail=all` or `limit=0` |
| Instrument timing in output | v1.6 | Observable performance for users and agents |

## Accumulated Context

- v1.0 shipped 2026-03-18 with core MCP + CLI + parsing/onboarding foundations
- v1.1 shipped 2026-03-20 with agent-native tools and file-free drift
- v1.2 shipped 2026-03-21 with Juniper CMS CRUD + composite tools + CMS drift
- v1.3 shipped 2026-03-25 with 165→3 API Bridge consolidation
- v1.4 shipped 2026-03-26 with robustness, diagnostics, and response ergonomics
- v1.5 phases 23-27 planned for 2026-03-28 — Agent Performance & Quality
- v1.6 started 2026-03-28 to address query-level performance root causes

## Blockers

None.

---
*State initialized: 2026-03-28*
*Last updated: 2026-03-28 — v1.6 milestone defined*
