# Phase 36: `firewall_summary` Detail N+1 Fix - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-31
**Phase:** 36-firewall-summary-n1-fix
**Areas discussed:** Bulk Prefetch Architecture, Partial Failure Handling (CQP-05), HTTP Call Budget, Unit Test Strategy

---

## Bulk Prefetch Architecture

| Option | Description | Selected |
|--------|-------------|----------|
| Same as Phase 35 (Recommended) | Inline prefetch block inside get_device_firewall_summary: 1 bulk terms + 1 bulk actions → lookup maps → dict lookups replace N loops | ✓ |
| Refactor list_firewall_terms to return shared lookup map | Refactor list_firewall_terms to support both summary and detail enrichment via shared lookup map | |
| You decide | Trust Claude to pick based on Phase 35 precedent | |

**User's choice:** Same as Phase 35 (Recommended)
**Notes:** Consistency with Phase 35 pattern; inline prefetch in workflow function only.

---

## Partial Failure Handling (CQP-05)

| Option | Description | Selected |
|--------|-------------|----------|
| Graceful degradation (Recommended) | Catch prefetch exception, add warning, return empty array — same as current behavior in the try/except blocks | ✓ |
| Hard-fail (propagate exception) | Bulk term prefetch failure raises immediately — mirrors Phase 35 family prefetch | |

**User's choice:** Graceful degradation (Recommended)
**Notes:** Terms/actions are enrichment for detail=True; the detail=False co-primary (term_count/action_count) already succeeded; partial data with warning is acceptable.

---

## HTTP Call Budget

| Option | Description | Selected |
|--------|-------------|----------|
| ≤6 (Recommended) | 2 co-primaries + 2 list-scoped bulks + 2 detail-scoped bulks = 6 max. Matches CQP-02 target in STATE.md. | ✓ |
| ≤4 (aggressive) | Deduplicate list-scoped and detail-scoped bulks — riskier to implement | |
| No specific budget | Just eliminate N+1 loops | |

**User's choice:** ≤6 (Recommended)
**Notes:** Matches CQP-02 from STATE.md.

---

## Unit Test Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| New dedicated test file (Recommended) | tests/test_cms_firewalls_n1.py with N+1 invariant tests — same pattern as Phase 35 | ✓ |
| Add to existing firewall tests | tests/test_cms_firewalls.py | |
| You decide | Trust Claude to pick | |

**User's choice:** New dedicated test file (Recommended)
**Notes:** Consistency with Phase 35; dedicated test file makes regression detection clear.

---

## Claude's Discretion

- Exact prefetch variable naming inside `get_device_firewall_summary`
- How to merge the `detail=False` dict-building logic with `detail=True` prefetch (keep separate or share)
- Exact placement of try/except blocks for graceful degradation
- Test fixture structure and mock response shapes

## Deferred Ideas

- `list_firewall_terms` deduplication — both `list_firewall_filters` (for term_count) and detail=True prefetch could share the same bulk term fetch. Future phase.
- `list_firewall_policer_actions` deduplication — same pattern for policer actions. Future phase.
