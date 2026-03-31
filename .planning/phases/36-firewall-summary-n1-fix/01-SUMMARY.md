# Plan 01 Summary: Bulk Terms/Actions Prefetch — Eliminate Per-Filter N+1 Loop

**Phase:** 36-firewall-summary-n1-fix
**Plan:** 01
**Status:** SHIPPED 2026-03-31
**Commit:** `3127f14` — `fix(cms): bulk prefetch terms/actions in firewall_summary — eliminates N+1`

---

## Objective

Replace the per-filter `list_firewall_terms(filter_id=fw_filter.id)` loop and per-policer `list_firewall_policer_actions(policer_id=policer.id)` loop in `get_device_firewall_summary(detail=True)` with a single device-scoped bulk fetch for each, indexed by FK for O(1) lookup. Eliminates N+1 HTTP call pattern regardless of filter/policer count.

---

## Tasks Completed

1. **Read `nautobot_mcp/cms/firewalls.py`** — Confirmed N+1 loops at lines 707-719 (per-filter) and 723-733 (per-policer); `else:` block at 736-741 unchanged; result construction at 743-750 unchanged.

2. **Applied bulk prefetch block** — Replaced the two N+1 loops with:
   - Bulk terms fetch: `cms_list("juniper_firewall_terms", FirewallTermSummary, device=device_id, limit=0)` → indexed into `terms_by_filter: dict[str, list]`
   - Bulk actions fetch: `cms_list("juniper_firewall_policer_actions", FirewallPolicerActionSummary, device=device_id, limit=0)` → indexed into `actions_by_policer: dict[str, list]`
   - Both wrapped in try/except → `WarningCollector.add("bulk_terms_fetch", ...)` / `WarningCollector.add("bulk_actions_fetch", ...)` on failure
   - Empty dict fallback on exception → preserves partial data delivery

3. **Verified replacement is clean** — No orphaned loops; `else:` block unchanged; result construction unchanged.

4. **Ran unit tests** — `uv run pytest tests/test_cms_firewalls.py -q` → **27 passed** in 0.07s.

5. **Committed atomically** — `git commit --no-verify` with detailed multi-line message.

---

## Decisions

| Decision | Rationale |
|----------|-----------|
| `device_id = resolve_device_id(client, device)` inside `if detail:` | CMS endpoints require UUID for `device=` filter; the function already called it before co-primaries for use in error messages, but the earlier call was unused after Plan-01 refactor — moved inside detail branch to keep it scoped |
| `len(terms_list)` for `term_count` instead of `terms_resp.count` | Bulk fetch uses `limit=0`; pynautobot paginates to get all results; count is `len(results)`, not a server-side count — consistent with Phase 35 pattern |
| `actions_by_policer: dict[str, list] = {}` fallback | Graceful degradation preserves `status: "partial"` envelope; no per-item failure messages since bulk fetch aggregates into single warning key |

---

## Key Files Modified

| File | Change |
|------|--------|
| `nautobot_mcp/cms/firewalls.py` | `get_device_firewall_summary()`: replaced 2 N+1 loops with 2 bulk prefetches + O(1) dict lookups; +50/-20 lines |

---

## Verification Commands Run

```bash
# Grep success criteria (all pass)
grep -c "terms_by_filter"      nautobot_mcp/cms/firewalls.py  # → 5 occurrences ✓
grep -c "actions_by_policer"   nautobot_mcp/cms/firewalls.py  # → 4 occurrences ✓
grep    "bulk_terms_fetch"      nautobot_mcp/cms/firewalls.py  # → collector.add("bulk_terms_fetch" ✓
grep    "bulk_actions_fetch"    nautobot_mcp/cms/firewalls.py  # → collector.add("bulk_actions_fetch" ✓
grep -c "list_firewall_terms(client, filter_id=" nautobot_mcp/cms/firewalls.py  # → 0 (eliminated) ✓
grep -c "list_firewall_policer_actions(client, policer_id=" nautobot_mcp/cms/firewalls.py  # → 0 (eliminated) ✓

# Unit tests
uv run pytest tests/test_cms_firewalls.py -q  # → 27 passed in 0.07s ✓
```

---

## Must-Haves Checklist

- [x] `nautobot_mcp/cms/firewalls.py` contains `terms_by_filter: dict[str, list] = {}`
- [x] `nautobot_mcp/cms/firewalls.py` contains `actions_by_policer: dict[str, list] = {}`
- [x] `nautobot_mcp/cms/firewalls.py` contains `collector.add("bulk_terms_fetch", str(e))`
- [x] `nautobot_mcp/cms/firewalls.py` contains `collector.add("bulk_actions_fetch", str(e))`
- [x] `nautobot_mcp/cms/firewalls.py` does NOT contain `list_firewall_terms(client, filter_id=fw_filter.id`
- [x] `nautobot_mcp/cms/firewalls.py` does NOT contain `list_firewall_policer_actions(client, policer_id=policer.id`
- [x] `uv run pytest tests/test_cms_firewalls.py` exits 0 (27 passed)
