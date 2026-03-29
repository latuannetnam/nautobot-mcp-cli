---
gsd_state_version: 1.0
milestone: v1.7
milestone_name: URI Limit & Server Resilience
status: verifying
last_updated: "2026-03-29T02:45:33.637Z"
last_activity: 2026-03-29
progress:
  total_phases: 25
  completed_phases: 24
  total_plans: 57
  completed_plans: 56
---

# Project State: nautobot-mcp-cli

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-29)

**Core value:** AI agents can discover, read, write, and orchestrate Nautobot data through 3 tools instead of 165
**Current focus:** Phase 30 — direct-http-bulk-fetch

## Current Position

Phase: 30 (direct-http-bulk-fetch) — EXECUTING
Plan: 1 of 1
Context: `.planning/phases/30-direct-http-bulk-fetch/30-CONTEXT.md`
Status: Phase complete — ready for verification
Last activity: 2026-03-29

## Context

**v1.6 status:** ✅ COMPLETE — shipped 2026-03-28 with skip_count and direct /count/ endpoint

**v1.7 Goal:** Eliminate all 414 Request-URI Too Large errors and address VLANs 500 errors.

**Root causes identified:**

1. **414 in ipam.py `get_device_ips()`:** `.filter(id__in=chunk)` and `.filter(interface=chunk)` use repeated query params → ~18 KB per 500-UUID chunk → 414 for large devices. Fix: direct HTTP with comma-separated DRF format.

2. **414 in bridge.py (`_execute_core()` + `_execute_cms()`):** No guard on caller-supplied `params`. External callers can inject `id__in=[uuid1..uuid10000]` → 414 on any endpoint. Fix: `_guard_filter_params()` with 500-item limit on `__in` lists.

3. **500 in VLANs count:** CLI passes `location=HQV` (name) to `/api/ipam/vlans/count/`. Nautobot's VLAN queryset annotation + ManyToMany location JOIN + name-based filter → ORM crash → 500. Fix: resolve location name→UUID before calling `/count/`.

**Impact:** `device-ips HQV-PE1-NEW` fails with 414; `devices summary HQV-PE1-NEW` fails with 500 on VLAN count.

## Key Decisions

| Decision | Phase | Rationale |
|----------|-------|-----------|
| Skip count for paginated requests | v1.6 | O(1) vs O(n) — eliminates all wasteful fetches |
| Infer has_more from result count | v1.6 | When limit is respected, `len == limit` means more exist |
| Direct `/count/` endpoint fallback | v1.6 | When count IS needed, bypass pynautobot for true O(1) |
| Adaptive count strategy | v1.6 | Only count when `detail=all` or `limit=0` |
| Instrument timing in output | v1.6 | Observable performance for users and agents |
| Direct HTTP with comma-separated for IP/M2M bulk | v1.7 | `?id__in=a,b,c` ~3x shorter than `?id__in=a&id__in=b&id__in=c` |
| Bridge guard rejects `__in` lists > 500 | v1.7 | Caller must chunk — prevents 414 from external agents |
| Raise vs auto-chunk on bridge guard | v1.7 | Raise error — auto-chunking would hide bad caller patterns |
| Location name → UUID before VLANs count | v1.7 | UUID avoids Nautobot's `TreeNodeMultipleChoiceFilter` name→object resolution path that triggers ORM crash |
| 500 fallback returns `None` | v1.7 | Count unavailable → `null` in output; operation continues |

## Accumulated Context

- v1.0 shipped 2026-03-18 with core MCP + CLI + parsing/onboarding foundations
- v1.1 shipped 2026-03-20 with agent-native tools and file-free drift
- v1.2 shipped 2026-03-21 with Juniper CMS CRUD + composite tools + CMS drift
- v1.3 shipped 2026-03-25 with 165→3 API Bridge consolidation
- v1.4 shipped 2026-03-26 with robustness, diagnostics, and response ergonomics
- v1.6 shipped 2026-03-28 with query performance optimizations
- v1.7 started 2026-03-29 to address 414 URI limit errors and VLANs 500 errors

## Blockers

None.

---
*State initialized: 2026-03-28*
*Last updated: 2026-03-29 — v1.7 milestone defined*
