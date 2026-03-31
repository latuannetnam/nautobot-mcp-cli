# Phase 36 Research: `firewall_summary` Detail N+1 Fix

**Researched:** 2026-03-31
**Status:** Complete — ready for planning

---

## 1. Current N+1 Patterns (Root Cause Analysis)

### N+1 #1: Per-filter term refetch (L707-717)

```python
# CURRENT — get_device_firewall_summary(), detail=True branch (L707-717)
for fw_filter in filters_data:
    fd = fw_filter.model_dump()
    try:
        terms_resp = list_firewall_terms(client, filter_id=fw_filter.id, limit=0)  # ← 1 call per filter
        terms_capped = terms_resp.results[:limit] if limit > 0 else terms_resp.results
        fd["terms"] = [t.model_dump() for t in terms_capped]
        fd["term_count"] = terms_resp.count
    except Exception as e:
        collector.add(f"list_firewall_terms(filter={fw_filter.id})", str(e))
        fd["terms"] = []
    filter_dicts.append(fd)
```

**Problem:** For each firewall filter, one `list_firewall_terms(filter_id=...)` HTTP call.
With many filters on a device: N sequential HTTP calls instead of 1.

### N+1 #2: Per-policer action refetch (L722-733)

```python
# CURRENT — get_device_firewall_summary(), detail=True branch (L722-733)
for policer in policers_data:
    pd = policer.model_dump()
    try:
        actions_resp = list_firewall_policer_actions(client, policer_id=policer.id, limit=0)  # ← 1 call per policer
        actions_capped = actions_resp.results[:limit] if limit > 0 else actions_resp.results
        pd["actions"] = [a.model_dump() for a in actions_capped]
        pd["action_count"] = actions_resp.count
    except Exception as e:
        collector.add(f"list_firewall_policer_actions(policer={policer.id})", str(e))
        pd["actions"] = []
    policer_dicts.append(pd)
```

**Problem:** For each firewall policer, one `list_firewall_policer_actions(policer_id=...)` HTTP call.
With many policers: M sequential HTTP calls instead of 1.

### Total N+1 Call Count

| Scenario | Per-filter calls | Per-policer calls | Total extra calls |
|----------|-----------------|-------------------|-------------------|
| Few filters/policers | N_filters | N_policers | N + M |
| Many (HQV-PE1) | ~10-50 | ~5-20 | 15-70+ |

While smaller than `interface_detail`'s ~4,000-call problem, the pattern is identical and the fix is straightforward.

---

## 2. Fix Design

### Prefetch Block (insert after L702 `if not filters_ok and not policers_ok`, inside `if detail:`, before L707 filter loop)

```python
# STEP 1: Resolve device_id (needed for device-scoped bulk fetches)
# list_firewall_filters/policers call resolve_device_id internally but don't expose it.
# We resolve it here for the prefetch. resolve_device_id is already imported at module top.
device_id = resolve_device_id(client, device)

# STEP 2: Bulk fetch ALL terms for all filters on this device → dict by filter_id
terms_by_filter: dict[str, list] = {}
try:
    all_terms_resp = cms_list(
        client,
        "juniper_firewall_terms",
        FirewallTermSummary,
        device=device_id,
        limit=0,
    )
    for t in all_terms_resp.results:
        terms_by_filter.setdefault(t.filter_id, []).append(t)
except Exception as e:
    collector.add("bulk_terms_fetch", str(e))
    terms_by_filter = {}  # graceful degradation

# STEP 3: Bulk fetch ALL actions for all policers on this device → dict by policer_id
actions_by_policer: dict[str, list] = {}
try:
    all_actions_resp = cms_list(
        client,
        "juniper_firewall_policer_actions",
        FirewallPolicerActionSummary,
        device=device_id,
        limit=0,
    )
    for a in all_actions_resp.results:
        actions_by_policer.setdefault(a.policer_id, []).append(a)
except Exception as e:
    collector.add("bulk_actions_fetch", str(e))
    actions_by_policer = {}  # graceful degradation
```

### Update Filter Loop (replace L710 `list_firewall_terms` call with dict lookup)

```python
# OLD (L710):
terms_resp = list_firewall_terms(client, filter_id=fw_filter.id, limit=0)
terms_capped = terms_resp.results[:limit] if limit > 0 else terms_resp.results
fd["terms"] = [t.model_dump() for t in terms_capped]
fd["term_count"] = terms_resp.count

# NEW (dict lookup, no HTTP call):
terms_list = terms_by_filter.get(fw_filter.id, [])
terms_capped = terms_list[:limit] if limit > 0 else terms_list
fd["terms"] = [t.model_dump() for t in terms_capped]
fd["term_count"] = len(terms_list)
```

