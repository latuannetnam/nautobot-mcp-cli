# Phase 35: `interface_detail` N+1 Fix - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-31
**Phase:** 35-interface-detail-n1-fix
**Areas discussed:** Family Prefetch Strategy, VRRP Prefetch Boundary, Partial Failure Handling

---

## Area 1: Family Prefetch Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Inside `get_interface_detail` only | Bulk fetch in `get_interface_detail` only, leave `list_interface_units` unchanged | ✓ |
| Shared via `list_interface_units` refactor | Refactor `list_interface_units` to return family lookup map | |
| New shared helper function | Create `_get_families_by_unit()` helper callable from both places | |

**User's choice:** Inside `get_interface_detail` only
**Notes:** Recommended approach. `list_interface_units` serves a different purpose (counts), refactoring risks breaking CLI callers, shared helper adds unnecessary abstraction.

---

## Area 2: VRRP Prefetch Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Bulk VRRP prefetch, family_id → VRRPGroup map | 1 bulk call, build lookup map, use map lookups | ✓ |
| Skip VRRP entirely | Remove VRRP enrichment from `get_interface_detail` | |
| Keep existing per-family memoized approach | Leave `_get_vrrp_for_family` with per-family HTTP calls | |

**User's choice:** Bulk VRRP prefetch, family_id → VRRPGroup map
**Notes:** Standard approach — same pattern as family prefetch.

---

## Area 3: Partial Failure Handling (CQP-05)

| Option | Description | Selected |
|--------|-------------|----------|
| Family: hard-fail / VRRP: graceful | Family prefetch failure → hard-fail. VRRP prefetch failure → WarningCollector + empty map. | ✓ |
| Both: graceful degradation | Both bulk prefetches caught, WarningCollector.add, continue with empty maps | |
| Both: hard-fail | Both bulk prefetches propagate exceptions on failure | |

**User's choice:** Family: hard-fail / VRRP: graceful
**Notes:** Recommended approach. Family data is critical for `detail=True` enrichment. VRRP is non-critical enrichment. Matches existing VRRP graceful degradation pattern in `_get_vrrp_for_family`.

---

## Claude's Discretion

- Exact placement of prefetch block in `get_interface_detail` (after `units_resp`, before unit processing loop)
- Whether `_get_vrrp_for_family` keeps its memoization cache after the map is available (planner to decide based on `get_interface_unit` compatibility)
- Threshold timing for smoke test validation

## Deferred Ideas

- `get_interface_unit` VRRP enrichment fix (separate from Phase 35 scope)
- `list_interface_units` deduplication (separate from Phase 35 scope)
