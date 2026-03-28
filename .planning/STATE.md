---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: Agent Performance & Quality
status: completed
last_updated: "2026-03-28T09:51:31.067Z"
last_activity: 2026-03-28
progress:
  total_phases: 23
  completed_phases: 22
  total_plans: 55
  completed_plans: 54
---

# Project State: nautobot-mcp-cli

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-28)

**Core value:** AI agents can discover, read, write, and orchestrate Nautobot data through 3 tools instead of 165
**Current focus:** Phase 28 — adaptive-count-fast-pagination

## Current Position

Phase: 28
Plan: Not started
Status: Phase 28 plan 01 complete — all 6 tasks executed and committed
Last activity: 2026-03-28

## Context

**Phase 28 status:** ✅ COMPLETE — all 6 tasks committed; skip_count plumbed through all layers
**Phase 29 scope:** Replace all pynautobot count() calls with direct /count/ endpoint; wire skip_count in bridge

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

## Phase 28 Decisions (completed 2026-03-28)

| Decision | Rationale |
|----------|-----------|
| D-01: `has_more = len(results) == limit` when count skipped | Exact `limit` results → `has_more=True`; fewer → `has_more=False` |
| D-02: Null totals when count skipped | Honest signal — `total_*` fields are `None` in JSON when counts not fetched |
| D-03: `skip_count` param plumbed through CLI + workflow + bridge + MCP tool | Unified across all interfaces, not just CLI |
| D-04: Per-section timing granularity | `interfaces_latency_ms`, `ips_latency_ms`, `vlans_latency_ms`, `total_latency_ms` |
| D-05: Parallel counts for `detail=all` via `ThreadPoolExecutor(max_workers=3)` | Max of 3 latencies instead of sum; sequential fallback on any failure |
| D-06: `limit=0` auto-enables `skip_count` | Unlimited mode should never pay count overhead |

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