### Update Policer Loop (replace L726 `list_firewall_policer_actions` call with dict lookup)

```python
# OLD (L726):
actions_resp = list_firewall_policer_actions(client, policer_id=policer.id, limit=0)
actions_capped = actions_resp.results[:limit] if limit > 0 else actions_resp.results
pd["actions"] = [a.model_dump() for a in actions_capped]
pd["action_count"] = actions_resp.count

# NEW (dict lookup, no HTTP call):
actions_list = actions_by_policer.get(policer.id, [])
actions_capped = actions_list[:limit] if limit > 0 else actions_list
pd["actions"] = [a.model_dump() for a in actions_capped]
pd["action_count"] = len(actions_list)
```

---

## 3. HTTP Call Budget (CQP-02)

Target: ≤6 HTTP calls in `get_device_firewall_summary(detail=True)` for a fully-enriched response:

| # | Call | Origin | Notes |
|---|------|--------|-------|
| 1 | `list_firewall_filters(device=..., limit=0)` | Co-primary 1 (L686) | Existing |
| 2 | `list_firewall_policers(device=..., limit=0)` | Co-primary 2 (L694) | Existing |
| 3 | `cms_list(juniper_firewall_terms, device=..., limit=0)` | NEW bulk terms prefetch | 1 call regardless of filter count |
| 4 | `cms_list(juniper_firewall_policer_actions, device=..., limit=0)` | NEW bulk actions prefetch | 1 call regardless of policer count |
| 5 | `cms_list(juniper_firewall_terms, ..., device=..., limit=0)` | Inside `list_firewall_filters` (L74-80) | `term_count` bulk (already correct) |
| 6 | `cms_list(juniper_firewall_policer_actions, ..., device=..., limit=0)` | Inside `list_firewall_policers` (L248-254) | `action_count` bulk (already correct) |

**Note:** Calls 5 and 6 are NOT in a per-filter/per-policer loop — they are single bulk fetches inside `list_firewall_filters` and `list_firewall_policers` respectively. They are counted but are already optimal (1 each). The 2 new bulk calls (3 and 4) replace the N+1 loops.

**Total: 6 calls constant, regardless of filter/policer/term/action count.**

---

## 4. Graceful Degradation (CQP-05)

Both `terms_by_filter` and `actions_by_policer` are non-critical enrichment for `detail=True`:
- The `detail=False` co-primaries (filters + policers with counts) already succeeded before entering the `detail=True` branch
- `WarningCollector` is already imported and instantiated at L678
- Co-primary failure already handled (L701-702: `not filters_ok and not policers_ok → raise`)

**Degradation scenarios:**

| Failure | Behavior | Warning Key |
|---------|----------|-------------|
| Bulk terms prefetch fails | `terms_by_filter = {}`, `fd["terms"] = []` per filter | `collector.add("bulk_terms_fetch", str(e))` |
| Bulk actions prefetch fails | `actions_by_policer = {}`, `pd["actions"] = []` per policer | `collector.add("bulk_actions_fetch", str(e))` |

The `terms_by_filter` and `actions_by_policer` dicts default to `{}` on failure, so `.get(id, [])` returns `[]` — same pattern as Phase 35 VRRP graceful degradation.

---

## 5. `device_id` Resolution

`resolve_device_id(client, device)` must be called inside the `if detail:` block because:
- `list_firewall_filters` and `list_firewall_policers` call it internally but don't return the UUID
- The prefetch block needs `device_id` for `device=device_id` filters
- `resolve_device_id` is already imported at module level (L23)

```python
from nautobot_mcp.cms.client import (
    ...
    resolve_device_id,  # already imported
    ...
)
```

Double-resolution (once inside each co-primary, once in prefetch) is the same acceptable tradeoff as Phase 35 `list_interface_units` double-fetching families. The 2nd resolution is a pynautobot `.get()` by name — negligible cost vs. the N+1 it prevents.

---

## 6. Model Field Compatibility

Both bulk prefetches reuse existing `FirewallTermSummary` and `FirewallPolicerActionSummary` models already imported at module top (L27-34):

