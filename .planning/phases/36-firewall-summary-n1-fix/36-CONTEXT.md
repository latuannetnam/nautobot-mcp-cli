# Phase 36: `firewall_summary` Detail N+1 Fix - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Eliminate N+1 HTTP query loops in `get_device_firewall_summary()` with `detail=True` in `nautobot_mcp/cms/firewalls.py`. Two specific patterns:

1. **Per-filter term refetch (N+1 #1):** `list_firewall_terms(client, filter_id=fw_filter.id)` called per-filter in a loop (L704-717). With many filters on a device: many sequential HTTP calls instead of 1.
2. **Per-policer action refetch (N+1 #2):** `list_firewall_policer_actions(client, policer_id=policer.id)` called per-policer (L722-733). With many policers: many sequential HTTP calls instead of 1.

Goal (CQP-02): `get_device_firewall_summary(detail=True)` makes ≤6 HTTP calls regardless of filter/policer count.

Out of scope: `detail=False` path (already correct — term_count and action_count populated by list-scoped bulk fetches), other CMS workflows.

</domain>

<decisions>
## Implementation Decisions

### Bulk Prefetch Architecture
- **D-01:** Same inline prefetch pattern as Phase 35 — add bulk prefetch block **inside `get_device_firewall_summary`** only. Do NOT refactor `list_firewall_terms()` or `list_firewall_policer_actions()` to return shared lookup maps. The duplicate prefetch between the `detail=False` list-scoped bulks and the `detail=True` prefetch is acceptable.
- **D-02:** Prefetch block comes inside the `if detail:` branch, immediately after co-primary fetches complete:
  1. Bulk terms: `cms_list(client, 'juniper_firewall_terms', FirewallTermSummary, device=device_id, limit=0)` → `terms_by_filter[filter_id] = [terms]`
  2. Bulk actions: `cms_list(client, 'juniper_firewall_policer_actions', FirewallPolicerActionSummary, device=device_id, limit=0)` → `actions_by_policer[policer_id] = [actions]`
- **D-03:** Replace per-filter `list_firewall_terms(filter_id=...)` loop with dict lookups: `terms_by_filter.get(fw_filter.id, [])`. Replace per-policer `list_firewall_policer_actions(policer_id=...)` loop with dict lookups: `actions_by_policer.get(policer.id, [])`.

### Partial Failure Handling (CQP-05)
- **D-04:** Term prefetch failure → graceful degradation: wrap in try/except, `WarningCollector.add("bulk_terms_fetch", str(e))`, use empty dict `{}`. Terms are enrichment for detail=True but the `detail=False` co-primary (term_count) already succeeded — partial data is acceptable.
- **D-05:** Action prefetch failure → graceful degradation: same pattern as terms. Wrap in try/except, add warning, use empty dict.
- **D-06:** If the co-primary (filters or policers) itself failed before reaching detail enrichment, the existing top-level exception propagation already handles it — the detail enrichment try/except only applies when co-primaries succeeded.

### HTTP Call Budget (CQP-02)
- **D-07:** Target: ≤6 HTTP calls in `get_device_firewall_summary(detail=True)` for a fully-enriched response:
  1. `list_firewall_filters` co-primary (filters)
  2. `list_firewall_policers` co-primary (policers)
  3. Bulk terms prefetch: `cms_list(..., device=device_id)` — already 1 call (not 1 per filter)
  4. Bulk actions prefetch: `cms_list(..., device=device_id)` — already 1 call (not 1 per policer)
  5. `list_firewall_terms(filter=...)` in `list_firewall_filters` — term_count bulk (already correct in list_ call, NOT the per-filter loop)
  6. `list_firewall_policer_actions(policer=...)` in `list_firewall_policers` — action_count bulk (already correct)

  Note: Calls 3-6 are all distinct bulk fetches — none are inside per-item loops after the fix.

### Unit Test Strategy
- **D-08:** New dedicated test file: `tests/test_cms_firewalls_n1.py` with N+1 invariant tests for `get_device_firewall_summary`. Follow Phase 35 pattern (`test_cms_interfaces_n1.py`): monkey-patch `cms_list` in the firewall module to count HTTP calls, assert ≤N regardless of how many filters/policers/terms/actions are in the mocked responses.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 36 Requirements
- `.planning/ROADMAP.md` §v1.10 — Phase 36 goal: CQP-02 (≤6 HTTP calls), CQP-05 (WarningCollector preserved)
- `.planning/REQUIREMENTS.md` §CQP — CQP-02 (≤6 HTTP calls), CQP-05 (WarningCollector preserved)
- `.planning/STATE.md` — Root cause: per-filter term refetch loop, per-policer action refetch loop; Phase 35 precedent decisions

### Prior Phase Decisions
- `.planning/phases/35-interface-detail-n1-fix/35-CONTEXT.md` — Inline prefetch pattern, hard-fail for critical data, graceful degradation for non-critical, ≤3 call budget, dedicated test file
- `.planning/phases/33-cms-pagination-fix/33-CONTEXT.md` — `_CMS_BULK_LIMIT = 200` constant
- `.planning/phases/19-partial-failure-resilience/19-CONTEXT.md` — `WarningCollector` pattern and co-primaries pattern

### Codebase References
- `nautobot_mcp/cms/firewalls.py` — `get_device_firewall_summary()` (L654-750) — PRIMARY fix target
- `nautobot_mcp/cms/firewalls.py` — `list_firewall_filters()` (L45-90) — already has correct bulk term count prefetch
- `nautobot_mcp/cms/firewalls.py` — `list_firewall_policers()` (L224-264) — already has correct bulk action count prefetch
- `nautobot_mcp/cms/firewalls.py` — `list_firewall_terms()` (L366-425) — existing CRUD function with bulk mc/actions fetching
- `nautobot_mcp/cms/client.py` — `cms_list()` (L135-168) — already handles `_CMS_BULK_LIMIT = 200`
- `nautobot_mcp/cms/client.py` — `CMS_ENDPOINTS` registry (L46-51) — endpoint names for firewall terms and policer actions
- `nautobot_mcp/warnings.py` — `WarningCollector` — already imported in `get_device_firewall_summary`
- `nautobot_mcp/models/cms/composites.py` — `FirewallSummaryResponse` Pydantic model
- `nautobot_mcp/workflows.py` — `firewall_summary` workflow stub

### Test References
- `tests/test_cms_interfaces_n1.py` — Phase 35 N+1 invariant tests (pattern to replicate)
- `scripts/uat_cms_smoke.py` — existing smoke test infrastructure

</canonical_refs>

<codebase_context>
## Existing Code Insights

### Reusable Assets
- `cms_list(client, 'juniper_firewall_terms', FirewallTermSummary, device=device_id, limit=0)` — correct endpoint for bulk terms prefetch, registered in `CMS_ENDPOINTS`
- `cms_list(client, 'juniper_firewall_policer_actions', FirewallPolicerActionSummary, device=device_id, limit=0)` — correct endpoint for bulk actions prefetch
- `WarningCollector` already imported and wired in `get_device_firewall_summary`
- `list_firewall_terms()` L390-420 already does bulk match-condition + action count enrichment — correct pattern for term prefetch

### Established Patterns
- Inline prefetch block (Phase 35): prefetch immediately after co-primary fetches, before per-item enrichment
- Graceful degradation: try/except around prefetch, `WarningCollector.add(key, str(e))`, use empty dict/map
- Bulk + lookup dict: `bulk_results = cms_list(...); lookup = {item.parent_id: [...] for item in bulk_results}`
- Co-primaries: independent `try/except` for filters vs policers; `not filters_ok and not policers_ok` → raise
- `object.__setattr__(item, attr, value)` for dynamic field attachment (Phase 35 used it, applicable here)

### Integration Points
- `get_device_firewall_summary` called by: `workflows.py` `firewall_summary` workflow stub, CLI `nautobot-mcp --json cms firewalls firewall-summary --detail`
- Return type: `tuple[FirewallSummaryResponse, list]` — no change
- `detail=False` path untouched — term_count and action_count already correct from list-scoped bulks

</codebase_context>

<specifics>
## Specific Ideas

- "Prefetch terms/actions scoped to the device, not to each filter/policer individually — device-scoped bulk is still 1 HTTP call"
- "Test coverage: assert call count ≤6 with 10 filters + 20 terms each + 5 policers + 10 actions each"
- "Phase 35 precedent: inline prefetch in workflow function, not refactored into shared helpers"
- "Phase 35 precedent: graceful degradation for non-critical enrichment"

</specifics>

<deferred>
## Deferred Ideas

### Scope Deferred
- `list_firewall_terms` deduplication — both `list_firewall_filters` (for term_count) and `get_device_firewall_summary detail=True` (for full terms) fetch all terms for a device. Future phase could refactor `list_firewall_terms` to return a shared lookup map, but not in Phase 36 scope.
- `list_firewall_policer_actions` deduplication — same pattern as above for policer actions.

</deferred>

---

*Phase: 36-firewall-summary-n1-fix*
*Context gathered: 2026-03-31*