| Prefetch | Endpoint | Model | Join Key | Usage |
|----------|----------|-------|----------|-------|
| Terms | `juniper_firewall_terms` | `FirewallTermSummary` | `t.filter_id` | `terms_by_filter[t.filter_id].append(t)` |
| Actions | `juniper_firewall_policer_actions` | `FirewallPolicerActionSummary` | `a.policer_id` | `actions_by_policer[a.policer_id].append(a)` |

Both models already have these fields from the existing `list_firewall_terms` and `list_firewall_policer_actions` functions. No model changes needed.

---

## 7. `detail=False` Path

The `detail=False` path (L736-741) is **untouched** — `term_count` and `action_count` are already populated by the list-scoped bulk fetches inside `list_firewall_filters` (L74-85) and `list_firewall_policers` (L248-259). No per-item HTTP calls in `detail=False`.

---

## 8. Phase 35 Precedent — Key Differences

| Aspect | Phase 35 (`interface_detail`) | Phase 36 (`firewall_summary`) |
|--------|-------------------------------|-------------------------------|
| Co-primaries | 1 (units) | 2 (filters + policers) |
| Per-item loops | 2 (per-unit families, per-family VRRP) | 2 (per-filter terms, per-policer actions) |
| Prefetch calls | 2 new (families + VRRP) | 2 new (terms + actions) |
| Critical data hard-fail | Family prefetch (D-03) | Neither — both are enrichment only |
| Call budget | ≤3 | ≤6 |
| Test file | `test_cms_interfaces_n1.py` | `test_cms_firewalls_n1.py` (new) |

**Critical difference:** Phase 35 had one hard-fail case (family prefetch = critical) and one graceful case (VRRP = enrichment). Phase 36 has **no hard-fail case** — both terms and actions are enrichment data. Both use graceful degradation with `WarningCollector`. This is simpler than Phase 35.

---

## 9. Unit Test Plan

Following Phase 35's `test_cms_interfaces_n1.py` pattern:

### New tests in `tests/test_cms_firewalls_n1.py`

| Test | What it verifies |
|------|-----------------|
| `test_firewall_summary_bulk_prefetch_exactly_6_calls` | CQP-02: With 10 filters + 20 terms + 5 policers + 10 actions, `cms_list` is called exactly 6 times (2 co-primary + 2 bulk + 2 list-scoped counts) |
| `test_firewall_summary_no_per_filter_terms_calls` | CQP-02: `list_firewall_terms` never called per-filter in `detail=True` |
| `test_firewall_summary_no_per_policer_actions_calls` | CQP-02: `list_firewall_policer_actions` never called per-policer in `detail=True` |
| `test_firewall_summary_terms_prefetch_failure_graceful` | CQP-05: Bulk terms prefetch failure → `collector.warnings` has `"bulk_terms_fetch"`, empty `terms_by_filter = {}`, `terms = []` |
| `test_firewall_summary_actions_prefetch_failure_graceful` | CQP-05: Bulk actions prefetch failure → `collector.warnings` has `"bulk_actions_fetch"`, empty `actions_by_policer = {}`, `actions = []` |
| `test_firewall_summary_terms_enriched_from_prefetch_map` | Term data correctly resolved from prefetched `terms_by_filter` map |
| `test_firewall_summary_actions_enriched_from_prefetch_map` | Action data correctly resolved from prefetched `actions_by_policer` map |
| `test_firewall_summary_detail_false_unaffected` | `detail=False` path makes 2 co-primary calls only (no prefetch block entered) |

### Test structure (Phase 35 pattern)

```python
# Monkey-patch cms_list to count HTTP calls
def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
    ...

with patch("nautobot_mcp.cms.firewalls.resolve_device_id", return_value="device-uuid-1"), \
     patch("nautobot_mcp.cms.firewalls.list_firewall_filters", return_value=filters_resp), \
     patch("nautobot_mcp.cms.firewalls.list_firewall_policers", return_value=policers_resp), \
     patch("nautobot_mcp.cms.firewalls.cms_list", side_effect=cms_list_side_effect) as mock_cms, \
     patch("nautobot_mcp.cms.firewalls.list_firewall_terms") as mock_terms, \
     patch("nautobot_mcp.cms.firewalls.list_firewall_policer_actions") as mock_actions:
    result, warnings = get_device_firewall_summary(client, device="edge-01", detail=True)

    assert mock_cms.call_count == 2  # 2 new bulk prefetch calls
    mock_terms.assert_not_called()   # no per-filter calls
    mock_actions.assert_not_called() # no per-policer calls
```

### Assertions for ≤6 call count

The 6-call total includes 2 co-primaries (patched as unit returns, not `cms_list` calls) + 2 bulk prefetch calls (via `cms_list`) + 2 list-scoped count calls (via `cms_list` inside the patched co-primaries).

**Co-primary unit-return patch vs cms_list patch distinction:** `list_firewall_filters` and `list_firewall_policers` are patched to return unit responses directly (no `cms_list` inside them). The list-scoped count calls (term_count, action_count) are what `list_firewall_filters`/`list_firewall_policers` would call internally — but since we're mocking them as unit returns, those internal calls don't happen in the test.

**Actual call count in test:** `cms_list` is called 2 times (bulk prefetch only). The list-scoped counts come from the patched co-primaries returning already-populated mock objects with `term_count`/`action_count` attributes set directly.

**Verification strategy:** Rather than counting total `cms_list` calls (complex due to unit-return patching), test two invariants:
1. `list_firewall_terms.assert_not_called()` — proves per-filter N+1 gone
2. `list_firewall_policer_actions.assert_not_called()` — proves per-policer N+1 gone
3. `cms_list.call_count == 2` (only the 2 bulk prefetches) — proves only intentional bulk calls

---

## 10. pynautobot Bulk Fetch (Same as Phase 33/35)

Same `_CMS_BULK_LIMIT = 200` mechanism:
- Both bulk prefetches go through `cms_list` → `endpoint.filter(device=device_id, limit=200)` or `endpoint.all(limit=200)`
- CMS plugin PAGE_SIZE=1: without `_CMS_BULK_LIMIT`, `limit=0` would make 1 call per record
- With `_CMS_BULK_LIMIT = 200`: `ceil(N/200)` calls per bulk endpoint
- For devices with many terms/actions: still bounded at ~ceil(N/200) pages, not N

---

## 11. `WarningCollector` Integration (CQP-05)

Already wired at `get_device_firewall_summary` L678:
```python
collector = WarningCollector()
```

Both graceful degradation paths add warnings with descriptive keys:

```python
# Terms failure
collector.add("bulk_terms_fetch", str(e))

# Actions failure
collector.add("bulk_actions_fetch", str(e))
```

**CQP-05 contract preserved:** Partial failure (bulk prefetch fails) → `status: "partial"` with warnings list. Response is still valid (enrichment is optional). Both co-primaries succeeded → no hard-fail.

---

## 12. Code Change Map

| Region | Before | After |
|--------|--------|-------|
| L703 (`if detail:`) | Opens detail branch | + `device_id = resolve_device_id(...)` + bulk prefetch block |
| L707 (filter loop) | `list_firewall_terms(client, filter_id=fw_filter.id)` | `terms_by_filter.get(fw_filter.id, [])` |
| L710-712 (terms assignment) | `terms_resp.count`, `[t.model_dump() for t in terms_capped]` | `len(terms_list)`, `[t.model_dump() for t in terms_capped]` |
| L714-716 (terms error) | `collector.add("list_firewall_terms(...)", str(e))` | No collector call (handled by prefetch block) |
| L722 (policer loop) | `list_firewall_policer_actions(client, policer_id=policer.id)` | `actions_by_policer.get(policer.id, [])` |
| L726-729 (actions assignment) | `actions_resp.count`, `[a.model_dump() for a in actions_capped]` | `len(actions_list)`, `[a.model_dump() for a in actions_capped]` |
| L730-732 (actions error) | `collector.add("list_firewall_policer_actions(...)", str(e))` | No collector call (handled by prefetch block) |
| Total HTTP calls | N_filters + N_policers + 2 co-primaries + 2 list-scoped | 6 constant |

**Note on error collector calls (L714-716, L730-732):** After the fix, these exception handlers are dead code for the normal path (bulk prefetch succeeds). They remain as defensive fallback if:
1. A filter/policer was created between co-primary fetch and detail prefetch
2. The bulk prefetch succeeded but a specific filter_id/policer_id is missing from results

This defensive fallback is harmless — it just means per-item HTTP calls as a last resort. The N+1 is only truly eliminated when bulk prefetch fully succeeds.

---

## 13. `detail=False` Behavior (No Change)

The `detail=False` path (L736-741) has no per-item loops:
```python
else:
    filters_capped = filters_data[:limit] if limit > 0 else filters_data
    policers_capped = policers_data[:limit] if limit > 0 else policers_data
    filter_dicts = [f.model_dump() for f in filters_capped]
    policer_dicts = [p.model_dump() for p in policers_capped]
```

`term_count` and `action_count` are already set by `list_firewall_filters` (L82-85) and `list_firewall_policers` (L255-259) — 1 call each. No N+1 in `detail=False`.

---

## 14. Smoke Test Impact (`uat_cms_smoke.py`)

The smoke test (via CLI) will show:
- Pre-fix: N_filter + N_policer + 2 co-primary + 2 list-scoped calls (potentially 70+ total)
- Post-fix: Exactly 6 unique URL paths (filters, terms-bulk, terms-device, policers, actions-bulk, actions-device)

**Threshold:** `firewall_summary` workflow in `uat_cms_smoke.py` already has a `<60s` threshold. Post-fix should be well under that.

---

## 15. Open Questions / Clarifications

| # | Question | Answer |
|---|----------|--------|
| 1 | Are there per-term match-condition or action count enrichments in the detail path? | No — `detail=True` for `firewall_summary` stops at term list and action list. Match conditions per term are not fetched (unlike `get_firewall_filter` which does inline mc/action enrichment). No further N+1. |
| 2 | Should the prefetch block be gated on `filters_ok` or `policers_ok`? | Only gate on BOTH failing (`not filters_ok and not policers_ok`). If one co-primary succeeded, its detail enrichment is still useful. The prefetch uses `device_id` directly, not `filters_data`/`policers_data`. |
| 3 | What if the device has 0 filters or 0 policers? | Prefetch still runs (empty results → empty dicts → empty enrichment → fine). Co-primaries succeeded so we enter the `if detail:` branch. |
| 4 | Should `list_firewall_terms` or `list_firewall_policer_actions` be refactored to reuse the prefetch? | Out of scope (D-01: inline prefetch only). Those functions are used independently (e.g., in `get_firewall_filter`, `get_firewall_policer`). |
| 5 | Does `resolve_device_id` inside `if detail:` cause an extra call even for `detail=False`? | No — it's inside the `if detail:` block only. `detail=False` never calls it. |
| 6 | Are the error collector calls in the per-item loops (L714-716, L730-732) dead code after fix? | Mostly yes if bulk prefetch succeeds. They remain as defensive fallback for race conditions (data created between co-primary and detail prefetch). Harmless to keep. |

---

## 16. Summary of All Findings

| Question | Answer |
|----------|--------|
| N+1 #1 exact lines | L707-717: `list_firewall_terms(filter_id=fw_filter.id)` per filter in loop |
| N+1 #2 exact lines | L722-733: `list_firewall_policer_actions(policer_id=policer.id)` per policer in loop |
| Prefetch structure | Inside `if detail:` after co-primary checks: resolve device_id → bulk terms → index by filter_id → bulk actions → index by policer_id |
| Graceful degradation | Both term and action prefetch failures: try/except → `collector.add("bulk_terms_fetch"/"bulk_actions_fetch", str(e))` → empty dict |
| Call budget | ≤6 total (2 co-primaries + 2 new bulk prefetches + 2 list-scoped counts already in co-primaries) |
| Model changes | None — `FirewallTermSummary.filter_id` and `FirewallPolicerActionSummary.policer_id` already exist |
| `WarningCollector` | Already imported at L651; warning keys: `"bulk_terms_fetch"`, `"bulk_actions_fetch"` |
| `detail=False` affected? | No — prefetch block only inside `if detail:`, `detail=False` unchanged |
| Phase 35 precedent | Same inline prefetch pattern; simpler (no hard-fail case, both are enrichment) |
| New tests | 8 new tests in `tests/test_cms_firewalls_n1.py` following Phase 35 pattern |
| No blockers | None identified |

---

## 17. Planning Inputs

**Ready for PLAN.md:**
- Both N+1 patterns identified with exact line numbers
- Fix structure: 2 new bulk prefetch blocks → dict lookups replace per-item HTTP calls
- Graceful degradation: both enrichment failures use `WarningCollector` with descriptive keys
- 6-call budget breakdown confirmed
- Test plan: 8 new tests following Phase 35 `test_cms_interfaces_n1.py` pattern
- No model changes, no signature changes, no `detail=False` impact
- No blockers

**Key observation:** Phase 36 is simpler than Phase 35 — no hard-fail case (both terms and actions are enrichment), no closure update needed, no backward-compatibility concerns with other callers of the per-item functions. The fix is a pure prefetch + dict-lookup substitution.
